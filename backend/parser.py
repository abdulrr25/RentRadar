"""
Natural language query parser for Bangalore rental searches.
Extracts BHK type, locality, and max rent from free-form text.
"""

import difflib
import re


BANGALORE_LOCALITIES = [
    # East / Whitefield corridor
    "Whitefield", "Marathahalli", "Brookefield", "Kadugodi", "Kundalahalli",
    "Mahadevapura", "Kadubeesanahalli", "Panathur", "Varthur",
    "Devarabeesanahalli", "Kasavanahalli", "Halanayakanahalli",
    "Hoodi", "Garudacharpalya", "Ramagondanahalli", "Seegehalli",
    "Hopefarm", "Immadihalli", "KR Puram", "Krishnarajapuram", "Tin Factory",
    "Channasandra", "Kadugodi Tree Park",
    # South / Outer Ring Road
    "Bellandur", "Sarjapur", "Haralur", "Bommanahalli", "Electronic City",
    "Bannerghatta", "Hulimavu", "Begur", "Neeladri Nagar",
    "Bommasandra", "Chandapura", "Attibele", "Anekal", "Hongasandra",
    "Arekere", "Gottigere", "Konanakunte", "Vasanthapura",
    "Kumaraswamy Layout", "Yelachenahalli", "Jigani", "Hosur Road",
    # Central South
    "HSR Layout", "BTM Layout", "Koramangala", "Jayanagar", "JP Nagar",
    "Banashankari", "Padmanabhanagar", "Basavanagudi", "Girinagar",
    "Wilson Garden", "Langford Town", "Adugodi", "Suddaguntepalya",
    # Central / CBD
    "Indiranagar", "Domlur", "Madiwala", "Ejipura", "Vivek Nagar",
    "Richmond Town", "Shivajinagar", "MG Road", "UB City", "Lavelle Road",
    "Cox Town", "Frazer Town", "Cooke Town", "Cunningham Road",
    "Vasanth Nagar", "Sampangiramanagar", "Seshadripuram", "Gandhinagar",
    "Majestic", "Chickpet",
    # North
    "Hebbal", "Yelahanka", "Thanisandra", "Nagawara", "Sahakara Nagar",
    "Devanahalli", "HBR Layout", "Kalyan Nagar", "RT Nagar",
    "Banaswadi", "CV Raman Nagar", "Ramamurthy Nagar", "Jakkur",
    "Attur Layout", "Hennur", "Kammanahalli", "Kothanur", "Horamavu",
    "Vidyaranyapura", "Yelahanka New Town", "Sanjaynagar", "Mathikere",
    "Bagalur", "Bettahalsur",
    # West
    "Rajajinagar", "Vijayanagar", "Nagarbhavi", "Kengeri", "Uttarahalli",
    "Yeshwanthpur", "Malleshwaram", "Sadashivanagar", "Dollars Colony",
    "RPC Layout", "Chord Road", "Basaveshwaranagar", "Kamakshipalya",
    "Rajarajeshwari Nagar", "RR Nagar", "Nayandahalli", "Herohalli",
    "Nagasandra", "Andrahalli",
    # North West / Outskirts
    "Peenya", "Tumkur Road", "Hesaraghatta", "Jalahalli",
    "Chikkabanavara", "Dasarahalli", "Doddaballapur",
    # Tech parks / micro-localities
    "Manyata Tech Park", "Embassy Tech Village", "Prestige Tech Park",
    "ITPL", "Bagmane Tech Park",
]

# Words to strip when falling back to a raw locality extraction (below) —
# BHK/rent phrasing and city names, not place names themselves.
_FILLER_WORDS = {
    "bhk", "flat", "flats", "apartment", "apartments", "house", "houses",
    "room", "rooms", "for", "rent", "in", "near", "at", "around", "on",
    "bangalore", "bengaluru", "blr", "a", "an", "the", "place", "looking",
    "need", "want", "find", "search",
}

# A time/distance unit immediately after a rent-regex number match means it
# was never a currency amount (e.g. "under 30 mins") — see parse_query.
_RENT_UNIT_RE = re.compile(
    r"\s*(?:min|mins|minute|minutes|hr|hrs|hour|hours|km|kms|kilometers?|sec|secs|seconds?)\b",
    re.IGNORECASE,
)


def _fix_case(word: str) -> str:
    # Leave acronyms/already-capitalized input alone (e.g. "HAL", "ITPL");
    # only capitalize words the user typed in lowercase.
    return word if any(c.isupper() for c in word) else word.capitalize()


_LOCALITY_LOOKUP = {loc.lower(): loc for loc in BANGALORE_LOCALITIES}


def _fuzzy_match_locality(query: str) -> "str | None":
    """
    Catch near-miss spellings of a known locality (e.g. "kadubesanhalli" for
    "Kadubeesanahalli") before falling back to raw extraction — a slightly
    misspelled but real, known place should still resolve to its canonical
    name rather than being searched for exactly as typed.
    """
    words = re.findall(r"[a-z]+", query.lower())
    candidates = set(words)
    for i in range(len(words) - 1):
        candidates.add(f"{words[i]} {words[i + 1]}")

    best_match = None
    best_ratio = 0.0
    for cand in candidates:
        if len(cand) < 5:
            continue  # too short for a meaningful fuzzy match — avoid false hits
        close = difflib.get_close_matches(cand, _LOCALITY_LOOKUP.keys(), n=1, cutoff=0.8)
        if close:
            ratio = difflib.SequenceMatcher(None, cand, close[0]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = _LOCALITY_LOOKUP[close[0]]
    return best_match


def _extract_fallback_locality(query: str) -> "str | None":
    """
    Whatever real place name the user typed that isn't in our curated
    BANGALORE_LOCALITIES list (small or less common areas — e.g. "Bagalur")
    would otherwise be silently discarded, defaulting the search to
    city-wide "Bangalore" and losing the user's actual intent entirely.
    This pulls the leftover place-like words out of the query instead.
    """
    # Drop the rent clause — anything from the first rent-trigger word on.
    cut = re.split(
        r"\b(?:under|below|max|upto|up\s+to|₹|rs\.?)\b", query, maxsplit=1, flags=re.IGNORECASE
    )[0]
    # Drop the BHK token (e.g. "2BHK", "2 BHK")
    cut = re.sub(r"\d+\s*bhk", " ", cut, flags=re.IGNORECASE)

    words = re.findall(r"[A-Za-z]+", cut)
    kept = [w for w in words if w.lower() not in _FILLER_WORDS]
    if not kept:
        return None
    return " ".join(_fix_case(w) for w in kept)


def parse_query(query: str) -> dict:
    """
    Parse a free-form rental query into structured parameters.

    Examples:
        "2BHK near Bellandur under ₹25,000"
        → {"bhk": "2BHK", "locality": "Bellandur", "max_rent": 25000, ...}
    """
    result = {
        "bhk": "2BHK",
        "locality": "Bangalore",
        "max_rent": 50000,
        "city": "Bangalore",
        "raw_query": query,
    }

    # Extract BHK
    bhk_match = re.search(r"(\d+)\s*bhk", query, re.IGNORECASE)
    if bhk_match:
        result["bhk"] = f"{bhk_match.group(1)}BHK"

    # Extract locality — longest match wins to avoid partial hits
    matched_locality = None
    matched_len = 0
    for loc in BANGALORE_LOCALITIES:
        if loc.lower() in query.lower() and len(loc) > matched_len:
            matched_locality = loc
            matched_len = len(loc)
    if matched_locality:
        result["locality"] = matched_locality
    else:
        fuzzy = _fuzzy_match_locality(query)
        if fuzzy:
            result["locality"] = fuzzy
        else:
            fallback = _extract_fallback_locality(query)
            if fallback:
                result["locality"] = fallback

    # Extract max rent — handles ₹25000, Rs 25,000, under 25k, below 25000.
    # "under"/"below" are common English words unrelated to money — plain
    # "...under 30 mins to ITPL" would otherwise parse as a ₹30 budget, and
    # the real listings all get hard-filtered out as "over budget" downstream
    # in agent.py. Checked as a separate step rather than a regex lookahead:
    # a lookahead here is defeatable by backtracking (the greedy digit group
    # backs off to a shorter prefix like "3" to dodge a "not followed by
    # mins" assertion on "30"), so each full candidate match is found first
    # and only then checked against what immediately follows it.
    rent_match = None
    for candidate in re.finditer(
        r"(?:under|below|max|upto|up\s+to|₹|rs\.?)\s*(\d[\d,]*[kK]?)",
        query,
        re.IGNORECASE,
    ):
        if _RENT_UNIT_RE.match(query, candidate.end()):
            continue  # a time/distance unit, not a currency amount
        rent_match = candidate
        break
    if rent_match:
        raw = rent_match.group(1).replace(",", "").strip()
        try:
            if raw.lower().endswith("k"):
                result["max_rent"] = int(raw[:-1]) * 1000
            else:
                result["max_rent"] = int(raw)
        except ValueError:
            pass  # keep default 50000

    return result
