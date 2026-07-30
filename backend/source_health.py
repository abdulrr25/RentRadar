"""
Tracks whether the live data sources (Anakin) are currently healthy, based on
real search outcomes rather than a separate proactive health-check call —
Anakin's search API costs real credits per call (this project has hit 0
balance once already), so polling it just to answer "are we healthy" would
make the exact problem it's meant to catch worse. Instead, agent.py reports
in after every real search, and /health reflects that.

The cost of that tradeoff is that this module can be genuinely ignorant:
right after a restart, or during a quiet stretch, nothing has reported in.
It used to answer "healthy" in that situation, which is a guess dressed up
as a fact — an uptime monitor watching /health would see a freshly
restarted instance as fine even while Anakin was completely down. So the
state is now three-valued: healthy, degraded, or unknown.
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
    "credit_exhausted": False,
}


def mark_credit_exhausted() -> bool:
    """
    Record that at least one Anakin API reported exhausted credits.

    Tracked separately from `degraded` on purpose: credit exhaustion can be
    partial. Anakin exposes two APIs (search for listings, wire for
    Reddit/HN/news) and if those bill from separate pools, one can run dry
    while the other keeps working — results quietly get worse without a
    total outage. That still needs to page the owner (it costs money to
    fix), but it does not warrant telling users the site is broken while
    listings are still coming back.

    Returns True only on the transition into exhaustion, so callers page
    once rather than on every subsequent search.
    """
    was_clear = not _state["credit_exhausted"]
    _state["credit_exhausted"] = True
    return was_clear


def clear_credit_exhausted() -> None:
    """Called after a search where no source reported a credit problem."""
    _state["credit_exhausted"] = False


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
    _state["credit_exhausted"] = False


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
        "credit_exhausted": _state["credit_exhausted"],
    }
