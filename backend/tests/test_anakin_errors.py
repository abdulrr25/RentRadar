from tools.anakin_errors import is_credit_exhausted


def test_402_status_is_credit_exhausted():
    assert is_credit_exhausted(402, "") is True


def test_body_mentions_credit():
    assert is_credit_exhausted(400, "Your credit balance is too low") is True


def test_body_mentions_quota():
    assert is_credit_exhausted(403, "Quota exceeded for this API key") is True


def test_body_mentions_insufficient_case_insensitive():
    assert is_credit_exhausted(400, "INSUFFICIENT FUNDS") is True


def test_unrelated_error_is_not_credit_exhausted():
    assert is_credit_exhausted(500, "Internal server error") is False


def test_network_error_with_no_status_or_body():
    assert is_credit_exhausted(None, "") is False
