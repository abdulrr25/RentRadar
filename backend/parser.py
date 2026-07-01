"""
Natural language query parser for Bangalore rental searches.
Extracts BHK type, locality, and max rent from free-form text.
"""

import re


BANGALORE_LOCALITIES = [
    # East / Whitefield corridor
    "Whitefield", "Marathahalli", "Brookefield", "Kadugodi", "Kundalahalli",
    "Mahadevapura", "Kadubeesanahalli", "Panathur", "Varthur",
    "Devarabeesanahalli", "Kasavanahalli", "Halanayakanahalli",
    # South / Outer Ring Road
    "Bellandur", "Sarjapur", "Haralur", "Bommanahalli", "Electronic City",
    "Bannerghatta", "Hulimavu", "Begur", "Neeladri Nagar",
    # Central South
    "HSR Layout", "BTM Layout", "Koramangala", "Jayanagar", "JP Nagar",
    "Banashankari", "Padmanabhanagar", "Basavanagudi", "Girinagar",
    "Wilson Garden", "Langford Town",
    # Central / CBD
    "Indiranagar", "Domlur", "Madiwala", "Ejipura", "Vivek Nagar",
    "Richmond Town", "Shivajinagar", "MG Road", "UB City", "Lavelle Road",
    # North
    "Hebbal", "Yelahanka", "Thanisandra", "Nagawara", "Sahakara Nagar",
    "Devanahalli", "HBR Layout", "Kalyan Nagar", "RT Nagar",
    "Banaswadi", "CV Raman Nagar", "Ramamurthy Nagar",
    # West
    "Rajajinagar", "Vijayanagar", "Nagarbhavi", "Kengeri", "Uttarahalli",
    "Yeshwanthpur", "Malleshwaram", "Sadashivanagar", "Dollars Colony",
    "RPC Layout", "Chord Road",
    # North West
    "Peenya", "Tumkur Road", "Hesaraghatta", "Jalahalli",
    # Tech parks / micro-localities
    "Manyata Tech Park", "Embassy Tech Village", "Prestige Tech Park",
    "ITPL", "Bagmane Tech Park",
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
