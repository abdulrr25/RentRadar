"""
Short-TTL cache for identical searches — every search costs real Groq
tokens (and puts load on the self-hosted SearXNG instance), and two people
searching "2BHK Bellandur under 25k" seconds apart currently pay that cost
twice for an identical result.

Deliberately in-memory (a plain dict), matching the project's existing
single-instance assumptions (same as the rate limiter) — no new infra for
what's meant to be a cheap first pass, not a durable cache.

Deliberately does NOT cache sources_unavailable / synthesis_failed briefs —
caching a failure would keep serving a stale "sources down" message for the
full TTL even after the search backend recovers, directly undermining source_health.py's
recovery detection (which relies on the next real search actually retrying).
"""

import time

TTL_SECONDS = 15 * 60
MAX_ENTRIES = 500

_cache: dict[tuple, dict] = {}


def _key(locality: str, bhk: str, max_rent: int,
         min_rent: int | None = None, preferences: list[str] | None = None) -> tuple:
    # min_rent and preferences are part of the identity of a search: two
    # queries that differ only by a rent floor ("under 30k" vs "20k–30k")
    # produce different results (the floor is a hard filter in agent.py), so
    # they must not share a cache entry — otherwise the range query could be
    # served a cached brief containing listings below its floor. Preferences
    # change ranking, so they key too.
    prefs = tuple(sorted(preferences)) if preferences else ()
    return (locality.strip().lower(), bhk.strip().upper(), max_rent, min_rent, prefs)


def get(locality: str, bhk: str, max_rent: int,
        min_rent: int | None = None, preferences: list[str] | None = None) -> dict | None:
    key = _key(locality, bhk, max_rent, min_rent, preferences)
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.time() - entry["cached_at"] > TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return entry


def set(locality: str, bhk: str, max_rent: int,
        source_statuses: list[tuple[str, str]], brief: str,
        min_rent: int | None = None, preferences: list[str] | None = None) -> None:
    if len(_cache) >= MAX_ENTRIES:
        # Evict the oldest entry rather than let this grow unbounded across
        # a long-running process — a plain dict has no LRU built in.
        oldest_key = min(_cache, key=lambda k: _cache[k]["cached_at"])
        _cache.pop(oldest_key, None)
    _cache[_key(locality, bhk, max_rent, min_rent, preferences)] = {
        "source_statuses": source_statuses,
        "brief": brief,
        "cached_at": time.time(),
    }


def clear() -> None:
    """Test-only — reset cache state between tests."""
    _cache.clear()
