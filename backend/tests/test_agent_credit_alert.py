import pytest

import agent
import source_health


def setup_function():
    # reset(), not mark_healthy() — mark_healthy deliberately does NOT clear
    # the credit_exhausted latch (credit exhaustion can persist while some
    # sources still succeed), so using it here would leak that flag between
    # tests and suppress the one-shot alert in whichever ran second.
    source_health.reset()


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

    assert sent["subject"] == "Urgent- RentRadar Credits expired"
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


# ── partial credit exhaustion ────────────────────────────────────────────────
#
# Anakin exposes two APIs — search (listings) and wire (Reddit/HN/news). If
# they bill from separate pools, one can run dry while the other keeps
# working. Previously the credit check lived inside the "every source
# failed" branch, so this case took the healthy path: no alert, no record,
# results quietly worse.

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


def _partial_state():
    return {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            # Listings still working...
            {"source": "NoBroker", "status": "ok", "results": [
                {"title": "2BHK", "url": "https://nobroker.in/x", "snippet": "Rent 20000/month"}
            ]},
            # ...while the wire API reports exhausted credits.
            {"source": "Reddit", "status": "error", "data": "402", "credit_exhausted": True},
        ],
    }


@pytest.mark.asyncio
async def test_partial_credit_exhaustion_still_alerts(monkeypatch):
    sent = {}

    async def fake_send_admin_alert(subject, body):
        sent["subject"] = subject
        sent["body"] = body
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)
    monkeypatch.setattr(agent, "_groq_client", lambda: _FakeGroq())

    await agent.synthesis_node(_partial_state())
    await _drain_tasks()

    assert sent["subject"] == "Urgent- RentRadar Credits expired"
    # The body must make clear this is the silent-degradation case, since
    # the site will look fine while returning fewer results.
    assert "Reddit" in sent["body"]
    assert "fewer results" in sent["body"]


@pytest.mark.asyncio
async def test_partial_exhaustion_does_not_mark_the_site_degraded(monkeypatch):
    monkeypatch.setattr(agent, "send_admin_alert", lambda s, b: _noop())
    monkeypatch.setattr(agent, "_groq_client", lambda: _FakeGroq())

    await agent.synthesis_node(_partial_state())
    await _drain_tasks()

    status = source_health.get_status()
    # Listings still work, so users should NOT get an "everything is broken"
    # banner — but the owner-facing flag must be set for diagnosis.
    assert status["degraded"] is False
    assert status["credit_exhausted"] is True


@pytest.mark.asyncio
async def test_partial_exhaustion_alert_fires_only_once(monkeypatch):
    calls = []

    async def fake_send_admin_alert(subject, body):
        calls.append(subject)
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)
    monkeypatch.setattr(agent, "_groq_client", lambda: _FakeGroq())

    await agent.synthesis_node(_partial_state())
    await agent.synthesis_node(_partial_state())
    await _drain_tasks()

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_recovery_clears_the_latch_so_a_later_outage_alerts_again(monkeypatch):
    calls = []

    async def fake_send_admin_alert(subject, body):
        calls.append(subject)
        return True

    monkeypatch.setattr(agent, "send_admin_alert", fake_send_admin_alert)
    monkeypatch.setattr(agent, "_groq_client", lambda: _FakeGroq())

    await agent.synthesis_node(_partial_state())

    # A clean search — no source reports a credit problem.
    clean = {
        "query": {"locality": "Bellandur", "bhk": "2BHK", "max_rent": 25000},
        "raw_data": [
            {"source": "NoBroker", "status": "ok", "results": [
                {"title": "2BHK", "url": "https://nobroker.in/x", "snippet": "Rent 20000/month"}
            ]},
        ],
    }
    await agent.synthesis_node(clean)
    assert source_health.get_status()["credit_exhausted"] is False

    # Credits run out again — this must page, not be swallowed by a stale latch.
    await agent.synthesis_node(_partial_state())
    await _drain_tasks()

    assert len(calls) == 2


async def _noop():
    return True
