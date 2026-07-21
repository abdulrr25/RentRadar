import pytest
import pytest_asyncio
import db
import alerts_store


@pytest_asyncio.fixture
async def fresh_db(monkeypatch):
    """Each test gets its own isolated in-memory DB — no cross-test state, no files to clean up."""
    monkeypatch.setattr(db, "DB_PATH", ":memory:")
    await db.init_db()
    yield
    await db.close_db()


@pytest.mark.asyncio
async def test_create_and_confirm_flow(fresh_db):
    search_id = await alerts_store.create_saved_search("+919876543210", "Bellandur", "2BHK", 25000)
    assert search_id

    # Not confirmed yet — shouldn't show up in the active/confirmed list the worker uses
    assert await alerts_store.list_active_confirmed() == []

    confirmed_id = await alerts_store.confirm_latest_for_phone("+919876543210")
    assert confirmed_id == search_id

    active = await alerts_store.list_active_confirmed()
    assert len(active) == 1
    assert active[0]["id"] == search_id
    assert active[0]["locality"] == "Bellandur"


@pytest.mark.asyncio
async def test_confirm_with_no_pending_search_returns_none(fresh_db):
    assert await alerts_store.confirm_latest_for_phone("+910000000000") is None


@pytest.mark.asyncio
async def test_confirm_picks_most_recent_pending_search(fresh_db):
    await alerts_store.create_saved_search("+919876543210", "Whitefield", "1BHK", 18000)
    second_id = await alerts_store.create_saved_search("+919876543210", "Bellandur", "2BHK", 25000)

    confirmed_id = await alerts_store.confirm_latest_for_phone("+919876543210")
    assert confirmed_id == second_id


@pytest.mark.asyncio
async def test_deactivate_removes_from_active_list(fresh_db):
    search_id = await alerts_store.create_saved_search("+919876543210", "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_latest_for_phone("+919876543210")
    assert len(await alerts_store.list_active_confirmed()) == 1

    ok = await alerts_store.deactivate(search_id)
    assert ok is True
    assert await alerts_store.list_active_confirmed() == []


@pytest.mark.asyncio
async def test_deactivate_nonexistent_id_returns_false(fresh_db):
    assert await alerts_store.deactivate("does-not-exist") is False


@pytest.mark.asyncio
async def test_seen_listings_dedup(fresh_db):
    search_id = await alerts_store.create_saved_search("+919876543210", "Bellandur", "2BHK", 25000)

    assert await alerts_store.has_seen(search_id, "abc123") is False
    await alerts_store.mark_seen(search_id, "abc123")
    assert await alerts_store.has_seen(search_id, "abc123") is True

    # Marking the same ref twice must not raise (INSERT OR IGNORE)
    await alerts_store.mark_seen(search_id, "abc123")


@pytest.mark.asyncio
async def test_mark_checked_sets_timestamp(fresh_db):
    search_id = await alerts_store.create_saved_search("+919876543210", "Bellandur", "2BHK", 25000)
    await alerts_store.mark_checked(search_id)
    # No exception, and the row still exists — mark_checked doesn't affect active/confirmed state
    await alerts_store.confirm_latest_for_phone("+919876543210")
    active = await alerts_store.list_active_confirmed()
    assert active[0]["id"] == search_id
