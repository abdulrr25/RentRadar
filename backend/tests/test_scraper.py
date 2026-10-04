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


def test_matches_domain_false_for_lookalike_suffix():
    # "nobroker.in" is a substring of this host but it is not nobroker.in or
    # a subdomain of it — a naive `expected_domain in netloc` check would
    # wrongly trust this as a real NoBroker page.
    assert _matches_domain("https://evilnobroker.in/x", "nobroker.in") is False


def test_matches_domain_false_for_lookalike_parent_domain():
    assert _matches_domain("https://nobroker.in.scam.com/x", "nobroker.in") is False


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
    assert _is_generic_listing_page(url, "Kadubeesanahalli Property", "nobroker.in") is True


def test_generic_listing_page_detects_search_url_with_type_filter():
    url = (
        "https://www.nobroker.in/property/rent/bangalore/Kadubeesanahalli,%20Bangalore"
        "?searchParam=W3sibGF0IjoxMi45Mzk0MTM3fQ==&lat_lng=12.9397155,77.6952732&type=BHK1"
    )
    assert _is_generic_listing_page(url, "Kadubeesanahalli Property", "nobroker.in") is True


def test_generic_listing_page_false_for_real_specific_listing():
    # Captured live in the same search — a genuine single-property page: a
    # numeric listing ID up front, specific sqft, singular "apartment".
    url = "https://housing.com/rent/19960137-750-sqft-1-bhk-apartment-on-rent-in-kadubeesanahalli-bengaluru"
    title = "750 sqft 1 BHK Apartment for Rent in Kadubeesanahalli, Bengaluru"
    assert _is_generic_listing_page(url, title, "housing.com") is False


def test_generic_listing_page_case_insensitive():
    url = "https://www.nobroker.in/property/rent/bangalore/x?SearchParam=abc"
    assert _is_generic_listing_page(url, "Some Property", "nobroker.in") is True


def test_generic_listing_page_detects_nobroker_locality_wide_page():
    # Captured live: site:nobroker.in search for "2BHK Bellandur" returning
    # this as a top result. Its own title says "Flats" (plural) and the
    # page itself lists a dozen+ differently-priced units — not one flat.
    url = "https://www.nobroker.in/2bhk-flats-for-rent-in-bellandur_bangalore"
    title = "2 BHK Flats for Rent in   Bellandur Bangalore - NoBroker"
    assert _is_generic_listing_page(url, title, "nobroker.in") is True


def test_generic_listing_page_detects_nobroker_project_wide_page():
    # Captured live: a whole-apartment-complex page ("197+" units), not one
    # flat, despite the URL naming a specific building ("Adarsh Rosewood").
    url = "https://www.nobroker.in/2bhk-flats-for-rent-in-adarsh-rosewood-bellandur-bangalore-prjtl"
    title = "2 BHK  Flats for Rent in   Bellandur, Bangalore - NoBroker 197+ "
    assert _is_generic_listing_page(url, title, "nobroker.in") is True


def test_generic_listing_page_detects_nobroker_for_sale_page():
    # Wrong transaction type entirely — must never surface in a rent search
    # even though the domain and BHK match.
    url = "https://www.nobroker.in/2bhk-flats-for-sale-in-bellandur_bangalore"
    assert _is_generic_listing_page(url, "2 BHK Flats for Sale in Bellandur Bangalore - NoBroker", "nobroker.in") is True


def test_generic_listing_page_detects_housing_city_wide_page():
    # Captured live: site:housing.com search for "2BHK Bellandur" returning
    # a whole-Bangalore results page (not even Bellandur-specific), with no
    # numeric listing ID in the URL.
    url = "https://housing.com/rent/2bhk-flats-for-rent-in-bangalore-karnataka-C4P38f9yfbk7p3m2h1f"
    title = "2 BHK Flats for Rent in Bangalore, Karnataka"
    assert _is_generic_listing_page(url, title, "housing.com") is True


def test_generic_listing_page_detects_housing_buy_page():
    url = "https://housing.com/in/buy/bengaluru/2bhk-flats-fid"
    assert _is_generic_listing_page(url, "2 BHK Flats for Sale in Bengaluru", "housing.com") is True


def test_generic_listing_page_detects_olx_category_page():
    # Captured live: a bare category/query browse page, not one ad.
    url = "https://www.olx.in/real-estate_c3/q-2-bhk-flats"
    assert _is_generic_listing_page(url, "2 BHK Flats - OLX", "olx.in") is True


def test_generic_listing_page_false_for_genuine_olx_ad():
    url = "https://www.olx.in/item/2bhk-semi-furnished-flat-for-rent-near-bellandur-iid-1234567890"
    title = "2BHK semi furnished flat for rent near Bellandur, fully furnished with parking"
    assert _is_generic_listing_page(url, title, "olx.in") is False


def test_generic_listing_page_detects_nobroker_any_bhk_locality_page():
    # Captured live, same search — the "any BHK" variant of the locality
    # page has no "2bhk-" prefix in the URL and no "BHK" in the title at
    # all, unlike the other NoBroker generic pages above.
    url = "https://www.nobroker.in/flats-for-rent-in-bellandur_bangalore"
    title = "Flats for Rent in Bellandur Bangalore - NoBroker"
    assert _is_generic_listing_page(url, title, "nobroker.in") is True


def test_generic_listing_page_detects_trailing_listing_count_regardless_of_domain():
    # The portal's own "<N>+" count is a strong signal on its own, even when
    # the URL shape itself doesn't match any known bad pattern for that
    # domain — a page the URL-only checks would have let through.
    url = "https://www.nobroker.in/property/rent/bangalore/some-building-xyz123"
    assert _is_generic_listing_page(url, "Flats available near Bellandur 85+", "nobroker.in") is True
