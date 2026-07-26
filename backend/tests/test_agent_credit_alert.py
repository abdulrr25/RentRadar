import pytest

import agent
import source_health


def setup_function():
    source_health.mark_healthy()


@pytest.mark.asyncio
async def test_credit_exhausted_triggers_admin_alert(monkeypatch):
    sent = {}

    async def fake_send_admin_alert(subject, body):
        sent["subject"] = subject
        sent["body"] = body
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)

    state = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            {"source": "NoBroker", "status": "error", "error": "402", "credit_exhausted": True},
            {"source": "OLX", "status": "error", "error": "402", "credit_exhausted": True},
        ],
    }

    await agent.synthesis_node(state)

    # asyncio.create_task schedules the alert; let it run.
    await _drain_tasks()

    assert "Anakin API credits exhausted" in sent["subject"]
    assert "recharge" in sent["body"].lower()
    assert source_health.get_status()["degraded"] is True


@pytest.mark.asyncio
async def test_generic_outage_does_not_claim_credits(monkeypatch):
    sent = {}

    async def fake_send_admin_alert(subject, body):
        sent["subject"] = subject
        sent["body"] = body
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)

    state = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            {"source": "NoBroker", "status": "error", "error": "timeout", "credit_exhausted": False},
        ],
    }

    await agent.synthesis_node(state)
    await _drain_tasks()

    assert sent["subject"] == "RentRadar alert: all live data sources are down"


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
            {"source": "NoBroker", "status": "error", "error": "402", "credit_exhausted": True},
        ],
    }

    await agent.synthesis_node(state)
    await agent.synthesis_node(state)
    await _drain_tasks()

    assert len(calls) == 1


async def _drain_tasks():
    import asyncio
    # Let scheduled asyncio.create_task callbacks run before assertions.
    await asyncio.sleep(0)
    await asyncio.sleep(0)
