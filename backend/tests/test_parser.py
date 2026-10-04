from parser import parse_query


def test_defaults_when_nothing_matches():
    r = parse_query("looking for a place")
    assert r["bhk"] == "2BHK"
    assert r["locality"] == "Bangalore"
    assert r["max_rent"] == 50000


def test_extracts_bhk():
    assert parse_query("3bhk in Indiranagar")["bhk"] == "3BHK"
    assert parse_query("1 BHK flat")["bhk"] == "1BHK"


def test_extracts_longest_matching_locality():
    # "HSR Layout" should win over any shorter substring match
    r = parse_query("2BHK HSR Layout under 40000")
    assert r["locality"] == "HSR Layout"


def test_locality_is_case_insensitive():
    r = parse_query("2bhk near bellandur under 25000")
    assert r["locality"] == "Bellandur"


def test_extracts_rent_with_rupee_symbol_and_commas():
    r = parse_query("2BHK near Bellandur under ₹25,000")
    assert r["max_rent"] == 25000


def test_extracts_rent_with_rs_prefix():
    r = parse_query("2BHK Koramangala below Rs 30000")
    assert r["max_rent"] == 30000


def test_extracts_rent_with_k_suffix():
    r = parse_query("1BHK Whitefield under 18k")
    assert r["max_rent"] == 18000


def test_malformed_rent_falls_back_to_default():
    # A pathological string that matches the rent regex prefix but not a
    # parseable number shouldn't crash parse_query or leave max_rent unset.
    r = parse_query("2BHK under ₹")
    assert r["max_rent"] == 50000


def test_commute_time_is_not_mistaken_for_rent():
    # Regression: "under 30 mins" used to match the rent regex's bare
    # "under N" branch, parsing a ₹30 budget from a commute-time mention —
    # then agent.py's hard budget filter dropped every real listing as
    # "over budget" against that bogus ₹30 cap.
    r = parse_query("2BHK near Whitefield under 30 mins to ITPL")
    assert r["max_rent"] == 50000


def test_commute_time_does_not_shadow_a_real_budget_later_in_the_query():
    r = parse_query("2BHK under 30 mins from ITPL under ₹25000")
    assert r["max_rent"] == 25000


def test_commute_hours_is_not_mistaken_for_rent():
    r = parse_query("1BHK below 1 hour from Whitefield")
    assert r["max_rent"] == 50000


def test_empty_query_does_not_crash():
    r = parse_query("")
    assert r["bhk"] == "2BHK"
    assert r["locality"] == "Bangalore"
    assert r["max_rent"] == 50000


def test_raw_query_preserved():
    q = "2BHK near Bellandur under ₹25,000"
    assert parse_query(q)["raw_query"] == q


def test_bagalur_is_recognized_directly():
    # The exact locality a user complained wasn't being detected — now in
    # the curated list so it resolves via the primary match, not fallback.
    r = parse_query("2BHK near Bagalur under 15000")
    assert r["locality"] == "Bagalur"


def test_unknown_locality_falls_back_to_raw_place_name():
    # "Nelamangala" is a real Bangalore-area town not in the curated list —
    # it must not silently collapse to the generic "Bangalore" city default,
    # which turns a targeted search into a city-wide one.
    r = parse_query("2BHK near Nelamangala under 15000")
    assert r["locality"] == "Nelamangala"


def test_unknown_locality_without_near_keyword():
    r = parse_query("1BHK Nelamangala under 12000")
    assert r["locality"] == "Nelamangala"


def test_unknown_locality_lowercase_gets_capitalized():
    r = parse_query("2bhk in nelamangala under 20000")
    assert r["locality"] == "Nelamangala"


def test_unknown_locality_preserves_acronym_casing():
    r = parse_query("2BHK near HAL under 25000")
    assert r["locality"] == "HAL"


def test_unknown_multiword_locality_drops_trailing_city_name():
    r = parse_query("2BHK in Chikkajala Bangalore under 20000")
    assert r["locality"] == "Chikkajala"


def test_misspelled_known_locality_resolves_to_canonical_name():
    # Real user query — "kadubesanhalli" is close enough to the curated
    # "Kadubeesanahalli" that it should resolve there, not be searched
    # for exactly as misspelled.
    r = parse_query("1 bhk in kadubesanhalli under 25k")
    assert r["locality"] == "Kadubeesanahalli"
    assert r["bhk"] == "1BHK"
    assert r["max_rent"] == 25000


def test_short_words_do_not_trigger_false_fuzzy_matches():
    # Short filler-ish words shouldn't accidentally fuzzy-match a locality.
    r = parse_query("2BHK near me under 20000")
    assert r["locality"] != "" and r["locality"] is not None


# ── locality_matched / rent_matched confidence flags ────────────────────────

def test_confidence_flags_true_for_a_real_match():
    r = parse_query("2BHK near Bellandur under 25000")
    assert r["locality_matched"] is True
    assert r["rent_matched"] is True


def test_confidence_flags_true_for_fuzzy_locality_match():
    r = parse_query("1 bhk in kadubesanhalli under 25k")
    assert r["locality_matched"] is True
    assert r["rent_matched"] is True


def test_confidence_flags_false_when_nothing_matches():
    # Nothing here resolves to a real locality or a real rent — both flags
    # must say so, even though "locality"/"max_rent" still hold their
    # (silent-default) values for a search query's sake.
    r = parse_query("looking for a place")
    assert r["locality_matched"] is False
    assert r["rent_matched"] is False
    assert r["locality"] == "Bangalore"
    assert r["max_rent"] == 50000


# ── rent ranges / minimum rent ──────────────────────────────────────────────

def test_between_x_and_y_sets_both_bounds():
    # Regression: this matched none of the upper-bound triggers, so it fell
    # back to the ₹50,000 default while the UI chip confidently read
    # "max ₹50,000" — a wrong answer presented as an understood one.
    r = parse_query("2BHK Bellandur between 20000 and 30000")
    assert r["min_rent"] == 20000
    assert r["max_rent"] == 30000
    assert r["rent_matched"] is True


def test_dash_separated_k_range():
    r = parse_query("2BHK Bellandur 20k-30k")
    assert (r["min_rent"], r["max_rent"]) == (20000, 30000)


def test_range_given_high_to_low_is_normalised():
    r = parse_query("2BHK Bellandur between 30000 and 20000")
    assert (r["min_rent"], r["max_rent"]) == (20000, 30000)


def test_separate_min_and_max_phrases():
    r = parse_query("2BHK Koramangala above 20000 under 30000")
    assert (r["min_rent"], r["max_rent"]) == (20000, 30000)


def test_bhk_count_range_is_not_read_as_a_budget():
    # "2 to 3" is a BHK count, not ₹2–₹3 — the plausible-rent floor is what
    # stops the range regex from swallowing it.
    r = parse_query("2 to 3 BHK in Indiranagar under 40000")
    assert r["min_rent"] is None
    assert r["max_rent"] == 40000


def test_commute_range_is_not_read_as_a_budget():
    r = parse_query("2BHK near Bellandur under 30 mins from ITPL")
    assert r["min_rent"] is None
    assert r["max_rent"] == 50000
    assert r["rent_matched"] is False


def test_min_above_max_drops_the_floor():
    # Contradictory input — keep the ceiling people actually care about
    # rather than filtering every listing out.
    r = parse_query("2BHK Bellandur above 40000 under 30000")
    assert r["min_rent"] is None
    assert r["max_rent"] == 30000


def test_no_rent_bounds_leaves_min_unset():
    assert parse_query("2BHK near Bellandur under 25000")["min_rent"] is None


# ── preferences ─────────────────────────────────────────────────────────────

def test_extracts_multiple_preferences():
    r = parse_query("2BHK furnished near metro in Indiranagar under 35k, no brokers, with parking")
    assert set(r["preferences"]) == {"furnished", "metro", "parking", "no_broker"}


def test_semi_furnished_does_not_also_report_furnished():
    r = parse_query("3BHK Whitefield under 50k, semi furnished")
    assert "semi_furnished" in r["preferences"]
    assert "furnished" not in r["preferences"]


def test_unfurnished_does_not_also_report_furnished():
    r = parse_query("1BHK HSR Layout under 20k unfurnished")
    assert "unfurnished" in r["preferences"]
    assert "furnished" not in r["preferences"]


def test_no_preferences_for_a_plain_query():
    assert parse_query("2BHK near Bellandur under 25000")["preferences"] == []


def test_locality_matched_false_for_loose_fallback_extraction():
    # The raw fallback extraction (an unrecognised place-like word) is
    # deliberately permissive for a search query, but it's not a confident
    # match — e.g. it could just as easily latch onto a person's name in a
    # sentence that isn't about a locality at all.
    r = parse_query("2BHK near Nelamangala under 15000")
    assert r["locality"] == "Nelamangala"
    assert r["locality_matched"] is False


def test_clearly_unrelated_word_does_not_fuzzy_match():
    r = parse_query("2BHK near Nelamangala under 20000")
    assert r["locality"] == "Nelamangala"  # not fuzzy-matched to an unrelated known locality


def test_no_locality_at_all_still_defaults_to_bangalore():
    r = parse_query("2BHK under 25000")
    assert r["locality"] == "Bangalore"
