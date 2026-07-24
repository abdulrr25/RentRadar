import json
import time

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import db
import briefs_store
import main
import query_cache


@pytest_asyncio.fixture
async def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATABASE_URL", f"file:{tmp_path / 'test.db'}")
    await db.init_db()
    yield
    await db.close_db()


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATABASE_URL", f"file:{tmp_path / 'test.db'}")
    main.limiter.reset()
    query_cache.clear()
    with TestClient(main.app) as c:
        yield c


# ── store round-trip ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_get_brief(fresh_db):
    brief_json = json.dumps({"locality": "Bellandur", "top_listings": []})
    brief_id = await briefs_store.save_brief("Bellandur", "2BHK", 25000, brief_json)
    assert len(brief_id) == 8

    record = await briefs_store.get_brief(brief_id)
    assert record is not None
    assert record["locality"] == "Bellandur"
    assert record["bhk"] == "2BHK"
    assert record["max_rent"] == 25000
    assert record["brief"] == brief_json


@pytest.mark.asyncio
async def test_get_unknown_brief_returns_none(fresh_db):
    assert await briefs_store.get_brief("nope1234") is None


@pytest.mark.asyncio
async def test_expired_brief_not_returned_and_swept(fresh_db):
    brief_id = await briefs_store.save_brief("Bellandur", "2BHK", 25000, "{}")
    # Age the row past the TTL directly in the DB
    conn = db.get_conn()
    await conn.execute(
        "UPDATE briefs SET created_at = ? WHERE id = ?",
        (int(time.time()) - briefs_store._TTL_SECONDS - 60, brief_id),
    )

    assert await briefs_store.get_brief(brief_id) is None

    # The next save runs the inline sweep, which should delete the aged row
    await briefs_store.save_brief("Whitefield", "1BHK", 18000, "{}")
    result = await conn.execute("SELECT 1 FROM briefs WHERE id = ?", (brief_id,))
    assert not result.rows


# ── GET /brief/{id} endpoint ─────────────────────────────────────────────────

def test_brief_endpoint_404_for_unknown_id(client):
    assert client.get("/brief/doesnotexist").status_code == 404


def test_brief_endpoint_404_for_oversized_id(client):
    assert client.get(f"/brief/{'x' * 100}").status_code == 404


# ── share event in /search stream ────────────────────────────────────────────

def _sse_events(text: str):
    return [json.loads(l[6:]) for l in text.split("\n") if l.startswith("data: ")]


def test_search_emits_share_event_and_brief_is_fetchable(client, monkeypatch):
    async def fake_ainvoke(state):
        return {
            **state,
            "raw_data": [{"source": "NoBroker", "status": "ok"}],
            "brief": json.dumps({"locality": "Bellandur", "search_summary": "2BHK brief", "top_listings": []}),
        }

    monkeypatch.setattr(main.agent, "ainvoke", fake_ainvoke)

    res = client.post("/search", json={"query": "2BHK near Bellandur under 25000"})
    events = _sse_events(res.text)
    types = [e["type"] for e in events]
    assert types == ["parsed", "fetching", "source_complete", "brief", "share", "done"]

    share_id = next(e for e in events if e["type"] == "share")["id"]
    fetched = client.get(f"/brief/{share_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["locality"] == "Bellandur"
    assert json.loads(body["brief"])["search_summary"] == "2BHK brief"


def test_search_skips_share_for_unavailable_sources(client, monkeypatch):
    async def fake_ainvoke(state):
        return {
            **state,
            "raw_data": [{"source": "NoBroker", "status": "error"}],
            "brief": json.dumps({"sources_unavailable": True, "locality": "Bellandur"}),
        }

    monkeypatch.setattr(main.agent, "ainvoke", fake_ainvoke)

    res = client.post("/search", json={"query": "2BHK near Bellandur under 25000"})
    types = [e["type"] for e in _sse_events(res.text)]
    assert "share" not in types
    assert types[-1] == "done"
