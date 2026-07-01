"""
LLM synthesis prompt for RentRadar.
Produces a structured JSON rental brief from multi-source raw data.
"""

import json
import re

# Keep total context well under 8K tokens (Groq free tier: 12K TPM).
LISTING_SNIPPET_LIMIT = 380   # chars per portal result page
SENTIMENT_LIMIT = 600         # chars per discussion source

# Short, stable ref prefixes per listing source
SRC_PREFIX = {"NoBroker": "NB", "OLX": "OLX", "Housing.com": "HS"}

# Which sources are property portals (carry "results") vs discussion (carry "data")
LISTING_SOURCES = {"NoBroker", "OLX", "Housing.com"}


SYSTEM_PROMPT = """You are RentRadar — a rental intelligence agent for Bangalore. Respond with valid JSON only — no prose, no markdown fences, no explanation.

You receive PROPERTY LISTINGS from three portals (NoBroker, OLX, Housing.com) and AREA SENTIMENT from Reddit, Google News and Hacker News.

Output EXACTLY this JSON:

{
  "locality": "string",
  "search_summary": "one line",
  "budget_note": "set ONLY if no listings exist at or below the user's budget — say so plainly; otherwise omit",
  "top_listings": [
    {"rank":1,"locality_detail":"e.g. Haralur Road","rent":22000,"bhk":"2BHK","source":"NoBroker","ref":"NB1","commute_note":"12 min to ORR","highlights":["Owner direct","Furnished"]}
  ],
  "locality_scores": {"safety":8.2,"water_supply":6.5,"traffic":5.8,"food_options":7.9,"public_transport":6.2,"overall":7.1},
  "price_trend": "rising",
  "trend_note": "one line trend insight",
  "reddit_pulse": "2-3 sentences on what Reddit says",
  "hn_signal": "one sentence tech-worker view",
  "green_flags": ["positive1","positive2"],
  "red_flags": ["warning1","warning2"],
  "scam_alerts": ["alert if any"],
  "verdict": "3-4 plain-English sentences — where to look, what to avoid, act fast or negotiate."
}

DIVERSITY RULE (critical): Spread top_listings ACROSS the portals. If NoBroker, OLX and Housing.com each have data, include at least one listing from EACH. Never return every listing from a single platform when others have listings. Aim for 4-6 listings total.

REF RULE (critical): For every listing set "ref" to the exact [REF] tag shown next to the source page you took it from (e.g. "OLX2"). This is how the listing gets linked to the right page. Do not invent refs.

PRICE RULE (critical): Each listing line below has a [PRICE: ₹X] tag pre-extracted by code from the raw snippet. Use that exact number as the "rent" value. Do NOT invent or infer a price if no [PRICE] tag is present — omit that listing instead.

BUDGET RULE (critical): NEVER include any listing with rent > user's max budget. Hard exclude them — do NOT show them even as alternatives. Sort remaining listings ascending by rent. If EVERY listing found is above budget, return an empty top_listings array and set "budget_note" explaining nothing was available at/under budget.

SCORES RULE: locality_scores are estimates derived from community sentiment (Reddit, HN, news) — they reflect what people online say, not objective measurement. Score 1-10 from available evidence only; omit a dimension if no evidence exists.

Other rules: ignore sale prices like ₹25,00,000 / "Crores" (those are not monthly rent), omit fields with no evidence, skip unavailable sources silently."""


def _extract_price(text: str) -> str:
    """
    Extract the first monthly rent figure from a snippet and return a [PRICE: ₹X]
    annotation, or empty string if none found.

    Matches patterns like: ₹25,000/month  |  Rs 18000 per month  |  25000/mo
    Ignores sale prices (contains 'lakh', 'crore', or is > 2,00,000).
    """
    # Skip text that mentions lakh/crore — definitely a sale price
    if re.search(r'\b(?:lakh|crore|lac)\b', text, re.IGNORECASE):
        return ""
    # Prioritise explicit per-month patterns; avoid deposit/advance amounts
    patterns = [
        r'(?:₹|rs\.?)\s*([\d,]+)\s*/\s*(?:month|mo|mon|mnth)',
        r'([\d,]+)\s*/\s*(?:month|mo|mon|mnth)',
        r'\brent\b\D{0,6}(?:₹|rs\.?)\s*([\d,]+)',
        r'\bprice\b\D{0,6}(?:₹|rs\.?)\s*([\d,]+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(",", "")
            try:
                amount = int(raw)
                # Valid monthly rent range for Bangalore: ₹5,000–₹2,00,000
                if 5000 <= amount <= 200000:
                    return f"[PRICE: ₹{amount:,}]"
            except ValueError:
                continue
    return ""


def _trim(data, limit: int) -> str:
    """Convert data to string and hard-trim to limit chars."""
    if isinstance(data, str):
        text = data
    else:
        try:
            if isinstance(data, dict) and "data" in data:
                inner = data["data"]
                if isinstance(inner, dict) and "data" in inner:
                    inner = inner["data"]
                text = json.dumps(inner, ensure_ascii=False)
            else:
                text = json.dumps(data, ensure_ascii=False)
        except Exception:
            text = str(data)

    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def build_context(raw_data: list, query: dict):
    """
    Build the LLM user message AND a {ref: url} map.

    Listing sources are expanded into individually-referenced result pages so
    the model can draw a diverse set across portals and cite the exact page for
    each listing. Returns (context_string, ref_map).
    """
    ref_map: dict = {}
    counters: dict = {}

    listing_lines = []
    for item in raw_data:
        source = item.get("source", "Unknown")
        if source not in LISTING_SOURCES:
            continue
        if item.get("status") != "ok" or not item.get("results"):
            listing_lines.append(f"[{source}] no results")
            continue
        prefix = SRC_PREFIX.get(source, source[:2].upper())
        for res in item["results"][:3]:
            counters[source] = counters.get(source, 0) + 1
            ref = f"{prefix}{counters[source]}"
            ref_map[ref] = {"url": res.get("url"), "source": source}
            title = (res.get("title") or "")[:80]
            snippet_raw = res.get("snippet", "")
            price_tag = _extract_price(snippet_raw)
            snippet = _trim(snippet_raw, LISTING_SNIPPET_LIMIT)
            # Prepend pre-extracted price so LLM uses ground-truth number
            line = f"[{ref}] {source} {price_tag} — {title} | {snippet}"
            listing_lines.append(line)

    sentiment_lines = []
    for item in raw_data:
        source = item.get("source", "Unknown")
        if source in LISTING_SOURCES:
            continue
        if item.get("status") != "ok":
            sentiment_lines.append(f"[{source}]: unavailable")
        else:
            sentiment_lines.append(f"[{source}]: {_trim(item.get('data', ''), SENTIMENT_LIMIT)}")

    context = "\n".join(
        [
            f"QUERY: {query['bhk']} in {query['locality']}, max ₹{query['max_rent']}/mo",
            "",
            "PROPERTY LISTINGS (cite the [REF] for each listing you use):",
            *listing_lines,
            "",
            "AREA SENTIMENT:",
            *sentiment_lines,
        ]
    )
    return context, ref_map
