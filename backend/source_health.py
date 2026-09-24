"""
Tracks whether the live listing search (SearXNG + the portal scrapers) is
currently healthy, based on real search outcomes rather than a separate
proactive health-check call. Reporting in after every real search instead of
polling means a status check never adds load of its own — agent.py reports
in after every real search, and /health reflects that.

The cost of that tradeoff is that this module can be genuinely ignorant:
right after a restart, or during a quiet stretch, nothing has reported in.
It used to answer "healthy" in that situation, which is a guess dressed up
as a fact — an uptime monitor watching /health would see a freshly
restarted instance as fine even while the search backend was completely
down. So the state is now three-valued: healthy, degraded, or unknown.
"""

import time

# How long a successful search is treated as evidence that sources still
# work. Past this, we stop claiming "healthy" and fall back to "unknown" —
# we don't know that anything is broken, but we no longer know it isn't.
FRESH_FOR_SECONDS = 3600

_state = {
    "degraded": False,
    "reason": None,
    "since": None,
    "last_result_at": None,
}


def mark_degraded(reason: str) -> bool:
    """Returns True the moment sources go from healthy to degraded (a fresh
    outage), False on every subsequent call while still degraded — callers
    use this to fire one-time alerts instead of re-alerting on every request.
    """
    was_healthy = not _state["degraded"]
    if was_healthy:
        _state["since"] = int(time.time())
    _state["degraded"] = True
    _state["reason"] = reason
    _state["last_result_at"] = int(time.time())
    return was_healthy


def mark_healthy() -> None:
    _state["degraded"] = False
    _state["reason"] = None
    _state["since"] = None
    _state["last_result_at"] = int(time.time())


def reset() -> None:
    """Back to the just-started state — nothing observed yet. For tests."""
    _state["degraded"] = False
    _state["reason"] = None
    _state["since"] = None
    _state["last_result_at"] = None


def get_status() -> dict:
    """
    Current view of source health.

    `status` is one of:
      degraded — a real search recently failed across every source
      ok       — a real search recently succeeded
      unknown  — nothing has reported in since startup, or the last result
                 is older than FRESH_FOR_SECONDS

    "unknown" is deliberately not treated as a problem by callers: it means
    we have no evidence either way, not that something is wrong.
    """
    last = _state["last_result_at"]
    if _state["degraded"]:
        status = "degraded"
    elif last is None:
        status = "unknown"
    elif time.time() - last > FRESH_FOR_SECONDS:
        status = "unknown"
    else:
        status = "ok"

    return {
        "status": status,
        "degraded": _state["degraded"],
        "reason": _state["reason"],
        "since": _state["since"],
        "last_result_at": last,
    }
