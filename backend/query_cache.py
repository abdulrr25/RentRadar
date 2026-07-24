"""
Short-TTL cache for identical searches — every search costs real Anakin
search credits (this project has hit 0 balance once already) plus Groq
tokens, and two people searching "2BHK Bellandur under 25k" seconds apart
currently pay that cost twice for an identical result.

Deliberately in-memory (a plain dict), matching the project's existing
single-instance assumptions (same as the rate limiter) — no new infra for
what's meant to be a cheap first pass, not a durable cache.

Deliberately does NOT cache sources_unavailable / synthesis_failed briefs —
caching a failure would keep serving a stale "sources down" message for the
full TTL even after Anakin recovers, directly undermining source_health.py's
recovery detection (which relies on the next real search actually retrying).
"""

import time

TTL_SECONDS = 15 * 60
MAX_ENTRIES = 500

_cache: dict[tuple, dict] = {}


def _key(locality: str, bhk: str, max_rent: int) -> tuple:
    return (locality.strip().lower(), bhk.strip().upper(), max_rent)


def get(locality: str, bhk: str, max_rent: int) -> dict | None:
    entry = _cache.get(_key(locality, bhk, max_rent))
    if entry is None:
        return None
    if time.time() - entry["cached_at"] > TTL_SECONDS:
        _cache.pop(_key(locality, bhk, max_rent), None)
        return None
    return entry


def set(locality: str, bhk: str, max_rent: int, source_statuses: list[tuple[str, str]], brief: str) -> None:
    if len(_cache) >= MAX_ENTRIES:
        # Evict the oldest entry rather than let this grow unbounded across
        # a long-running process — a plain dict has no LRU built in.
        oldest_key = min(_cache, key=lambda k: _cache[k]["cached_at"])
        _cache.pop(oldest_key, None)
    _cache[_key(locality, bhk, max_rent)] = {
        "source_statuses": source_statuses,
        "brief": brief,
        "cached_at": time.time(),
    }


def clear() -> None:
    """Test-only — reset cache state between tests."""
    _cache.clear()
