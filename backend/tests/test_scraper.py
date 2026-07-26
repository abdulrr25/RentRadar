from tools.scraper import _matches_domain, _is_generic_listing_page


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


def test_generic_listing_page_detects_real_nobroker_search_url():
    # Captured live: a "1BHK in Kadubeesanahalli" search returning this as a
    # "listing" — it's actually NoBroker's locality-wide search results page
    # (searchParam is a base64-encoded location filter), not one specific
    # flat. This is the exact "fake/half information" a user reported.
    url = (
        "https://www.nobroker.in/property/rent/bangalore/Kadubeesanahalli"
        "?searchParam=W3sibGF0IjoxMi45Mzk3MTU1LCJsb24iOjc3LjY5NTI3MzIsInNob3dNYXAiOmZhbHNlLCJwbGFjZUlkIjoiQ2hJSjBVaXBBYklUcmpzUjh1UGdhaDhxYWl3IiwicGxhY2VOYW1lIjoiS2FkdWJlZXNhbmFoYWxsaSIsImNpdHkiOiJiYW5nYWxvcmUifV0="
        "&lat_lng=12.934665000000000000,77.697564999999940000"
    )
    assert _is_generic_listing_page(url) is True


def test_generic_listing_page_detects_search_url_with_type_filter():
    url = (
        "https://www.nobroker.in/property/rent/bangalore/Kadubeesanahalli,%20Bangalore"
        "?searchParam=W3sibGF0IjoxMi45Mzk0MTM3fQ==&lat_lng=12.9397155,77.6952732&type=BHK1"
    )
    assert _is_generic_listing_page(url) is True


def test_generic_listing_page_false_for_real_specific_listing():
    # Captured live in the same search — a genuine single-property page.
    url = "https://housing.com/rent/19960137-750-sqft-1-bhk-apartment-on-rent-in-kadubeesanahalli-bengaluru"
    assert _is_generic_listing_page(url) is False


def test_generic_listing_page_case_insensitive():
    url = "https://www.nobroker.in/property/rent/bangalore/x?SearchParam=abc"
    assert _is_generic_listing_page(url) is True
