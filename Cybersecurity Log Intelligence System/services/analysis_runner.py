"""
Submits log-analysis jobs to process-isolated workers and bounds concurrency.

Why this exists
---------------
Streamlit serves every user from a single Python process. A CPU-heavy analysis
(parsing + regex over hundreds of thousands of lines) holds the GIL and would
freeze every other IT Owner's session. This runner offloads that work to a
separate OS process (``services.analysis_worker``) and only *waits* on it, so the
main process stays responsive for everyone.

A module-level semaphore caps how many worker processes run at once, so a burst of
80–90 users cannot exhaust CPU/RAM — excess jobs queue until a slot frees up.

If a worker cannot be launched for any reason, it transparently falls back to
in-process execution so the application always works.
"""
import os
import sys
import json
import time
# pickle only de/serialises our OWN worker's trusted output file (never external data).
import pickle  # nosec B403
import logging
import tempfile
import threading
# subprocess launches our own analysis worker with a fixed argv and shell=False.
import subprocess  # nosec B404

from config.settings import BASE_DIR, ANALYSIS_MAX_WORKERS, USE_WORKER_PROCESS

logger = logging.getLogger(__name__)

# Shared across all Streamlit sessions (same process) → caps total concurrent workers.
_slots = threading.BoundedSemaphore(max(1, ANALYSIS_MAX_WORKERS))

_RAW_COLS = ["line_num", "timestamp", "level", "source_ip", "message"]
_MAX_QUEUE_WAIT_SECONDS = 180


def rules_to_dicts(rules) -> list[dict]:
    """Convert DetectionRule ORM objects to plain, picklable dicts for the worker."""
    out = []
    for r in rules:
        out.append({
            "rule_name": r.rule_name,
            "condition": r.condition,
            "rule_type": r.rule_type,
            "severity": r.severity,
            "is_static": getattr(r, "is_static", True),
            "default_threshold": r.default_threshold,
            "time_window_seconds": r.time_window_seconds,
            # group_by drives behavioural/custom aggregation (Source IP / Username /
            # whole-file); without it, grouped custom rules misbehave in the worker.
            "group_by": getattr(r, "group_by", None),
            # Carry the live (admin-editable) recommended action to the worker so it
            # travels with each finding into the PDF / results panel — keeping the
            # report in sync with what the Rules page shows.
            "recommended_action": getattr(r, "recommended_action", None),
        })
    return out


def _cancelled_result() -> dict:
    return {"findings": [], "total_entries": 0, "raw_sample": None, "error": None, "cancelled": True}


def run_analysis_job(file_paths: list[str], rule_dicts: list[dict], progress_cb=None,
                     cancel_event=None) -> dict:
    """Parse the given log files and evaluate the rules.

    Returns {"findings", "total_entries", "raw_sample", "error"}. progress_cb, if
    given, is called with (fraction in [0,1], status text). If cancel_event is
    provided and gets set, the run is aborted (worker subprocess terminated).
    """
    if not USE_WORKER_PROCESS:
        return _run_in_process(file_paths, rule_dicts, progress_cb, cancel_event)

    # Wait (non-blocking poll) for a free worker slot so we can show "queued" feedback.
    # The sleeps release the GIL, so other sessions keep running while we wait.
    waited = 0.0
    while not _slots.acquire(blocking=False):
        if cancel_event is not None and cancel_event.is_set():
            return _cancelled_result()
        if progress_cb:
            progress_cb(0.02, "Queued — waiting for a free analysis worker…")
        time.sleep(0.3)
        waited += 0.3
        if waited > _MAX_QUEUE_WAIT_SECONDS:
            logger.warning("Worker-slot wait exceeded %ss; running in-process.", _MAX_QUEUE_WAIT_SECONDS)
            return _run_in_process(file_paths, rule_dicts, progress_cb, cancel_event)

    job_path = prog_path = out_path = None
    try:
        job_path = _mktemp("_job.json")
        prog_path = _mktemp("_prog.json")
        out_path = _mktemp("_out.pkl")

        with open(job_path, "w", encoding="utf-8") as fh:
            json.dump({
                "file_paths": file_paths,
                "rules": rule_dicts,
                "progress_path": prog_path,
                "output_path": out_path,
            }, fh)

        if progress_cb:
            progress_cb(0.04, "Starting analysis worker…")

        # Fixed argv via sys.executable; shell=False; no user input.
        proc = subprocess.Popen(  # nosec B603
            [sys.executable, "-m", "services.analysis_worker", job_path],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        while proc.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
                return _cancelled_result()
            frac, text = _read_progress(prog_path)
            if progress_cb and frac is not None:
                progress_cb(frac, text or "Analyzing…")
            time.sleep(0.25)

        if proc.returncode != 0:
            err = b""
            try:
                err = proc.stderr.read() if proc.stderr else b""
            except Exception:
                logger.debug("Could not read worker stderr.", exc_info=True)
            logger.error("Analysis worker exited %s: %s", proc.returncode, err[:1000])
            return _run_in_process(file_paths, rule_dicts, progress_cb, cancel_event)

        with open(out_path, "rb") as fh:
            # Trusted input: this file is the pickled result our own worker process
            # wrote to a temp path we created moments ago — not external/user data.
            result = pickle.load(fh)  # nosec B301
        if progress_cb:
            progress_cb(1.0, "Done!")
        return result
    except Exception as exc:
        logger.exception("Worker run failed; falling back to in-process: %s", exc)
        return _run_in_process(file_paths, rule_dicts, progress_cb, cancel_event)
    finally:
        _slots.release()
        for p in (job_path, prog_path, out_path):
            if p:
                try:
                    os.remove(p)
                except OSError:
                    pass


# ── In-process fallback (same logic, runs in the Streamlit process) ─────────────

def _run_in_process(file_paths, rule_dicts, progress_cb, cancel_event=None) -> dict:
    from services.log_parser import parse_log_file, merge_dataframes
    from services.threat_engine import run_analysis
    from services.analysis_worker import Rule

    n = max(len(file_paths), 1)
    dfs = []
    for i, path in enumerate(file_paths):
        if cancel_event is not None and cancel_event.is_set():
            return _cancelled_result()

        def _pcb(fr, entries=0, _i=i):
            if progress_cb:
                progress_cb(0.05 + 0.50 * ((_i + fr) / n),
                            f"Parsing log files… {entries:,} entries")
        df = parse_log_file(path, progress_cb=_pcb)
        if df is not None and not df.empty:
            dfs.append(df)

    if not dfs:
        return {"findings": [], "total_entries": 0, "raw_sample": None, "error": None}

    if cancel_event is not None and cancel_event.is_set():
        return _cancelled_result()

    merged = dfs[0]
    for d in dfs[1:]:
        merged = merge_dataframes(merged, d)

    total = len(merged)

    def _rcb(fr):
        if progress_cb:
            progress_cb(0.55 + 0.40 * fr, f"Running detection rules on {total:,} entries…")

    # Flip the status text to the detection phase up-front, matching the worker path.
    if progress_cb:
        progress_cb(0.55, f"Running detection rules on {total:,} entries…")
    rules = [Rule(d) for d in rule_dicts]
    findings = run_analysis(merged, rules, progress_cb=_rcb)
    raw_cols = [c for c in _RAW_COLS if c in merged.columns]
    return {
        "findings": findings,
        "total_entries": int(len(merged)),
        "raw_sample": merged[raw_cols].head(1000).copy(),
        "error": None,
    }


# ── helpers ─────────────────────────────────────────────────────────────────────

def _mktemp(suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def _read_progress(path: str):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return d.get("frac"), d.get("text", "")
    except Exception:
        # File may be missing or mid-write; just skip this poll.
        return None, ""
