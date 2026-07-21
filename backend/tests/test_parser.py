from parser import parse_query


def test_defaults_when_nothing_matches():
    r = parse_query("looking for a place")
    assert r["bhk"] == "2BHK"
    assert r["locality"] == "Bangalore"
    assert r["max_rent"] == 30000


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
    assert r["max_rent"] == 30000


def test_empty_query_does_not_crash():
    r = parse_query("")
    assert r["bhk"] == "2BHK"
    assert r["locality"] == "Bangalore"
    assert r["max_rent"] == 30000


def test_raw_query_preserved():
    q = "2BHK near Bellandur under ₹25,000"
    assert parse_query(q)["raw_query"] == q
