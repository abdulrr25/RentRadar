from prompts import extract_price_int, _extract_price, build_context


def test_extracts_price_per_month_with_rupee_symbol():
    assert extract_price_int("Spacious 2BHK ₹25,000/month, owner direct") == 25000


def test_extracts_price_with_rs_and_per_month_words():
    assert extract_price_int("Rent Rs 18000 per month, no brokerage") == 18000


def test_ignores_lakh_prices():
    assert extract_price_int("Selling for 45 lakh, negotiable") is None


def test_ignores_crore_prices():
    assert extract_price_int("2.5 crore, ready to move") is None


def test_rejects_amount_below_valid_range():
    # Below ₹3,000 is treated as noise, not a real Bangalore rent
    assert extract_price_int("deposit ₹2,000/month token") is None


def test_rejects_amount_above_valid_range():
    assert extract_price_int("₹500,000/month luxury villa") is None


def test_no_price_in_text_returns_none():
    assert extract_price_int("Nice flat, great locality, contact owner") is None


def test_extract_price_wraps_int_version_with_tag():
    assert _extract_price("₹22,000/month") == "[PRICE: ₹22,000]"
    assert _extract_price("no price here") == ""


def test_build_context_maps_refs_to_source_and_url():
    raw_data = [
        {
            "source": "NoBroker",
            "status": "ok",
            "results": [
                {"title": "2BHK Bellandur", "url": "https://nobroker.in/x", "snippet": "₹25,000/month"},
            ],
        },
        {"source": "Hacker News", "status": "ok", "data": "People say Bellandur traffic is bad"},
    ]
    query = {"bhk": "2BHK", "locality": "Bellandur", "max_rent": 25000}

    context, ref_map = build_context(raw_data, query)

    assert "NB1" in ref_map
    assert ref_map["NB1"] == {"url": "https://nobroker.in/x", "source": "NoBroker"}
    assert "Bellandur" in context
    assert "traffic is bad" in context


def test_build_context_marks_unavailable_sources():
    raw_data = [{"source": "NoBroker", "status": "error", "results": []}]
    query = {"bhk": "1BHK", "locality": "Whitefield", "max_rent": 18000}

    context, ref_map = build_context(raw_data, query)

    assert ref_map == {}
    assert "no results" in context
