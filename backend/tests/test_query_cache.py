import time

import query_cache


def setup_function():
    query_cache.clear()


def test_miss_when_empty():
    assert query_cache.get("Bellandur", "2BHK", 25000) is None


def test_set_then_get_hit():
    query_cache.set("Bellandur", "2BHK", 25000, [("NoBroker", "ok")], '{"locality":"Bellandur"}')
    entry = query_cache.get("Bellandur", "2BHK", 25000)
    assert entry is not None
    assert entry["brief"] == '{"locality":"Bellandur"}'
    assert entry["source_statuses"] == [("NoBroker", "ok")]


def test_key_normalises_case_and_whitespace():
    query_cache.set("  Bellandur  ", "2bhk", 25000, [], "{}")
    assert query_cache.get("BELLANDUR", "2BHK", 25000) is not None


def test_different_max_rent_is_a_different_key():
    query_cache.set("Bellandur", "2BHK", 25000, [], "{}")
    assert query_cache.get("Bellandur", "2BHK", 30000) is None


def test_different_min_rent_is_a_different_key():
    # "under 30000" (no floor) and "20000-30000" share locality/bhk/max_rent
    # but are different searches — the floor is a hard filter, so a cached
    # no-floor result must not be served for the range query.
    query_cache.set("Bellandur", "2BHK", 30000, [], "{}", min_rent=None)
    assert query_cache.get("Bellandur", "2BHK", 30000, min_rent=20000) is None
    # ...and the exact same bounds still hit.
    assert query_cache.get("Bellandur", "2BHK", 30000, min_rent=None) is not None


def test_different_preferences_is_a_different_key():
    query_cache.set("Bellandur", "2BHK", 30000, [], "{}", preferences=["furnished"])
    assert query_cache.get("Bellandur", "2BHK", 30000, preferences=["parking"]) is None
    # order-insensitive: same set of preferences hits regardless of order.
    query_cache.set("Bellandur", "2BHK", 30000, [], "{}", preferences=["furnished", "metro"])
    assert query_cache.get("Bellandur", "2BHK", 30000, preferences=["metro", "furnished"]) is not None


def test_expired_entry_is_not_returned():
    query_cache.set("Bellandur", "2BHK", 25000, [], "{}")
    # Backdate the entry past the TTL directly, rather than sleeping in a test.
    key = query_cache._key("Bellandur", "2BHK", 25000)
    query_cache._cache[key]["cached_at"] = time.time() - query_cache.TTL_SECONDS - 60
    assert query_cache.get("Bellandur", "2BHK", 25000) is None


def test_eviction_when_over_max_entries(monkeypatch):
    monkeypatch.setattr(query_cache, "MAX_ENTRIES", 3)
    for i in range(3):
        query_cache.set(f"Locality{i}", "2BHK", 25000, [], "{}")
        time.sleep(0.01)  # ensure distinct cached_at ordering
    assert len(query_cache._cache) == 3

    # Adding a 4th over the cap should evict the oldest (Locality0), not crash
    # or grow unbounded.
    query_cache.set("Locality3", "2BHK", 25000, [], "{}")
    assert len(query_cache._cache) == 3
    assert query_cache.get("Locality0", "2BHK", 25000) is None
    assert query_cache.get("Locality3", "2BHK", 25000) is not None
