"""
Natural language query parser for Bangalore rental searches.
Extracts BHK type, locality, and max rent from free-form text.
"""

import re


BANGALORE_LOCALITIES = [
    "Bellandur", "Koramangala", "Indiranagar", "HSR Layout",
    "Whitefield", "Electronic City", "Marathahalli", "BTM Layout",
    "Sarjapur", "Haralur", "Hebbal", "Yelahanka", "Jayanagar",
    "JP Nagar", "Bannerghatta", "Domlur", "Madiwala", "Bommanahalli",
    "Kadugodi", "Brookefield", "Kundalahalli", "Mahadevapura",
    "Kadubeesanahalli", "Panathur", "Varthur", "Devarabeesanahalli",
    "Kasavanahalli", "Halanayakanahalli", "Nagawara", "Thanisandra",
]


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
        "max_rent": 30000,
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

    # Extract max rent — handles ₹25000, Rs 25,000, under 25k, below 25000
    rent_match = re.search(
        r"(?:under|below|max|upto|up\s+to|₹|rs\.?)\s*(\d[\d,]*[kK]?)",
        query,
        re.IGNORECASE,
    )
    if rent_match:
        raw = rent_match.group(1).replace(",", "").strip()
        try:
            if raw.lower().endswith("k"):
                result["max_rent"] = int(raw[:-1]) * 1000
            else:
                result["max_rent"] = int(raw)
        except ValueError:
            pass  # keep default 30000

    return result
