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


def test_generic_listing_page_detects_nobroker_insite_search_page():
    # NoBroker's own in-site search lives under /property/rent/bangalore/... —
    # it IS under /property/ but is a results page, not one unit, so the
    # allowlist's (?!rent/) must exclude it.
    url = "https://www.nobroker.in/property/rent/bangalore/some-area?searchParam=abc"
    assert _is_generic_listing_page(url, "whatever", "nobroker.in") is True


# ── gaps found in the live-corpus audit (10 localities x 3 portals) ──────────

def test_generic_listing_page_detects_olx_bare_geo_page():
    # Captured live: a bare locality page with no category — slipped through
    # the old blocklist entirely (no /q- and no _c<id>).
    url = "https://www.olx.in/bellandur_g5313788"
    assert _is_generic_listing_page(url, "Bellandur Free classifieds - OLX India", "olx.in") is True


def test_generic_listing_page_detects_olx_category_page_with_query_string():
    # Captured live: a category page with a trailing ?filter= — the old
    # "_c\d+(?:/|$)" anchor was defeated by the "?".
    url = "https://www.olx.in/bellandur_g5313788/for-rent-houses-apartments_c1723?filter=rooms_eq_2"
    assert _is_generic_listing_page(url, "2 BHK for rent", "olx.in") is True


def test_generic_listing_page_detects_olx_pg_guest_house_page():
    # Captured live: a PG / shared-room browse page — not a flat at all.
    url = "https://www.olx.in/bellandur_g5313788/pg-guest-houses_c1449?filter=subtype_eq_roommate"
    assert _is_generic_listing_page(url, "PG in Bellandur", "olx.in") is True


def test_generic_listing_page_false_for_olx_new_format_item():
    # Captured live: OLX's current single-ad shape. Note "c1723" appears in
    # the slug with hyphens, not "_c1723" — it must not be mistaken for a
    # category page.
    url = "https://www.olx.in/item/for-rent-houses-apartments-c1723-2-bhk-flats-apartments-1180-sq-ft-in-bellandur"
    assert _is_generic_listing_page(url, "2 BHK Flats & Apartments", "olx.in") is False


def test_generic_listing_page_false_for_olx_item_under_locale_prefix():
    url = "https://www.olx.in/en-in/item/for-rent-houses-apartments-c1723-1-bhk-flats-apartments-650-sq-ft"
    assert _is_generic_listing_page(url, "1 BHK", "olx.in") is False


def test_generic_listing_page_detects_nobroker_house_locality_page():
    # Captured live: the old blocklist only matched "flats", so the "house"
    # variant of the same locality browse page was wrongly kept.
    url = "https://www.nobroker.in/2-bhk-house-for-rent-in-indira-nagar-bangalore"
    assert _is_generic_listing_page(url, "2 BHK House for Rent in Indiranagar", "nobroker.in") is True


def test_generic_listing_page_false_for_genuine_nobroker_property():
    # Captured live: a genuine individual property, always under /property/.
    url = "https://www.nobroker.in/property/2-bhk-apartment-for-rent-in-bellandur-bangalore-for-rs-23000/8aa9b"
    assert _is_generic_listing_page(url, "2 BHK Apartment for Rent in Bellandur", "nobroker.in") is False


def test_generic_listing_page_detects_housing_project_rpid_page():
    # Captured live: a whole-building rental page (named by project, no unit
    # specifics, "rpid" = project id, URL is /rent-<slug> not /rent/<id>-).
    url = "https://housing.com/rent-assetz-east-point-for-rent-in-bellandur-bengaluru-rpid-AG61eAH0"
    assert _is_generic_listing_page(url, "Assetz East Point", "housing.com") is True


def test_generic_listing_page_detects_housing_overview_and_flatmates_pages():
    overview = "https://housing.com/bellandur-bengaluru-overview-P29di09q225s3j6s1"
    flatmates = "https://housing.com/flatmates/shared-accomodation-for-rent-in-bellandur-bengaluru-P29"
    assert _is_generic_listing_page(overview, "Bellandur Overview", "housing.com") is True
    assert _is_generic_listing_page(flatmates, "Shared accommodation", "housing.com") is True


def test_title_fallback_applies_only_to_domains_without_an_allowlist():
    # The title heuristics are a defensive net for a hypothetical future
    # source with no URL allowlist — exercised here via an unknown domain.
    assert _is_generic_listing_page(
        "https://example.com/some-results-page", "2 BHK Flats for Rent in Bellandur 120+", "example.com"
    ) is True
    # ...and a price in the title marks a specific listing, so it's kept.
    assert _is_generic_listing_page(
        "https://example.com/listing", "2 BHK Flat for Rent in Bellandur for Rs 25,000", "example.com"
    ) is False
