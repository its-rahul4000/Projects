"""
Standalone, process-isolated analysis worker.

This module is launched in a SEPARATE OS process via:

    python -m services.analysis_worker <job.json>

Running the heavy log parsing + regex rule evaluation in its own process means it
never holds the Streamlit server's GIL, so the dashboard stays responsive for all
other IT Owners while one user's large log file is being analysed. It also isolates
crashes — a worker failure cannot take down the web server.

It deliberately imports NO Streamlit code and has no import-time side effects, so
it is safe to spawn on Windows (``spawn`` start method) without re-launching the app.

Job JSON schema:
    {
      "file_paths":   ["<temp path>", ...],   # log files to parse (merged together)
      "rules":        [ {rule dict}, ... ],    # plain dicts (no ORM/DB needed)
      "progress_path":"<path>",                # worker writes {"frac","text"} here
      "output_path":  "<path>"                 # worker writes a pickled result here
    }

Result (pickled dict):
    {"findings": [...], "total_entries": int, "raw_sample": DataFrame|None, "error": str|None}
"""
import sys
import json
# pickle only de/serialises this worker's OWN trusted result file (never external data).
import pickle  # nosec B403
from pathlib import Path

# Make the project root importable when launched with -m from any working dir.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# NOTE: pandas / analysis modules are imported lazily inside run_job(), NOT at module
# top level. The parallel matcher spawns child processes that re-import this module
# during bootstrap; keeping the top level stdlib-only means each child starts in
# milliseconds instead of paying a ~1-2s pandas import (the main speed-up for #17).

_RAW_COLS = ["line_num", "timestamp", "level", "source_ip", "message"]


class Rule:
    """Lightweight, duck-typed stand-in for a DetectionRule ORM object.

    run_analysis only reads attributes (no DB), so a plain object is enough and
    keeps the worker free of any database/session dependency.
    """

    def __init__(self, d: dict):
        self.rule_name = d.get("rule_name", "")
        self.condition = d.get("condition", "")
        self.rule_type = d.get("rule_type", "static")
        self.severity = d.get("severity", "INFO")
        self.is_static = d.get("is_static", True)
        self.default_threshold = d.get("default_threshold")
        self.time_window_seconds = d.get("time_window_seconds")
        # group_by drives custom/behavioural aggregation; it MUST be carried to the
        # worker or grouped custom rules silently fall back to whole-file counting.
        self.group_by = d.get("group_by")
        self.recommended_action = d.get("recommended_action")


def _write_progress(path: str, frac: float, text: str = "") -> None:
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"frac": max(0.0, min(float(frac), 1.0)), "text": text}, fh)
    except Exception:
        # Progress file is best-effort UI feedback; a write failure is non-fatal.
        pass  # nosec B110


def run_job(job: dict) -> dict:
    # Heavy imports live here (the main worker process only) so spawned match children
    # never import them. See the top-of-module note.
    from services.log_parser import parse_log_file, merge_dataframes
    from services.threat_engine import run_analysis

    file_paths = job.get("file_paths", [])
    rules = [Rule(d) for d in job.get("rules", [])]
    progress_path = job.get("progress_path", "")
    n = max(len(file_paths), 1)

    dfs = []
    for i, path in enumerate(file_paths):
        def _pcb(fr, entries=0, _i=i):
            _write_progress(progress_path, 0.05 + 0.50 * ((_i + fr) / n),
                            f"Parsing log files… {entries:,} entries")
        df = parse_log_file(path, progress_cb=_pcb)
        if df is not None and not df.empty:
            dfs.append(df)

    if not dfs:
        return {"findings": [], "total_entries": 0, "raw_sample": None, "error": None}

    merged = dfs[0]
    for d in dfs[1:]:
        merged = merge_dataframes(merged, d)

    total = len(merged)

    def _rcb(fr):
        _write_progress(progress_path, 0.55 + 0.40 * fr,
                        f"Running detection rules on {total:,} entries…")

    # Flip the status text to the detection phase up-front so the label is correct
    # while the first multi-core static pass runs (it reports no sub-progress yet).
    _write_progress(progress_path, 0.55, f"Running detection rules on {total:,} entries…")
    # parallel=True → static regex rules are matched across CPU cores in this worker.
    findings = run_analysis(merged, rules, progress_cb=_rcb, parallel=True)

    raw_cols = [c for c in _RAW_COLS if c in merged.columns]
    raw_sample = merged[raw_cols].head(1000).copy()

    return {
        "findings": findings,
        "total_entries": int(len(merged)),
        "raw_sample": raw_sample,
        "error": None,
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("usage: python -m services.analysis_worker <job.json>", file=sys.stderr)
        sys.exit(2)

    job_path = argv[0]
    with open(job_path, "r", encoding="utf-8") as fh:
        job = json.load(fh)

    try:
        result = run_job(job)
        _write_progress(job.get("progress_path", ""), 1.0, "Done")
    except Exception as exc:  # report the error back instead of crashing silently
        result = {"findings": [], "total_entries": 0, "raw_sample": None, "error": str(exc)}

    with open(job["output_path"], "wb") as fh:
        pickle.dump(result, fh)


if __name__ == "__main__":
    main()
