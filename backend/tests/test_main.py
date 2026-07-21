import json

import pytest
from fastapi.testclient import TestClient

import db
import main


@pytest.fixture
def client(monkeypatch):
    """
    Fresh in-memory DB and a reset rate limiter per test, so tests can't leak
    state into each other regardless of run order.
    """
    monkeypatch.setattr(db, "DB_PATH", ":memory:")
    main.limiter.reset()
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
    monkeypatch.setenv("ANAKIN_API_KEY", "x")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_degraded_when_env_vars_missing(client, monkeypatch):
    monkeypatch.delenv("ANAKIN_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    res = client.get("/health")
    assert res.json()["status"] == "degraded"
    assert "ANAKIN_API_KEY" in res.json()["missing_env"]


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
    assert types == ["parsed", "fetching", "source_complete", "brief", "done"]
    assert events[0]["data"]["locality"] == "Bellandur"


# ── /alerts ──────────────────────────────────────────────────────────────────

def test_create_alert_rejects_invalid_phone(client):
    res = client.post("/alerts", json={"phone": "abc", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000})
    assert res.status_code == 422


def test_create_alert_success(client):
    res = client.post("/alerts", json={"phone": "+919876543210", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "pending_confirmation"
    assert body["id"]


def test_create_alert_rate_limited_after_five(client):
    for i in range(5):
        res = client.post("/alerts", json={"phone": f"+9198765432{i}0", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000})
        assert res.status_code == 200
    res = client.post("/alerts", json={"phone": "+919876543299", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000})
    assert res.status_code == 429


# ── /alerts/webhook ──────────────────────────────────────────────────────────

def test_webhook_disabled_without_secret_configured(client, monkeypatch):
    monkeypatch.delenv("ALERTS_WEBHOOK_SECRET", raising=False)
    res = client.post("/alerts/webhook", json={"phone": "+919876543210", "message": "YES"})
    assert res.status_code == 503


def test_webhook_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setenv("ALERTS_WEBHOOK_SECRET", "correct-secret")
    res = client.post(
        "/alerts/webhook",
        json={"phone": "+919876543210", "message": "YES"},
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert res.status_code == 403


def test_webhook_confirms_pending_search_on_yes(client, monkeypatch):
    monkeypatch.setenv("ALERTS_WEBHOOK_SECRET", "correct-secret")
    create_res = client.post("/alerts", json={"phone": "+919876543210", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000})
    search_id = create_res.json()["id"]

    res = client.post(
        "/alerts/webhook",
        json={"phone": "+919876543210", "message": "yes"},
        headers={"X-Webhook-Secret": "correct-secret"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "confirmed", "id": search_id}


def test_webhook_ignores_non_yes_messages(client, monkeypatch):
    monkeypatch.setenv("ALERTS_WEBHOOK_SECRET", "correct-secret")
    res = client.post(
        "/alerts/webhook",
        json={"phone": "+919876543210", "message": "hi"},
        headers={"X-Webhook-Secret": "correct-secret"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "ignored"}


# ── DELETE /alerts/{id} ──────────────────────────────────────────────────────

def test_delete_nonexistent_alert_returns_404(client):
    res = client.delete("/alerts/does-not-exist")
    assert res.status_code == 404


def test_delete_existing_alert(client):
    create_res = client.post("/alerts", json={"phone": "+919876543210", "locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000})
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

def test_feedback_success(client, tmp_path, monkeypatch):
    feedback_file = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(main, "FEEDBACK_FILE", feedback_file)

    res = client.post("/feedback", json={"rating": "up", "message": "Loved it", "query": "2BHK Bellandur"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    lines = feedback_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["rating"] == "up"
    assert entry["message"] == "Loved it"


def test_feedback_rejects_invalid_rating(client):
    res = client.post("/feedback", json={"rating": "sideways"})
    assert res.status_code == 422
