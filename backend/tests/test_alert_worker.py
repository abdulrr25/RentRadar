import pytest
import pytest_asyncio

import db
import alerts_store
import alert_worker


@pytest_asyncio.fixture
async def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DATABASE_URL", f"file:{tmp_path / 'test.db'}")
    await db.init_db()
    yield
    await db.close_db()


async def _make_confirmed_webpush(target="sub-json") -> str:
    search_id = await alerts_store.create_pending(
        "webpush", target, None, "Bellandur", "2BHK", 25000
    )
    await alerts_store.confirm_by_id(search_id)
    return search_id


@pytest.mark.asyncio
async def test_gone_webpush_deactivates_saved_search(fresh_db, monkeypatch):
    search_id = await _make_confirmed_webpush()

    async def fake_find_matches(locality, bhk, max_rent):
        return [{"source": "NoBroker", "url": "https://nobroker.in/x", "title": "t", "price": 20000}]

    async def fake_send_webpush(target, message):
        return "gone"

    monkeypatch.setattr(alert_worker, "_find_matches", fake_find_matches)
    monkeypatch.setattr(alert_worker, "send_webpush", fake_send_webpush)

    summary = await alert_worker.run_all_alerts()

    assert summary["alerts_sent"] == 0
    active = await alerts_store.list_active_confirmed()
    assert all(s["id"] != search_id for s in active)


@pytest.mark.asyncio
async def test_gone_webpush_does_not_process_further_matches_for_same_search(fresh_db, monkeypatch):
    await _make_confirmed_webpush()

    async def fake_find_matches(locality, bhk, max_rent):
        return [
            {"source": "NoBroker", "url": "https://nobroker.in/a", "title": "a", "price": 20000},
            {"source": "OLX", "url": "https://olx.in/b", "title": "b", "price": 21000},
        ]

    calls = []

    async def fake_send_webpush(target, message):
        calls.append(message)
        return "gone"

    monkeypatch.setattr(alert_worker, "_find_matches", fake_find_matches)
    monkeypatch.setattr(alert_worker, "send_webpush", fake_send_webpush)

    await alert_worker.run_all_alerts()

    # Should stop at the first "gone" result, not try every match.
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_transient_failure_does_not_mark_seen(fresh_db, monkeypatch):
    search_id = await _make_confirmed_webpush()

    async def fake_find_matches(locality, bhk, max_rent):
        return [{"source": "NoBroker", "url": "https://nobroker.in/x", "title": "t", "price": 20000}]

    async def fake_send_webpush(target, message):
        return "failed"

    monkeypatch.setattr(alert_worker, "_find_matches", fake_find_matches)
    monkeypatch.setattr(alert_worker, "send_webpush", fake_send_webpush)

    summary = await alert_worker.run_all_alerts()

    assert summary["alerts_sent"] == 0
    ref = alert_worker._ref_hash("https://nobroker.in/x")
    # Not marked seen — a future run (once the transient issue clears) must
    # still be able to notify about this listing.
    assert await alerts_store.has_seen(search_id, ref) is False
    # And the saved search itself must still be active (a transient failure
    # is not grounds for deactivation, unlike a confirmed-gone subscription).
    active = await alerts_store.list_active_confirmed()
    assert any(s["id"] == search_id for s in active)


@pytest.mark.asyncio
async def test_successful_send_marks_seen_and_counts(fresh_db, monkeypatch):
    search_id = await _make_confirmed_webpush()

    async def fake_find_matches(locality, bhk, max_rent):
        return [{"source": "NoBroker", "url": "https://nobroker.in/x", "title": "t", "price": 20000}]

    async def fake_send_webpush(target, message):
        return "sent"

    monkeypatch.setattr(alert_worker, "_find_matches", fake_find_matches)
    monkeypatch.setattr(alert_worker, "send_webpush", fake_send_webpush)

    summary = await alert_worker.run_all_alerts()

    assert summary["alerts_sent"] == 1
    ref = alert_worker._ref_hash("https://nobroker.in/x")
    assert await alerts_store.has_seen(search_id, ref) is True


@pytest.mark.asyncio
async def test_already_seen_match_is_not_resent(fresh_db, monkeypatch):
    search_id = await _make_confirmed_webpush()
    await alerts_store.mark_seen(search_id, alert_worker._ref_hash("https://nobroker.in/x"))

    async def fake_find_matches(locality, bhk, max_rent):
        return [{"source": "NoBroker", "url": "https://nobroker.in/x", "title": "t", "price": 20000}]

    calls = []

    async def fake_send_webpush(target, message):
        calls.append(message)
        return "sent"

    monkeypatch.setattr(alert_worker, "_find_matches", fake_find_matches)
    monkeypatch.setattr(alert_worker, "send_webpush", fake_send_webpush)

    await alert_worker.run_all_alerts()

    assert calls == []


@pytest.mark.asyncio
async def test_one_bad_search_does_not_stop_the_whole_run(fresh_db, monkeypatch):
    id1 = await _make_confirmed_webpush(target="sub-1")
    id2 = await alerts_store.create_pending("telegram", None, "tok", "Koramangala", "1BHK", 15000)
    await alerts_store.confirm_by_token("tok", target="chat-123")

    call_count = {"n": 0}

    async def fake_find_matches(locality, bhk, max_rent):
        call_count["n"] += 1
        if locality == "Bellandur":
            raise RuntimeError("boom")
        return []

    monkeypatch.setattr(alert_worker, "_find_matches", fake_find_matches)

    summary = await alert_worker.run_all_alerts()

    assert summary["checked"] == 2
    assert summary["errors"] == 1
    assert call_count["n"] == 2  # the second search still ran despite the first raising


@pytest.mark.asyncio
async def test_no_active_searches_returns_zeroed_summary(fresh_db):
    summary = await alert_worker.run_all_alerts()
    assert summary == {
        "checked": 0,
        "alerts_sent": 0,
        "errors": 0,
        "purged_seen_listings": 0,
        "purged_briefs": 0,
    }


@pytest.mark.asyncio
async def test_run_purges_seen_listings_of_deactivated_searches(fresh_db):
    search_id = await _make_confirmed_webpush()
    await alerts_store.mark_seen(search_id, "deadbeef")
    await alerts_store.deactivate(search_id)

    summary = await alert_worker.run_all_alerts()

    assert summary["purged_seen_listings"] == 1


@pytest.mark.asyncio
async def test_cleanup_failure_does_not_fail_the_alert_run(fresh_db, monkeypatch):
    async def boom():
        raise RuntimeError("turso unavailable")

    monkeypatch.setattr(alerts_store, "purge_seen_listings", boom)

    # Should still return a normal summary rather than propagating.
    summary = await alert_worker.run_all_alerts()
    assert summary["checked"] == 0
    assert summary["purged_seen_listings"] == 0
