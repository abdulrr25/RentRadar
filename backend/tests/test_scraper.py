from tools.scraper import _matches_domain


def test_matches_domain_true_for_exact_host():
    assert _matches_domain("https://www.nobroker.in/property/rent/123", "nobroker.in") is True


def test_matches_domain_true_for_subdomain():
    assert _matches_domain("https://housing.com/rent/456", "housing.com") is True


def test_matches_domain_false_for_cross_domain_url():
    # This is the exact bug found live: a "site:nobroker.in" search
    # returning a housing.com URL, which must NOT be trusted as NoBroker's.
    assert _matches_domain("https://housing.com/rent/456", "nobroker.in") is False


def test_matches_domain_false_when_domain_only_appears_in_path_or_query():
    # A URL that merely mentions "nobroker.in" in its query string (e.g. a
    # comparison/aggregator page) must not be mistaken for an actual
    # nobroker.in page — only the real host counts.
    assert _matches_domain("https://example.com/compare?ref=nobroker.in", "nobroker.in") is False


def test_matches_domain_false_for_malformed_url():
    assert _matches_domain("not a url", "nobroker.in") is False


def test_matches_domain_case_insensitive():
    assert _matches_domain("https://WWW.NoBroker.IN/x", "nobroker.in") is True
