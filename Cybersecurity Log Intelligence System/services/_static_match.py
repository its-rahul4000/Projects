"""
Lightweight static-pattern matcher executed in child processes.

This module deliberately imports ONLY the standard library (``re``). Worker processes
spawned for parallel static matching import this module — never pandas or any analysis
module — so each child starts in milliseconds instead of paying a ~1-2s pandas import.
Cheap child startup is what makes multi-core matching a real net win (the previous
design re-imported pandas in every spawned process, which on Windows ``spawn`` dominated
the runtime and made parallelism slower than serial on some machines).
"""
import re


def match_chunk(texts, patterns):
    """Run every pattern over a chunk of log-line texts (executed in a child process).

    Returns, per pattern, the LOCAL row indices that matched. Uses ``re.search`` with
    IGNORECASE — identical semantics to pandas ``str.contains(case=False, regex=True)`` —
    so parallel results are byte-for-byte the same as the single-process path.
    """
    progs = [re.compile(p, re.IGNORECASE) for p in patterns]
    out = [[] for _ in patterns]
    for i, t in enumerate(texts):
        if not t:
            continue
        for pi, prog in enumerate(progs):
            if prog.search(t):
                out[pi].append(i)
    return out
