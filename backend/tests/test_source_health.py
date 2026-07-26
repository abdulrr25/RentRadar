import source_health


def setup_function():
    # Module-level global — reset before every test regardless of order.
    source_health.mark_healthy()


def test_starts_healthy():
    assert source_health.get_status() == {"degraded": False, "reason": None, "since": None}


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
    assert source_health.get_status() == {"degraded": False, "reason": None, "since": None}


def test_mark_degraded_returns_true_on_first_transition():
    assert source_health.mark_degraded("first failure") is True


def test_mark_degraded_returns_false_while_already_degraded():
    source_health.mark_degraded("first failure")
    assert source_health.mark_degraded("still failing") is False


def test_mark_degraded_returns_true_again_after_recovering():
    source_health.mark_degraded("first outage")
    source_health.mark_healthy()
    assert source_health.mark_degraded("second outage") is True
