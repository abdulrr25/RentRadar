import time

import pytest
import pytest_asyncio
import db
import alerts_store


@pytest_asyncio.fixture
async def fresh_db(monkeypatch, tmp_path):
    """
    Each test gets its own isolated DB file — libsql_client's local ':memory:'
    mode doesn't persist state across separate execute() calls (each one
    appears to open a fresh connection to it), so a per-test temp file is
    used instead. tmp_path is unique per test, so isolation still holds.
    """
    monkeypatch.setattr(db, "DATABASE_URL", f"file:{tmp_path / 'test.db'}")
    await db.init_db()
    yield
    await db.close_db()


# ── webpush: immediate confirmation, no token ───────────────────────────────

@pytest.mark.asyncio
async def test_webpush_confirm_by_id_flow(fresh_db):
    search_id = await alerts_store.create_pending(
        "webpush", '{"endpoint":"https://x"}', None, "Bellandur", "2BHK", 25000
    )
    assert await alerts_store.list_active_confirmed() == []

    ok = await alerts_store.confirm_by_id(search_id)
    assert ok is True

    active = await alerts_store.list_active_confirmed()
    assert len(active) == 1
    assert active[0]["channel"] == "webpush"
    assert active[0]["target"] == '{"endpoint":"https://x"}'


@pytest.mark.asyncio
async def test_confirm_by_id_nonexistent_returns_false(fresh_db):
    assert await alerts_store.confirm_by_id("does-not-exist") is False


# ── email / telegram: token-based confirmation ──────────────────────────────

@pytest.mark.asyncio
async def test_email_confirm_by_token_flow(fresh_db):
    search_id = await alerts_store.create_pending(
        "email", "user@example.com", "tok123", "Whitefield", "1BHK", 18000
    )
    assert await alerts_store.list_active_confirmed() == []

    confirmed_id = await alerts_store.confirm_by_token("tok123")
    assert confirmed_id == search_id

    active = await alerts_store.list_active_confirmed()
    assert len(active) == 1
    assert active[0]["target"] == "user@example.com"


@pytest.mark.asyncio
async def test_telegram_confirm_by_token_fills_in_target(fresh_db):
    # telegram: target is unknown at creation, only the confirm_token is set
    search_id = await alerts_store.create_pending(
        "telegram", None, "tok456", "Bellandur", "2BHK", 25000
    )
    confirmed_id = await alerts_store.confirm_by_token("tok456", target="123456789")
    assert confirmed_id == search_id

    active = await alerts_store.list_active_confirmed()
    assert active[0]["channel"] == "telegram"
    assert active[0]["target"] == "123456789"


@pytest.mark.asyncio
async def test_confirm_by_token_wrong_token_returns_none(fresh_db):
    await alerts_store.create_pending("email", "user@example.com", "tok123", "Bellandur", "2BHK", 25000)
    assert await alerts_store.confirm_by_token("wrong-token") is None


@pytest.mark.asyncio
async def test_confirm_by_token_cannot_be_reused(fresh_db):
    await alerts_store.create_pending("email", "user@example.com", "tok123", "Bellandur", "2BHK", 25000)
    first = await alerts_store.confirm_by_token("tok123")
    assert first is not None
    # Token was cleared on confirm — a second attempt (e.g. a duplicate
    # webhook delivery, or someone replaying a captured link) must not match.
    second = await alerts_store.confirm_by_token("tok123")
    assert second is None


# ── deactivate / list ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deactivate_removes_from_active_list(fresh_db):
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_by_id(search_id)
    assert len(await alerts_store.list_active_confirmed()) == 1

    ok = await alerts_store.deactivate(search_id)
    assert ok is True
    assert await alerts_store.list_active_confirmed() == []


@pytest.mark.asyncio
async def test_deactivate_nonexistent_id_returns_false(fresh_db):
    assert await alerts_store.deactivate("does-not-exist") is False


# ── seen_listings dedup ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seen_listings_dedup(fresh_db):
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)

    assert await alerts_store.has_seen(search_id, "abc123") is False
    await alerts_store.mark_seen(search_id, "abc123")
    assert await alerts_store.has_seen(search_id, "abc123") is True

    # Marking the same ref twice must not raise (INSERT OR IGNORE)
    await alerts_store.mark_seen(search_id, "abc123")


@pytest.mark.asyncio
async def test_mark_checked_does_not_affect_confirmed_state(fresh_db):
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_by_id(search_id)
    await alerts_store.mark_checked(search_id)
    active = await alerts_store.list_active_confirmed()
    assert active[0]["id"] == search_id


# ── seen_listings purge ──────────────────────────────────────────────────────

async def _seen_count() -> int:
    from db import get_conn
    result = await get_conn().execute("SELECT count(*) FROM seen_listings")
    return result.rows[0][0]


@pytest.mark.asyncio
async def test_purge_removes_rows_past_ttl(fresh_db):
    from db import get_conn
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_by_id(search_id)
    await alerts_store.mark_seen(search_id, "old-ref")

    # Backdate past the TTL rather than waiting 90 days.
    stale = int(time.time()) - alerts_store._SEEN_TTL_SECONDS - 60
    await get_conn().execute(
        "UPDATE seen_listings SET first_seen_at = ? WHERE ref_hash = 'old-ref'", (stale,)
    )

    removed = await alerts_store.purge_seen_listings()
    assert removed == 1
    assert await _seen_count() == 0


@pytest.mark.asyncio
async def test_purge_keeps_recent_rows_for_active_searches(fresh_db):
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_by_id(search_id)
    await alerts_store.mark_seen(search_id, "fresh-ref")

    removed = await alerts_store.purge_seen_listings()
    assert removed == 0
    # Still suppresses a duplicate notification — the whole point of the row.
    assert await alerts_store.has_seen(search_id, "fresh-ref") is True


@pytest.mark.asyncio
async def test_purge_removes_rows_belonging_to_deactivated_searches(fresh_db):
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_by_id(search_id)
    await alerts_store.mark_seen(search_id, "ref-1")
    await alerts_store.mark_seen(search_id, "ref-2")

    # Recent rows, but the search can never notify again — there is no
    # reactivate path, so its dedup ledger is pure dead weight.
    await alerts_store.deactivate(search_id)

    removed = await alerts_store.purge_seen_listings()
    assert removed == 2
    assert await _seen_count() == 0


@pytest.mark.asyncio
async def test_purge_does_not_touch_other_active_searches(fresh_db):
    dead = await alerts_store.create_pending("webpush", '{"endpoint":"a"}', None, "Bellandur", "2BHK", 25000)
    live = await alerts_store.create_pending("webpush", '{"endpoint":"b"}', None, "Koramangala", "1BHK", 20000)
    await alerts_store.confirm_by_id(dead)
    await alerts_store.confirm_by_id(live)
    await alerts_store.mark_seen(dead, "ref-dead")
    await alerts_store.mark_seen(live, "ref-live")
    await alerts_store.deactivate(dead)

    removed = await alerts_store.purge_seen_listings()
    assert removed == 1
    assert await alerts_store.has_seen(live, "ref-live") is True


@pytest.mark.asyncio
async def test_purge_on_empty_table_is_a_noop(fresh_db):
    assert await alerts_store.purge_seen_listings() == 0


# ── unconfirmed signup expiry ────────────────────────────────────────────────

async def _backdate_creation(search_id: str, seconds_ago: int) -> None:
    from db import get_conn
    await get_conn().execute(
        "UPDATE saved_searches SET created_at = ? WHERE id = ?",
        (int(time.time()) - seconds_ago, search_id),
    )


@pytest.mark.asyncio
async def test_expired_confirm_token_is_rejected(fresh_db):
    search_id = await alerts_store.create_pending("telegram", None, "tok-old", "Bellandur", "2BHK", 25000)
    await _backdate_creation(search_id, alerts_store._UNCONFIRMED_TTL_SECONDS + 60)

    # Must fail at use time, not merely once a cleanup job happens to run —
    # a confirm token is a bearer credential.
    assert await alerts_store.confirm_by_token("tok-old", target="chat-1") is None


@pytest.mark.asyncio
async def test_fresh_confirm_token_still_works(fresh_db):
    search_id = await alerts_store.create_pending("telegram", None, "tok-new", "Bellandur", "2BHK", 25000)
    assert await alerts_store.confirm_by_token("tok-new", target="chat-1") == search_id


@pytest.mark.asyncio
async def test_token_just_inside_the_window_still_works(fresh_db):
    search_id = await alerts_store.create_pending("email", "a@b.com", "tok-edge", "Bellandur", "2BHK", 25000)
    await _backdate_creation(search_id, alerts_store._UNCONFIRMED_TTL_SECONDS - 120)
    assert await alerts_store.confirm_by_token("tok-edge") == search_id


@pytest.mark.asyncio
async def test_purge_unconfirmed_removes_abandoned_signups(fresh_db):
    abandoned = await alerts_store.create_pending("email", "a@b.com", "tok-1", "Bellandur", "2BHK", 25000)
    await _backdate_creation(abandoned, alerts_store._UNCONFIRMED_TTL_SECONDS + 60)

    assert await alerts_store.purge_unconfirmed() == 1


@pytest.mark.asyncio
async def test_purge_unconfirmed_keeps_recent_pending_signups(fresh_db):
    await alerts_store.create_pending("email", "a@b.com", "tok-2", "Bellandur", "2BHK", 25000)
    assert await alerts_store.purge_unconfirmed() == 0


@pytest.mark.asyncio
async def test_purge_unconfirmed_never_touches_confirmed_searches(fresh_db):
    search_id = await alerts_store.create_pending("webpush", '{"endpoint":"x"}', None, "Bellandur", "2BHK", 25000)
    await alerts_store.confirm_by_id(search_id)
    # Old, but confirmed — this is a live subscription and must survive.
    await _backdate_creation(search_id, alerts_store._UNCONFIRMED_TTL_SECONDS * 10)

    assert await alerts_store.purge_unconfirmed() == 0
    active = await alerts_store.list_active_confirmed()
    assert any(s["id"] == search_id for s in active)
