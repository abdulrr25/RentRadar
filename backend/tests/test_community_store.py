import time

import pytest
import pytest_asyncio

import db
import community_store


@pytest_asyncio.fixture
async def fresh_db(monkeypatch, tmp_path):
    """Per-test isolated DB file — see test_alerts_store.py for why."""
    monkeypatch.setattr(db, "DATABASE_URL", f"file:{tmp_path / 'test.db'}")
    await db.init_db()
    yield
    await db.close_db()


@pytest.mark.asyncio
async def test_create_then_search_round_trip(fresh_db):
    await community_store.create_listing(
        "chat1", "Bellandur", "2BHK", 22000, "Spacious 2BHK, owner direct, near ORR"
    )
    results = await community_store.search_listings("Bellandur", "2BHK", 25000)
    assert len(results) == 1
    assert results[0]["locality"] == "Bellandur"
    assert results[0]["rent"] == 22000
    assert "owner direct" in results[0]["description"]


@pytest.mark.asyncio
async def test_search_requires_exact_locality_match(fresh_db):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 22000, "desc")
    assert await community_store.search_listings("Koramangala", "2BHK", 25000) == []


@pytest.mark.asyncio
async def test_search_requires_exact_bhk_match(fresh_db):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 22000, "desc")
    assert await community_store.search_listings("Bellandur", "3BHK", 25000) == []


@pytest.mark.asyncio
async def test_search_excludes_over_budget_listings(fresh_db):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 30000, "desc")
    assert await community_store.search_listings("Bellandur", "2BHK", 25000) == []


@pytest.mark.asyncio
async def test_search_excludes_listings_below_min_rent(fresh_db):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 12000, "cheap")
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 24000, "in range")

    results = await community_store.search_listings("Bellandur", "2BHK", 30000, min_rent=20000)
    assert [r["rent"] for r in results] == [24000]


@pytest.mark.asyncio
async def test_search_without_min_rent_keeps_everything_in_budget(fresh_db):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 12000, "cheap")
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 24000, "pricier")

    results = await community_store.search_listings("Bellandur", "2BHK", 30000)
    assert sorted(r["rent"] for r in results) == [12000, 24000]


@pytest.mark.asyncio
async def test_search_excludes_expired_listings(fresh_db, monkeypatch):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 22000, "desc")

    # Jump time forward past the expiry window instead of waiting for it.
    future = time.time() + community_store._EXPIRY_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: future)

    assert await community_store.search_listings("Bellandur", "2BHK", 25000) == []


@pytest.mark.asyncio
async def test_count_recent_by_chat(fresh_db):
    assert await community_store.count_recent_by_chat("chat1") == 0
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 22000, "desc")
    await community_store.create_listing("chat1", "Indiranagar", "1BHK", 18000, "desc")
    await community_store.create_listing("chat2", "Bellandur", "2BHK", 22000, "desc")
    assert await community_store.count_recent_by_chat("chat1") == 2
    assert await community_store.count_recent_by_chat("chat2") == 1


@pytest.mark.asyncio
async def test_count_recent_by_chat_excludes_old_submissions(fresh_db, monkeypatch):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 22000, "desc")

    future = time.time() + community_store._SUBMIT_WINDOW_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: future)

    assert await community_store.count_recent_by_chat("chat1") == 0


@pytest.mark.asyncio
async def test_purge_expired_removes_only_expired_rows(fresh_db, monkeypatch):
    await community_store.create_listing("chat1", "Bellandur", "2BHK", 22000, "still fresh")

    future = time.time() + community_store._EXPIRY_SECONDS + 1
    monkeypatch.setattr(time, "time", lambda: future)
    await community_store.create_listing("chat1", "Indiranagar", "1BHK", 18000, "created after the jump")

    removed = await community_store.purge_expired()
    assert removed == 1

    remaining = await community_store.search_listings("Indiranagar", "1BHK", 25000)
    assert len(remaining) == 1
