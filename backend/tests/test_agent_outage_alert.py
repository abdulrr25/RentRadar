import pytest

import agent
import source_health


def setup_function():
    source_health.reset()


@pytest.mark.asyncio
async def test_all_sources_failing_triggers_admin_alert(monkeypatch):
    sent = {}

    async def fake_send_admin_alert(subject, body):
        sent["subject"] = subject
        sent["body"] = body
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)

    state = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            {"source": "NoBroker", "status": "error", "error": "timeout"},
            {"source": "OLX", "status": "error", "error": "timeout"},
        ],
    }

    await agent.synthesis_node(state)
    await _drain_tasks()

    assert sent["subject"] == "RentRadar alert: all live data sources are down"
    assert source_health.get_status()["degraded"] is True


@pytest.mark.asyncio
async def test_partial_failure_does_not_alert_or_degrade(monkeypatch):
    """One portal failing while another succeeds is normal noise, not an outage."""
    sent = {}

    async def fake_send_admin_alert(subject, body):
        sent["subject"] = subject
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)
    monkeypatch.setattr(agent, "_groq_client", lambda: _FakeGroq())

    state = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            {"source": "NoBroker", "status": "ok", "results": [
                {"title": "2BHK", "url": "https://nobroker.in/x", "snippet": "Rent 20000/month"}
            ]},
            {"source": "OLX", "status": "error", "error": "timeout"},
        ],
    }

    await agent.synthesis_node(state)
    await _drain_tasks()

    assert sent == {}
    assert source_health.get_status()["degraded"] is False


@pytest.mark.asyncio
async def test_alert_only_fires_once_per_outage(monkeypatch):
    calls = []

    async def fake_send_admin_alert(subject, body):
        calls.append(subject)
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)

    state = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            {"source": "NoBroker", "status": "error", "error": "timeout"},
        ],
    }

    await agent.synthesis_node(state)
    await agent.synthesis_node(state)
    await _drain_tasks()

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_recovery_allows_a_later_outage_to_alert_again(monkeypatch):
    calls = []

    async def fake_send_admin_alert(subject, body):
        calls.append(subject)
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)
    monkeypatch.setattr(agent, "_groq_client", lambda: _FakeGroq())

    failing = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [{"source": "NoBroker", "status": "error", "error": "timeout"}],
    }
    await agent.synthesis_node(failing)
    await _drain_tasks()
    assert len(calls) == 1

    recovered = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [{"source": "NoBroker", "status": "ok", "results": [
            {"title": "2BHK", "url": "https://nobroker.in/x", "snippet": "Rent 20000/month"}
        ]}],
    }
    await agent.synthesis_node(recovered)
    assert source_health.get_status()["degraded"] is False

    await agent.synthesis_node(failing)
    await _drain_tasks()
    assert len(calls) == 2


async def _drain_tasks():
    import asyncio
    # Let scheduled asyncio.create_task callbacks run before assertions.
    await asyncio.sleep(0)
    await asyncio.sleep(0)


class _FakeMessage:
    content = '{"locality": "Bellandur", "top_listings": []}'


class _FakeChoice:
    message = _FakeMessage()


class _FakeCompletion:
    choices = [_FakeChoice()]


class _FakeGroq:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                return _FakeCompletion()
