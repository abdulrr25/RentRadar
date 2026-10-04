import json

import pytest

import agent


def _state(max_rent):
    return {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": max_rent},
        "raw_data": [
            {"source": "NoBroker", "status": "ok", "results": [
                {"title": "2BHK", "url": "https://nobroker.in/x", "snippet": "Rent 20000/month"}
            ]},
        ],
    }


def _fake_groq(content: str):
    class _FakeMessage:
        pass

    class _FakeChoice:
        pass

    class _FakeCompletion:
        pass

    class _FakeGroq:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    msg = _FakeMessage()
                    msg.content = content
                    choice = _FakeChoice()
                    choice.message = msg
                    completion = _FakeCompletion()
                    completion.choices = [choice]
                    return completion

    return _FakeGroq()


@pytest.mark.asyncio
async def test_over_budget_listing_is_dropped(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": 30000, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    result = await agent.synthesis_node(_state(max_rent=25000))
    brief = json.loads(result["brief"])

    assert brief["top_listings"] == []


@pytest.mark.asyncio
async def test_max_rent_zero_still_filters_everything(monkeypatch):
    """Regression: `if max_rent:` treated a real budget of ₹0 as "no filter",
    silently keeping every listing regardless of price."""
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": 5000, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    result = await agent.synthesis_node(_state(max_rent=0))
    brief = json.loads(result["brief"])

    assert brief["top_listings"] == []
    assert "budget_note" in brief


@pytest.mark.asyncio
async def test_comma_formatted_rent_string_is_parsed_and_filtered(monkeypatch):
    """Regression: the model can echo a comma-formatted price (it sees
    "[PRICE: ₹45,000]" tags in its own input) — int("45,000") used to raise
    and the listing was wrongly kept as "unknown price"."""
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": "45,000", "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    result = await agent.synthesis_node(_state(max_rent=25000))
    brief = json.loads(result["brief"])

    assert brief["top_listings"] == []


@pytest.mark.asyncio
async def test_below_min_rent_listing_is_dropped(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": 12000, "source": "NoBroker"},
        {"rank": 2, "rent": 24000, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=30000)
    state["query"]["min_rent"] = 20000

    result = await agent.synthesis_node(state)
    brief = json.loads(result["brief"])

    assert [l["rent"] for l in brief["top_listings"]] == [24000]


@pytest.mark.asyncio
async def test_unknown_price_listing_kept_even_with_a_min_rent(monkeypatch):
    # Same reasoning as the max bound: an unknown price can't be shown to be
    # out of range, so dropping it would manufacture "no listings found".
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": None, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=30000)
    state["query"]["min_rent"] = 20000

    result = await agent.synthesis_node(state)
    assert len(json.loads(result["brief"])["top_listings"]) == 1


@pytest.mark.asyncio
async def test_budget_note_mentions_both_bounds_for_a_range(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": 90000, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=30000)
    state["query"]["min_rent"] = 20000

    result = await agent.synthesis_node(state)
    note = json.loads(result["brief"])["budget_note"]

    assert "20,000" in note and "30,000" in note


@pytest.mark.asyncio
async def test_unknown_price_listing_is_kept(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": None, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    result = await agent.synthesis_node(_state(max_rent=25000))
    brief = json.loads(result["brief"])

    assert len(brief["top_listings"]) == 1
    assert brief["top_listings"][0]["rent"] is None


@pytest.mark.asyncio
async def test_non_dict_listing_entry_does_not_crash(monkeypatch):
    """Regression: a malformed completion putting a bare string in
    top_listings used to crash with AttributeError before the isinstance
    filter (which ran too late) ever got to remove it."""
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        "not a listing object",
        {"rank": 1, "rent": 20000, "source": "NoBroker"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    result = await agent.synthesis_node(_state(max_rent=25000))
    brief = json.loads(result["brief"])

    assert brief.get("error") != "synthesis_failed"
    assert len(brief["top_listings"]) == 1


# ── Evidence rule: no citation, no claim ────────────────────────────────────

def _state_with_news(max_rent=25000):
    """A state whose Google News source carries one citable headline (GN1)."""
    state = _state(max_rent)
    state["raw_data"].append({
        "source": "Google News", "status": "ok", "items": [
            {"title": "Bengaluru leasing fraud leaves 200 tenants stranded",
             "url": "https://news.example/fraud",
             "published_at": 1760000000, "mentions_locality": False},
        ],
    })
    return state


@pytest.mark.asyncio
async def test_claim_citing_a_real_headline_keeps_its_source(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "scam_alerts": [{"text": "A leasing fraud was reported in Bengaluru", "ref": "GN1"}],
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    brief = json.loads((await agent.synthesis_node(_state_with_news()))["brief"])

    assert len(brief["scam_alerts"]) == 1
    alert = brief["scam_alerts"][0]
    assert alert["url"] == "https://news.example/fraud"
    assert alert["published_at"] == 1760000000
    # The headline is about the city, not the searched locality — the UI
    # needs this to avoid implying Bellandur specifically.
    assert alert["locality_specific"] is False


@pytest.mark.asyncio
async def test_claim_citing_an_unknown_ref_is_dropped(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "red_flags": [{"text": "Invented problem", "ref": "GN99"}],
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    brief = json.loads((await agent.synthesis_node(_state_with_news()))["brief"])
    assert brief["red_flags"] == []


@pytest.mark.asyncio
async def test_uncited_plain_string_claim_is_dropped(monkeypatch):
    # The shape the model used to emit. Without a ref there is no source,
    # so it can't ship.
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "green_flags": ["Great metro connectivity"],
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    brief = json.loads((await agent.synthesis_node(_state_with_news()))["brief"])
    assert brief["green_flags"] == []


@pytest.mark.asyncio
async def test_uncited_trend_note_drops_the_trend_arrow_too(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "price_trend": "rising",
        "trend_note": {"text": "Rents are climbing", "ref": "GN42"},
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    brief = json.loads((await agent.synthesis_node(_state_with_news()))["brief"])

    assert "trend_note" not in brief
    assert "price_trend" not in brief, "a trend arrow with nothing behind it is worse than none"


@pytest.mark.asyncio
async def test_score_dimensions_without_evidence_are_dropped(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "locality_scores": {"safety": 8.2, "traffic": 5.0, "overall": 6.6},
        "scores_evidence": {"safety": "GN1"},  # traffic cites nothing
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    brief = json.loads((await agent.synthesis_node(_state_with_news()))["brief"])

    assert brief["locality_scores"]["safety"] == 8.2
    assert "traffic" not in brief["locality_scores"]
    assert brief["locality_scores"]["overall"] == 6.6


@pytest.mark.asyncio
async def test_overall_score_dropped_when_nothing_is_evidenced(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "locality_scores": {"safety": 8.2, "overall": 7.0},
        "scores_evidence": {},
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    brief = json.loads((await agent.synthesis_node(_state_with_news()))["brief"])
    assert brief["locality_scores"] == {}


@pytest.mark.asyncio
async def test_hn_signal_dropped_when_hacker_news_empty(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "hn_signal": "Tech workers say Bellandur is great",
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    # Default _state has no Hacker News source at all → treated as empty.
    brief = json.loads((await agent.synthesis_node(_state(max_rent=25000)))["brief"])
    assert "hn_signal" not in brief


@pytest.mark.asyncio
async def test_hn_signal_kept_when_hacker_news_has_items(monkeypatch):
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "hn_signal": "Tech workers note long commutes",
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=25000)
    state["raw_data"].append({
        "source": "Hacker News", "status": "ok",
        "items": [{"title": "Bangalore commute thread", "url": "https://news.ycombinator.com/item?id=1",
                   "published_at": 1760000000, "mentions_locality": False}],
    })
    brief = json.loads((await agent.synthesis_node(state))["brief"])
    assert brief["hn_signal"] == "Tech workers note long commutes"


# ── Community listings merge ────────────────────────────────────────────────

def _community_listing(rent=22000, highlight="Owner direct, near metro"):
    return {
        "locality_detail": "Bellandur (community submission)",
        "rent": rent,
        "bhk": "2BHK",
        "source": "Community",
        "highlights": [highlight],
        "url": None,
    }


@pytest.mark.asyncio
async def test_community_listing_merges_into_top_listings(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": 20000, "source": "NoBroker", "ref": "NB1"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=25000)
    state["raw_data"].append(
        {"source": "Community", "status": "ok", "listings": [_community_listing()]}
    )

    result = await agent.synthesis_node(state)
    brief = json.loads(result["brief"])

    sources = {l["source"] for l in brief["top_listings"]}
    assert "NoBroker" in sources
    assert "Community" in sources


@pytest.mark.asyncio
async def test_community_listing_still_subject_to_budget_filter(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": []})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=20000)
    state["raw_data"].append(
        {"source": "Community", "status": "ok", "listings": [_community_listing(rent=30000)]}
    )

    result = await agent.synthesis_node(state)
    brief = json.loads(result["brief"])

    assert brief["top_listings"] == []


@pytest.mark.asyncio
async def test_verdict_overridden_when_only_community_has_listings(monkeypatch):
    # The LLM wrote this verdict believing top_listings was empty — once a
    # community listing is the only reason the final list isn't, that
    # prose is stale and must not stand.
    content = json.dumps({
        "locality": "Bellandur", "top_listings": [],
        "verdict": "No listings were found in this area within your budget.",
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=25000)
    state["raw_data"].append(
        {"source": "Community", "status": "ok", "listings": [_community_listing()]}
    )

    result = await agent.synthesis_node(state)
    brief = json.loads(result["brief"])

    assert brief["verdict"] != "No listings were found in this area within your budget."
    assert "Telegram" in brief["verdict"]


@pytest.mark.asyncio
async def test_verdict_not_overridden_when_llm_already_had_listings(monkeypatch):
    # The LLM's own verdict is left alone when it already had real
    # (non-community) listings to reason about.
    content = json.dumps({
        "locality": "Bellandur",
        "top_listings": [{"rank": 1, "rent": 20000, "source": "NoBroker", "ref": "NB1"}],
        "verdict": "A solid NoBroker option is available within budget.",
    })
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=25000)
    state["raw_data"].append(
        {"source": "Community", "status": "ok", "listings": [_community_listing()]}
    )

    result = await agent.synthesis_node(state)
    brief = json.loads(result["brief"])

    assert brief["verdict"] == "A solid NoBroker option is available within budget."


@pytest.mark.asyncio
async def test_empty_community_result_is_not_merged(monkeypatch):
    content = json.dumps({"locality": "Bellandur", "top_listings": [
        {"rank": 1, "rent": 20000, "source": "NoBroker", "ref": "NB1"},
    ]})
    monkeypatch.setattr(agent, "_groq_client", lambda: _fake_groq(content))

    state = _state(max_rent=25000)
    state["raw_data"].append(
        {"source": "Community", "status": "error", "listings": [],
         "error": "No community listings matched this search"}
    )

    result = await agent.synthesis_node(state)
    brief = json.loads(result["brief"])

    assert all(l["source"] != "Community" for l in brief["top_listings"])
