"""
Tracks whether the live data sources (Anakin) are currently healthy, based on
real search outcomes rather than a separate proactive health-check call —
Anakin's search API costs real credits per call (this project has hit 0
balance once already), so polling it just to answer "are we healthy" would
make the exact problem it's meant to catch worse. Instead, agent.py reports
in after every real search, and /health reflects that.

This means the very first request after a cold start assumes healthy until
proven otherwise — a deliberate tradeoff for zero extra cost, not an oversight.
"""

import time

_state = {"degraded": False, "reason": None, "since": None}


def mark_degraded(reason: str) -> None:
    if not _state["degraded"]:
        _state["since"] = int(time.time())
    _state["degraded"] = True
    _state["reason"] = reason


def mark_healthy() -> None:
    _state["degraded"] = False
    _state["reason"] = None
    _state["since"] = None


def get_status() -> dict:
    return dict(_state)
