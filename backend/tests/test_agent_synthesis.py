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
