import json

import pytest
from fastapi.testclient import TestClient

import db
import main
import source_health
import query_cache


@pytest.fixture
def client(monkeypatch, tmp_path):
    """
    Fresh DB file (unique per test via tmp_path), a reset rate limiter, reset
    source_health state, and a cleared query_cache — all module-level globals
    that would otherwise leak between tests depending on run order.
    """
    monkeypatch.setattr(db, "DATABASE_URL", f"file:{tmp_path / 'test.db'}")
    main.limiter.reset()
    source_health.mark_healthy()
    query_cache.clear()
    with TestClient(main.app) as c:
        yield c


def _sse_events(text: str):
    events = []
    for line in text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


# ── /health ──────────────────────────────────────────────────────────────────

def test_health_ok_when_env_vars_present(client, monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_degraded_when_env_vars_missing(client, monkeypatch):
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    res = client.get("/health")
    assert res.json()["status"] == "degraded"
    assert "SEARXNG_URL" in res.json()["missing_env"]


def test_health_degraded_when_sources_failing(client, monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    source_health.mark_degraded("all sources failed in a real search")
    res = client.get("/health")
    assert res.json()["status"] == "degraded"
    assert res.json()["reason"] == "all sources failed in a real search"
    assert res.json()["since"] is not None


def test_health_unknown_on_a_fresh_instance(client, monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    # Just-restarted state: no search has reported in yet. Answering "ok"
    # here would let a monitor read a new instance as fine while the search
    # backend is down — the failure mode this three-valued status exists to
    # prevent.
    source_health.reset()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "unknown"
    assert res.json()["last_result_at"] is None


def test_health_always_returns_200_even_when_degraded(client, monkeypatch):
    # render.yaml uses healthCheckPath: /health, and Render restarts an
    # instance returning non-2xx. Signalling a third-party outage with a 5xx
    # would take the service down over something a restart cannot fix.
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    source_health.mark_degraded("all sources failed in a real search")
    assert client.get("/health").status_code == 200

    monkeypatch.delenv("SEARXNG_URL", raising=False)
    assert client.get("/health").status_code == 200


def test_health_recovers_after_mark_healthy(client, monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8080")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    source_health.mark_degraded("temporary failure")
    source_health.mark_healthy()
    res = client.get("/health")
    assert res.json()["status"] == "ok"


# ── API docs should not be publicly exposed ─────────────────────────────────

def test_docs_and_openapi_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/redoc").status_code == 404


# ── /search ──────────────────────────────────────────────────────────────────

def test_search_rejects_oversized_query(client):
    res = client.post("/search", json={"query": "a" * 400})
    assert res.status_code == 422


def test_search_rejects_empty_query(client):
    res = client.post("/search", json={"query": ""})
    assert res.status_code == 422


def test_search_happy_path_streams_expected_events(client, monkeypatch):
    async def fake_ainvoke(state):
        return {
            **state,
            "raw_data": [{"source": "NoBroker", "status": "ok"}],
            "brief": json.dumps({"locality": "Bellandur", "top_listings": []}),
        }

    monkeypatch.setattr(main.agent, "ainvoke", fake_ainvoke)

    res = client.post("/search", json={"query": "2BHK near Bellandur under 25000"})
    assert res.status_code == 200
    events = _sse_events(res.text)
    types = [e["type"] for e in events]
    assert types == ["parsed", "fetching", "source_complete", "brief", "share", "done"]
    assert events[0]["data"]["locality"] == "Bellandur"


def test_repeat_search_hits_cache_and_skips_agent(client, monkeypatch):
    call_count = {"n": 0}

    async def fake_ainvoke(state):
        call_count["n"] += 1
        return {
            **state,
            "raw_data": [{"source": "NoBroker", "status": "ok"}],
            "brief": json.dumps({"locality": "Bellandur", "top_listings": []}),
        }

    monkeypatch.setattr(main.agent, "ainvoke", fake_ainvoke)

    first = client.post("/search", json={"query": "2BHK near Bellandur under 25000"})
    second = client.post("/search", json={"query": "2BHK near Bellandur under 25000"})

    assert first.status_code == 200 and second.status_code == 200
    assert call_count["n"] == 1, "second identical search should have hit the cache, not re-invoked the agent"

    second_types = [e["type"] for e in _sse_events(second.text)]
    assert second_types == ["parsed", "fetching", "source_complete", "brief", "share", "done"]


def test_search_does_not_cache_sources_unavailable_briefs(client, monkeypatch):
    call_count = {"n": 0}

    async def fake_ainvoke_unavailable(state):
        call_count["n"] += 1
        return {
            **state,
            "raw_data": [{"source": "NoBroker", "status": "error"}],
            "brief": json.dumps({"sources_unavailable": True, "locality": "Bellandur"}),
        }

    monkeypatch.setattr(main.agent, "ainvoke", fake_ainvoke_unavailable)

    client.post("/search", json={"query": "2BHK near Bellandur under 25000"})
    client.post("/search", json={"query": "2BHK near Bellandur under 25000"})

    assert call_count["n"] == 2, "an all-sources-failed brief must never be cached — it would block recovery detection"


# ── /alerts — webpush (immediate confirmation) ──────────────────────────────

def _valid_subscription():
    return json.dumps({"endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "a", "auth": "b"}})


def test_create_webpush_alert_confirms_immediately(client):
    res = client.post("/alerts", json={
        "channel": "webpush", "target": _valid_subscription(),
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"
    assert res.json()["id"]


def test_webpush_alert_rejects_missing_target(client):
    res = client.post("/alerts", json={
        "channel": "webpush", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 422


def test_webpush_alert_rejects_malformed_subscription(client):
    res = client.post("/alerts", json={
        "channel": "webpush", "target": "not json",
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 422


def test_webpush_alert_rejects_subscription_missing_keys_field(client):
    res = client.post("/alerts", json={
        "channel": "webpush", "target": json.dumps({"endpoint": "https://x"}),
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 422


# ── /alerts — email (token-link confirmation) ───────────────────────────────

def test_create_email_alert_pending_until_confirmed(client):
    res = client.post("/alerts", json={
        "channel": "email", "target": "user@example.com",
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 200
    assert res.json()["status"] == "pending_confirmation"


def test_email_alert_rejects_invalid_address(client):
    res = client.post("/alerts", json={
        "channel": "email", "target": "not-an-email",
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 422


def test_email_confirm_link_activates_alert(client, monkeypatch):
    # The API deliberately never returns the confirm token (it only ever goes
    # out via the actual email) — pin the generator so the test can predict it.
    monkeypatch.setattr(main.secrets, "token_urlsafe", lambda n: "fixed-test-token")

    create_res = client.post("/alerts", json={
        "channel": "email", "target": "user@example.com",
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    search_id = create_res.json()["id"]

    res = client.get("/alerts/confirm/fixed-test-token")
    assert res.status_code == 200
    assert "all set" in res.text.lower()

    # Confirming twice must not re-activate / double count
    res2 = client.get("/alerts/confirm/fixed-test-token")
    assert "invalid" in res2.text.lower()


def test_email_confirm_endpoint_rejects_bad_token(client):
    res = client.get("/alerts/confirm/not-a-real-token")
    assert res.status_code == 200  # always renders a page, success or not
    assert "invalid" in res.text.lower()


# ── /alerts — telegram (deep-link + webhook confirmation) ───────────────────

def test_create_telegram_alert_without_bot_configured_returns_503(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)
    res = client.post("/alerts", json={
        "channel": "telegram", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 503


def test_create_telegram_alert_returns_deep_link_when_configured(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "RentRadarBot")
    res = client.post("/alerts", json={
        "channel": "telegram", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "pending_confirmation"
    assert body["telegram_link"].startswith("https://t.me/RentRadarBot?start=")


def test_telegram_webhook_disabled_without_secret(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    res = client.post("/alerts/telegram/webhook", json={"message": {"text": "/start abc", "chat": {"id": 1}}})
    assert res.status_code == 503


def test_telegram_webhook_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "correct-secret")
    res = client.post(
        "/alerts/telegram/webhook",
        json={"message": {"text": "/start abc", "chat": {"id": 1}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert res.status_code == 403


def test_telegram_webhook_confirms_pending_search(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "RentRadarBot")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "correct-secret")

    create_res = client.post("/alerts", json={
        "channel": "telegram", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    telegram_link = create_res.json()["telegram_link"]
    token = telegram_link.split("start=")[1]

    res = client.post(
        "/alerts/telegram/webhook",
        json={"message": {"text": f"/start {token}", "chat": {"id": 999888}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "correct-secret"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "confirmed", "id": create_res.json()["id"]}


def test_telegram_webhook_ignores_non_start_messages(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "correct-secret")
    res = client.post(
        "/alerts/telegram/webhook",
        json={"message": {"text": "hi there", "chat": {"id": 1}}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "correct-secret"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ignored"}


def test_telegram_webhook_handles_missing_message_gracefully(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "correct-secret")
    res = client.post(
        "/alerts/telegram/webhook",
        json={},
        headers={"X-Telegram-Bot-Api-Secret-Token": "correct-secret"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ignored"}


# ── rate limiting ────────────────────────────────────────────────────────────

def test_create_alert_rate_limited_after_five(client):
    for _ in range(5):
        res = client.post("/alerts", json={
            "channel": "webpush", "target": _valid_subscription(),
            "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
        })
        assert res.status_code == 200
    res = client.post("/alerts", json={
        "channel": "webpush", "target": _valid_subscription(),
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    assert res.status_code == 429


# ── DELETE /alerts/{id} ──────────────────────────────────────────────────────

def test_delete_nonexistent_alert_returns_404(client):
    res = client.delete("/alerts/does-not-exist")
    assert res.status_code == 404


def test_delete_existing_alert(client):
    create_res = client.post("/alerts", json={
        "channel": "webpush", "target": _valid_subscription(),
        "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000,
    })
    search_id = create_res.json()["id"]
    res = client.delete(f"/alerts/{search_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "deactivated"


# ── /internal/run-alerts ─────────────────────────────────────────────────────

def test_internal_run_alerts_disabled_without_secret(client, monkeypatch):
    monkeypatch.delenv("ALERTS_INTERNAL_SECRET", raising=False)
    res = client.post("/internal/run-alerts")
    assert res.status_code == 503


def test_internal_run_alerts_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("ALERTS_INTERNAL_SECRET", "correct-secret")
    res = client.post("/internal/run-alerts", headers={"X-Internal-Secret": "wrong"})
    assert res.status_code == 403


# ── /feedback ────────────────────────────────────────────────────────────────

def test_feedback_success(client, monkeypatch):
    monkeypatch.setenv("ALERTS_INTERNAL_SECRET", "s3cret")

    res = client.post("/feedback", json={"rating": "up", "message": "Loved it", "query": "2BHK Bellandur"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Read it back out of the database — the whole point of this change is
    # that it survives somewhere other than a wiped-on-deploy local file.
    read = client.get("/internal/feedback", headers={"X-Internal-Secret": "s3cret"})
    assert read.status_code == 200
    body = read.json()
    assert body["counts"] == {"up": 1, "down": 0}
    assert body["recent"][0]["rating"] == "up"
    assert body["recent"][0]["message"] == "Loved it"
    assert body["recent"][0]["query"] == "2BHK Bellandur"


def test_feedback_counts_tally_both_ratings(client, monkeypatch):
    monkeypatch.setenv("ALERTS_INTERNAL_SECRET", "s3cret")
    client.post("/feedback", json={"rating": "up"})
    client.post("/feedback", json={"rating": "down"})
    client.post("/feedback", json={"rating": "down"})

    body = client.get("/internal/feedback", headers={"X-Internal-Secret": "s3cret"}).json()
    assert body["counts"] == {"up": 1, "down": 2}


def test_internal_feedback_requires_secret(client, monkeypatch):
    monkeypatch.setenv("ALERTS_INTERNAL_SECRET", "s3cret")
    res = client.get("/internal/feedback", headers={"X-Internal-Secret": "wrong"})
    assert res.status_code == 403


def test_internal_feedback_503_when_secret_unset(client, monkeypatch):
    monkeypatch.delenv("ALERTS_INTERNAL_SECRET", raising=False)
    res = client.get("/internal/feedback")
    assert res.status_code == 503


def test_feedback_rejects_invalid_rating(client):
    res = client.post("/feedback", json={"rating": "sideways"})
    assert res.status_code == 422
