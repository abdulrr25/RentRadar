"""
Provenance and freshness of the area-sentiment sources.

These exist because the live APIs were measured returning HN threads from
2017 and 2023, and news headlines that never mention the searched locality —
all of which used to be fed in as current, local "area sentiment" with no
date and no link. No network here: httpx is stubbed.
"""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from tools import sentiment_sources


def _iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rfc822(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )


def _stub_response(monkeypatch, *, text=None, payload=None):
    """Make every httpx.AsyncClient.get return this one canned response."""
    async def fake_get(self, url, **kwargs):
        return httpx.Response(
            200,
            text=text if text is not None else json.dumps(payload),
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


def _rss(items: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f"<item><title>{t}</title><link>{link}</link><pubDate>{date}</pubDate></item>"
        for t, link, date in items
    )
    return f"<?xml version='1.0'?><rss><channel>{body}</channel></rss>"


# ── Hacker News ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hn_keeps_permalink_and_date(monkeypatch):
    _stub_response(monkeypatch, payload={"hits": [
        {"title": "Bangalore rent is wild", "objectID": "123", "created_at": _iso(10), "points": 42},
    ]})

    result = await sentiment_sources.fetch_hackernews("Bellandur")

    assert result["status"] == "ok"
    item = result["items"][0]
    assert item["url"] == "https://news.ycombinator.com/item?id=123"
    assert item["published_at"] is not None
    assert item["points"] == 42


@pytest.mark.asyncio
async def test_hn_drops_ancient_threads(monkeypatch):
    # Measured live: real results included a 2017 thread with 3 points,
    # surfaced as current tech-worker sentiment.
    _stub_response(monkeypatch, payload={"hits": [
        {"title": "Old thread", "objectID": "1", "created_at": _iso(9 * 365), "points": 3},
        {"title": "Recent thread", "objectID": "2", "created_at": _iso(5), "points": 10},
    ]})

    result = await sentiment_sources.fetch_hackernews("Bellandur")

    assert [i["title"] for i in result["items"]] == ["Recent thread"]


@pytest.mark.asyncio
async def test_hn_all_stale_reports_error_status(monkeypatch):
    _stub_response(monkeypatch, payload={"hits": [
        {"title": "Old", "objectID": "1", "created_at": _iso(5 * 365), "points": 3},
    ]})

    result = await sentiment_sources.fetch_hackernews("Bellandur")

    assert result["status"] == "error"
    assert result["items"] == []


# ── Google News ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_news_keeps_link_and_date(monkeypatch):
    _stub_response(monkeypatch, text=_rss([
        ("Bellandur rents climb", "https://news.example/1", _rfc822(3)),
    ]))

    result = await sentiment_sources.fetch_google_news("Bellandur")

    item = result["items"][0]
    assert item["url"] == "https://news.example/1"
    assert item["published_at"] is not None


@pytest.mark.asyncio
async def test_news_flags_whether_the_headline_is_about_the_locality(monkeypatch):
    # The exact failure measured live: a city-wide leasing-fraud story was
    # rendered as a scam alert for the searched locality.
    _stub_response(monkeypatch, text=_rss([
        ("Bellandur rents climb 12%", "https://news.example/local", _rfc822(2)),
        ("Bengaluru leasing fraud hits 200 tenants", "https://news.example/city", _rfc822(4)),
    ]))

    result = await sentiment_sources.fetch_google_news("Bellandur")
    by_title = {i["title"]: i["mentions_locality"] for i in result["items"]}

    assert by_title["Bellandur rents climb 12%"] is True
    assert by_title["Bengaluru leasing fraud hits 200 tenants"] is False


@pytest.mark.asyncio
async def test_news_sorted_newest_first(monkeypatch):
    _stub_response(monkeypatch, text=_rss([
        ("Older", "https://news.example/old", _rfc822(30)),
        ("Newer", "https://news.example/new", _rfc822(1)),
    ]))

    result = await sentiment_sources.fetch_google_news("Bellandur")

    assert [i["title"] for i in result["items"]] == ["Newer", "Older"]


@pytest.mark.asyncio
async def test_news_undated_items_are_kept(monkeypatch):
    # Missing date means unparsed, not old — dropping these would quietly
    # discard most of a source on a format change.
    _stub_response(monkeypatch, text=_rss([
        ("No date here", "https://news.example/x", "not-a-date"),
    ]))

    result = await sentiment_sources.fetch_google_news("Bellandur")

    assert result["status"] == "ok"
    assert result["items"][0]["published_at"] is None
