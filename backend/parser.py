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

_AMOUNT = r"(?:₹|rs\.?)?\s*(\d[\d,]*\s*[kK]?)"

# "between 20000 and 30000", "20k-30k", "₹20,000 to ₹30,000" — a budget with
# both ends. Checked before the single-bound patterns below, since the
# upper-bound regex would otherwise match only the first number and silently
# treat a range as "under ₹20,000".
_RENT_RANGE_RE = re.compile(
    rf"(?:between|from)?\s*{_AMOUNT}\s*(?:-|–|—|to|and)\s*{_AMOUNT}",
    re.IGNORECASE,
)

# The trigger here can itself be the currency symbol ("₹25,000"), so this
# one spells out its own amount group rather than reusing _AMOUNT.
_RENT_MAX_RE = re.compile(
    r"(?:under|below|max|upto|up\s+to|₹|rs\.?)\s*(\d[\d,]*\s*[kK]?)",
    re.IGNORECASE,
)

_RENT_MIN_RE = re.compile(
    rf"(?:above|over|more\s+than|at\s+least|starting\s+(?:at|from)|min(?:imum)?)\s*{_AMOUNT}",
    re.IGNORECASE,
)

# Below this, a number was never a monthly Bangalore rent — it's a BHK count
# ("2 to 3 BHK"), a commute time, a floor number. Guards every amount parsed
# here, which is what keeps the range regex above from reading "2 to 3 BHK"
# as a ₹2–₹3 budget.
_MIN_PLAUSIBLE_RENT = 1000


def _to_amount(raw: str) -> "int | None":
    """'25,000' / '25k' / '25 K' → 25000. None if it isn't a plausible rent."""
    cleaned = raw.replace(",", "").replace(" ", "").strip()
    try:
        value = int(cleaned[:-1]) * 1000 if cleaned.lower().endswith("k") else int(cleaned)
    except ValueError:
        return None
    return value if value >= _MIN_PLAUSIBLE_RENT else None


# Soft preferences — things a user asks for that we can rank on but can't
# verify from a search snippet (nothing here is ever used to exclude a
# listing; see prompts.py). Deterministic keyword matching, no LLM, same
# principle as the Telegram submission parsing in main.py.
# Order matters: the "semi"/"un" variants are checked before plain
# "furnished", which is a substring of both.
_PREFERENCE_PATTERNS = {
    "semi_furnished": r"semi[-\s]?furnished",
    "unfurnished": r"un[-\s]?furnished",
    "furnished": r"furnished",
    "parking": r"\bparking\b|\bcar\s*park(?:ing)?\b",
    "metro": r"\bmetro\b",
    "pet_friendly": r"\bpet[-\s]?friendly\b|\bpets?\s+allowed\b",
    "no_broker": r"\bno\s*broker(?:s|age)?\b|\bowner\s*direct\b|\bdirect\s*(?:from\s*)?owner\b|\bwithout\s*brokers?\b",
    "gated": r"\bgated\b",
    "family": r"\bfamil(?:y|ies)\b",
    "bachelors": r"\bbachelors?\b",
}


# Human-readable form of each canonical preference key, for the LLM context
# (prompts.py) and anywhere else these need to be shown as words. The
# frontend keeps its own copy for display — it never sees this module.
PREFERENCE_LABELS = {
    "furnished": "furnished",
    "semi_furnished": "semi-furnished",
    "unfurnished": "unfurnished",
    "parking": "parking",
    "metro": "near metro",
    "pet_friendly": "pet friendly",
    "no_broker": "owner direct / no brokerage",
    "gated": "gated community",
    "family": "suitable for families",
    "bachelors": "bachelors allowed",
}


def _extract_preferences(query: str) -> list[str]:
    found = [
        name for name, pattern in _PREFERENCE_PATTERNS.items()
        if re.search(pattern, query, re.IGNORECASE)
    ]
    # "semi furnished" / "unfurnished" both contain "furnished" — keep only
    # the specific one, or the brief would claim the user asked for both.
    if "semi_furnished" in found or "unfurnished" in found:
        found = [f for f in found if f != "furnished"]
    return found


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
        "min_rent": None,
        "preferences": [],
        "city": "Bangalore",
        "raw_query": query,
        # True only when a real locality/rent was found — not when the
        # field is left at its silent default, and not when "locality" was
        # only ever the loose fallback extraction (below), which is
        # deliberately permissive for a search query ("something beats a
        # generic Bangalore-wide search") but too weak a signal to trust
        # for e.g. gating whether a Telegram submission is a real listing
        # worth storing versus noise ("hi", a stray capitalized word).
        "locality_matched": False,
        "rent_matched": False,
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
        result["locality_matched"] = True
    else:
        fuzzy = _fuzzy_match_locality(query)
        if fuzzy:
            result["locality"] = fuzzy
            result["locality_matched"] = True
        else:
            fallback = _extract_fallback_locality(query)
            if fallback:
                result["locality"] = fallback

    result["preferences"] = _extract_preferences(query)

    # Rent. Each pattern is matched in full first and only then checked
    # against what immediately follows it — a lookahead is defeatable by
    # backtracking here (the greedy digit group backs off to a shorter
    # prefix like "3" to dodge a "not followed by mins" assertion on "30"),
    # which is why "...under 30 mins to ITPL" used to parse as a ₹30 budget
    # and hard-filter every real listing out as over-budget in agent.py.
    #
    # Ranges go first: "between 20000 and 30000" would otherwise match only
    # the upper-bound pattern's first number and silently become "under
    # ₹20,000" — or, before ranges were handled at all, match nothing and
    # fall back to the ₹50,000 default while the UI confidently showed it.
    def _first_valid(regex, groups: int = 1):
        for candidate in regex.finditer(query):
            if _RENT_UNIT_RE.match(query, candidate.end()):
                continue  # a time/distance unit, not a currency amount
            amounts = [_to_amount(candidate.group(i)) for i in range(1, groups + 1)]
            if all(a is not None for a in amounts):
                return amounts
        return None

    rent_range = _first_valid(_RENT_RANGE_RE, groups=2)
    if rent_range:
        low, high = sorted(rent_range)
        result["min_rent"], result["max_rent"] = low, high
        result["rent_matched"] = True
    else:
        rent_max = _first_valid(_RENT_MAX_RE)
        if rent_max:
            result["max_rent"] = rent_max[0]
            result["rent_matched"] = True

        rent_min = _first_valid(_RENT_MIN_RE)
        if rent_min:
            result["min_rent"] = rent_min[0]
            result["rent_matched"] = True

    # A floor above the ceiling is a contradiction we can't resolve — keep
    # the ceiling (the budget people actually care about) and drop the floor
    # rather than filtering every listing out.
    if result["min_rent"] is not None and result["min_rent"] > result["max_rent"]:
        result["min_rent"] = None

    return result
