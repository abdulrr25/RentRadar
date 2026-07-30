import time

import source_health


def setup_function():
    # Module-level global — reset before every test regardless of order.
    # reset() (not mark_healthy) gives the true just-started state: nothing
    # observed yet, which is what most of these tests want to reason about.
    source_health.reset()


def test_starts_unknown_not_healthy():
    # The whole point of the three-valued state: before any search has run
    # we have no evidence sources work. Claiming "ok" here would let an
    # uptime monitor read a freshly restarted instance as fine while Anakin
    # was completely down.
    status = source_health.get_status()
    assert status["status"] == "unknown"
    assert status["degraded"] is False
    assert status["last_result_at"] is None


def test_healthy_after_a_successful_search():
    source_health.mark_healthy()
    status = source_health.get_status()
    assert status["status"] == "ok"
    assert status["last_result_at"] is not None


def test_goes_unknown_once_the_last_result_is_stale():
    source_health.mark_healthy()
    assert source_health.get_status()["status"] == "ok"
    # Backdate past the freshness window rather than waiting an hour.
    source_health._state["last_result_at"] = int(time.time()) - source_health.FRESH_FOR_SECONDS - 60
    assert source_health.get_status()["status"] == "unknown"


def test_degraded_stays_degraded_even_when_stale():
    # A known outage must not decay into "unknown" — that would quietly
    # downgrade a real problem into a shrug.
    source_health.mark_degraded("Anakin credits exhausted")
    source_health._state["last_result_at"] = int(time.time()) - source_health.FRESH_FOR_SECONDS - 60
    assert source_health.get_status()["status"] == "degraded"


def test_mark_degraded_sets_reason_and_timestamp():
    source_health.mark_degraded("Anakin credits exhausted")
    status = source_health.get_status()
    assert status["degraded"] is True
    assert status["reason"] == "Anakin credits exhausted"
    assert status["since"] is not None


def test_mark_degraded_twice_keeps_original_since_timestamp():
    source_health.mark_degraded("first failure")
    first_since = source_health.get_status()["since"]
    source_health.mark_degraded("second failure, still down")
    status = source_health.get_status()
    # "since" should reflect when it FIRST went down, not the latest failure —
    # otherwise a banner showing "degraded since X" would reset on every
    # subsequent failed search instead of tracking the actual outage start.
    assert status["since"] == first_since
    assert status["reason"] == "second failure, still down"


def test_mark_healthy_clears_state():
    source_health.mark_degraded("some failure")
    source_health.mark_healthy()
    status = source_health.get_status()
    assert status["status"] == "ok"
    assert status["degraded"] is False
    assert status["reason"] is None
    assert status["since"] is None


def test_mark_degraded_returns_true_on_first_transition():
    assert source_health.mark_degraded("first failure") is True


def test_mark_degraded_returns_false_while_already_degraded():
    source_health.mark_degraded("first failure")
    assert source_health.mark_degraded("still failing") is False


def test_mark_degraded_returns_true_again_after_recovering():
    source_health.mark_degraded("first outage")
    source_health.mark_healthy()
    assert source_health.mark_degraded("second outage") is True
