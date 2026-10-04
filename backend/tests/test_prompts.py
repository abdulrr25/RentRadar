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
        {"source": "Hacker News", "status": "ok", "items": [
            {"title": "People say Bellandur traffic is bad",
             "url": "https://news.ycombinator.com/item?id=1",
             "published_at": 1760000000, "mentions_locality": True},
        ]},
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


def test_sentiment_items_get_refs_with_date_and_locality_scope():
    raw_data = [
        {"source": "Google News", "status": "ok", "items": [
            {"title": "Bellandur rents climb 12% this quarter",
             "url": "https://news.example/1",
             "published_at": 1760000000, "mentions_locality": True},
            {"title": "Bengaluru leasing fraud leaves tenants stranded",
             "url": "https://news.example/2",
             "published_at": 1750000000, "mentions_locality": False},
        ]},
    ]
    query = {"bhk": "2BHK", "locality": "Bellandur", "max_rent": 25000}

    context, ref_map = build_context(raw_data, query)

    assert ref_map["GN1"]["url"] == "https://news.example/1"
    assert ref_map["GN1"]["mentions_locality"] is True
    assert ref_map["GN2"]["mentions_locality"] is False

    # The model needs both markers to word a claim honestly — see the
    # LOCALITY RULE in SYSTEM_PROMPT.
    assert "[about Bellandur]" in context
    assert "[Bengaluru-wide]" in context
    assert "2025" in context or "2026" in context  # a real date, not "undated"


def test_sentiment_source_with_no_items_is_marked_unavailable():
    context, ref_map = build_context(
        [{"source": "Hacker News", "status": "error", "items": []}],
        {"bhk": "2BHK", "locality": "Bellandur", "max_rent": 25000},
    )
    assert "[Hacker News]: unavailable" in context
    assert ref_map == {}


def test_build_context_never_mentions_community_source():
    # Community listings are already-structured and merged directly into
    # top_listings after the LLM call (agent.py's synthesis_node) — they
    # must never reach the prompt itself, successful or not, since there's
    # no "data" (sentiment text) field on them to show under AREA SENTIMENT.
    query = {"bhk": "2BHK", "locality": "Bellandur", "max_rent": 25000}

    ok_context, _ = build_context(
        [{"source": "Community", "status": "ok", "listings": [{"rent": 22000}]}], query
    )
    assert "Community" not in ok_context

    empty_context, _ = build_context(
        [{"source": "Community", "status": "error", "listings": []}], query
    )
    assert "Community" not in empty_context
