import pytest
from pywebpush import WebPushException

import channels.webpush as webpush_module
from channels.webpush import send_webpush


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.mark.asyncio
async def test_stub_mode_returns_sent_when_no_vapid_key(monkeypatch):
    monkeypatch.delenv("VAPID_PRIVATE_KEY", raising=False)
    result = await send_webpush('{"endpoint": "x", "keys": {}}', "hello")
    assert result == "sent"


@pytest.mark.asyncio
async def test_malformed_subscription_json_returns_failed(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "fake-key")
    result = await send_webpush("not valid json", "hello")
    assert result == "failed"


@pytest.mark.asyncio
async def test_410_gone_status_returns_gone(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "fake-key")

    def fake_webpush(**kwargs):
        raise WebPushException("gone", response=_FakeResponse(410))

    monkeypatch.setattr(webpush_module, "webpush", fake_webpush)
    result = await send_webpush('{"endpoint": "x", "keys": {}}', "hello")
    assert result == "gone"


@pytest.mark.asyncio
async def test_404_not_found_status_returns_gone(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "fake-key")

    def fake_webpush(**kwargs):
        raise WebPushException("not found", response=_FakeResponse(404))

    monkeypatch.setattr(webpush_module, "webpush", fake_webpush)
    result = await send_webpush('{"endpoint": "x", "keys": {}}', "hello")
    assert result == "gone"


@pytest.mark.asyncio
async def test_other_status_returns_failed_not_gone(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "fake-key")

    def fake_webpush(**kwargs):
        raise WebPushException("server error", response=_FakeResponse(500))

    monkeypatch.setattr(webpush_module, "webpush", fake_webpush)
    result = await send_webpush('{"endpoint": "x", "keys": {}}', "hello")
    assert result == "failed"


@pytest.mark.asyncio
async def test_unexpected_exception_returns_failed(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "fake-key")

    def fake_webpush(**kwargs):
        raise ValueError("bad p256dh padding")

    monkeypatch.setattr(webpush_module, "webpush", fake_webpush)
    result = await send_webpush('{"endpoint": "x", "keys": {}}', "hello")
    assert result == "failed"


@pytest.mark.asyncio
async def test_successful_send_returns_sent(monkeypatch):
    monkeypatch.setenv("VAPID_PRIVATE_KEY", "fake-key")

    def fake_webpush(**kwargs):
        return None

    monkeypatch.setattr(webpush_module, "webpush", fake_webpush)
    result = await send_webpush('{"endpoint": "x", "keys": {}}', "hello")
    assert result == "sent"
