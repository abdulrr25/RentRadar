"""
LLM synthesis prompt for RentRadar.
Produces a structured JSON rental brief from multi-source raw data.
"""

import re
from datetime import datetime, timezone

from parser import PREFERENCE_LABELS

# Keep total context well under 8K tokens (Groq free tier: 12K TPM).
LISTING_SNIPPET_LIMIT = 380   # chars per portal result page
SENTIMENT_TITLE_LIMIT = 160   # chars per headline

# Short, stable ref prefixes per source. Sentiment sources get them too, so
# every area claim can cite the exact headline it came from — see agent.py,
# which drops any claim whose ref doesn't resolve.
SRC_PREFIX = {"NoBroker": "NB", "OLX": "OLX", "Housing.com": "HS"}
SENTIMENT_PREFIX = {"Google News": "GN", "Hacker News": "HN"}

# Which sources are property portals (carry "results") vs discussion (carry "items")
LISTING_SOURCES = {"NoBroker", "OLX", "Housing.com"}


SYSTEM_PROMPT = """You are RentRadar — a rental intelligence agent for Bangalore. Respond with valid JSON only — no prose, no markdown fences, no explanation.

You receive PROPERTY LISTINGS from three portals (NoBroker, OLX, Housing.com) and AREA SENTIMENT from Google News and Hacker News.

Output EXACTLY this JSON:

{
  "locality": "string",
  "search_summary": "one line",
  "budget_note": "set ONLY if no listings exist at or below the user's budget — say so plainly; otherwise omit",
  "top_listings": [
    {"rank":1,"locality_detail":"e.g. Haralur Road","rent":22000,"bhk":"2BHK","source":"NoBroker","ref":"NB1","commute_note":"12 min to ORR","highlights":["Owner direct","Furnished"]}
  ],
  "locality_scores": {"safety":8.2,"traffic":5.8,"overall":7.1},
  "scores_evidence": {"safety":"GN2","traffic":"HN1"},
  "price_trend": "rising",
  "trend_note": {"text":"one line trend insight","ref":"GN1"},
  "hn_signal": "one sentence tech-worker view",
  "green_flags": [{"text":"positive1","ref":"GN3"}],
  "red_flags": [{"text":"warning1","ref":"GN2"}],
  "scam_alerts": [{"text":"alert if any","ref":"GN4"}],
  "verdict": "3-4 plain-English sentences — where to look, what to avoid, act fast or negotiate."
}

DIVERSITY RULE (critical): Spread top_listings ACROSS the portals. If NoBroker, OLX and Housing.com each have data, include at least one listing from EACH. Never return every listing from a single platform when others have listings. Aim for 4-6 listings total.

REF RULE (critical): For every listing set "ref" to the exact [REF] tag shown next to the source page you took it from (e.g. "OLX2"). This is how the listing gets linked to the right page. Do not invent refs.

PRICE RULE (critical): If a [PRICE: ₹X] tag is present on a listing line, use that exact number as the "rent" value — never change it. If there is no [PRICE] tag, look carefully at the snippet text to extract the monthly rent yourself. If you genuinely cannot find a price anywhere in the snippet, set "rent": null — do NOT omit the listing. A listing with null rent is still useful; a listing silently dropped is not.

BUDGET RULE (critical): NEVER include any listing with rent > user's max budget, or below their minimum when one is given. Hard exclude them — do NOT show them even as alternatives. Sort remaining listings ascending by rent. If EVERY listing found is outside the budget, return an empty top_listings array and set "budget_note" explaining nothing was available in range.

PREFERENCES RULE: when a USER PREFERENCES line is present, rank listings whose snippet shows evidence of those preferences higher, and name the match in that listing's "highlights" (e.g. "Furnished", "Covered parking"). These are ranking hints ONLY — never drop a listing for lacking one, and never claim a listing has a preference its snippet doesn't actually mention.

EVIDENCE RULE (critical): every green_flag, red_flag, scam_alert, and trend_note MUST cite the [REF] of the exact AREA SENTIMENT headline it came from (e.g. "GN2"). Each is an object: {"text": "...", "ref": "GN2"}. A claim you cannot tie to a specific headline must be LEFT OUT — do not infer, do not generalise from background knowledge, do not reuse a ref for a claim that headline doesn't support. The same applies to locality_scores: score only the dimensions a headline actually speaks to, and name the supporting ref for each one in "scores_evidence". Omit every dimension you have no headline for — an empty locality_scores object is the correct answer when the headlines say nothing about the area.

LOCALITY RULE (critical): headlines tagged [Bengaluru-wide] are NOT about the user's locality — they are about the city generally. You may still cite them, but never word the claim as though it describes the user's specific area ("Bellandur has a scam problem"); word it as the city-wide fact it is ("a leasing fraud was reported in Bengaluru"). Headlines tagged [about <locality>] are the only ones that may be stated as facts about that locality.

SCORES RULE: locality_scores are estimates derived from community sentiment (HN, news) — they reflect what people online say, not objective measurement. Score 1-10 from available evidence only; omit a dimension if no evidence exists.

Other rules: ignore sale prices like ₹25,00,000 / "Crores" (those are not monthly rent), omit fields with no evidence, skip unavailable sources silently."""


def extract_price_int(text: str) -> "int | None":
    """
    Extract the first monthly rent figure from a snippet as a plain int, or None.

    Matches patterns like: ₹25,000/month  |  Rs 18000 per month  |  25000/mo
    Ignores sale prices (contains 'lakh', 'crore', or is > 2,00,000).
    """
    # Skip text that mentions lakh/crore — definitely a sale price
    if re.search(r'\b(?:lakh|crore|lac)\b', text, re.IGNORECASE):
        return None
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
                # Valid monthly rent range for Bangalore: ₹3,000–₹2,00,000
                if 3000 <= amount <= 200000:
                    return amount
            except ValueError:
                continue
    return None


def _extract_price(text: str) -> str:
    """Extract the first monthly rent figure and return a [PRICE: ₹X] annotation, or "" if none found."""
    amount = extract_price_int(text)
    return f"[PRICE: ₹{amount:,}]" if amount is not None else ""


def _trim(data, limit: int) -> str:
    """Convert data to string and hard-trim to limit chars."""
    text = data if isinstance(data, str) else str(data)
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def _format_date(epoch: "int | None") -> str:
    """Human date for the prompt line, so the model can weigh recency (and
    so a stale headline is visibly stale rather than implicitly current)."""
    if not epoch:
        return "undated"
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%d %b %Y")


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
        for res in item["results"][:5]:
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

    locality = query.get("locality", "")
    sentiment_lines = []
    for item in raw_data:
        source = item.get("source", "Unknown")
        if source in LISTING_SOURCES:
            continue
        if source == "Community":
            # Already-structured listings merged directly into top_listings
            # after the LLM call (see agent.py's synthesis_node) — never
            # part of the prompt. It carries no headlines to cite, and
            # without this it'd appear as a spurious blank or "unavailable"
            # line under AREA SENTIMENT for no reason.
            continue
        if item.get("status") != "ok" or not item.get("items"):
            sentiment_lines.append(f"[{source}]: unavailable")
            continue

        prefix = SENTIMENT_PREFIX.get(source, source[:2].upper())
        for entry in item["items"][:8]:
            counters[source] = counters.get(source, 0) + 1
            ref = f"{prefix}{counters[source]}"
            # Same ref_map the listing refs live in — agent.py resolves both
            # through it and drops anything the model cited that isn't here.
            ref_map[ref] = {
                "url": entry.get("url"),
                "source": source,
                "title": entry.get("title"),
                "published_at": entry.get("published_at"),
                "mentions_locality": bool(entry.get("mentions_locality")),
            }
            scope = f"about {locality}" if entry.get("mentions_locality") else "Bengaluru-wide"
            sentiment_lines.append(
                f"[{ref}] {source} [{_format_date(entry.get('published_at'))}] [{scope}] "
                f"— {_trim(entry.get('title', ''), SENTIMENT_TITLE_LIMIT)}"
            )

    min_rent = query.get("min_rent")
    budget = (
        f"₹{min_rent}–₹{query['max_rent']}/mo" if min_rent is not None
        else f"max ₹{query['max_rent']}/mo"
    )
    header = [f"QUERY: {query['bhk']} in {query['locality']}, {budget}"]
    if query.get("preferences"):
        header.append(
            "USER PREFERENCES (rank on these, never filter on them): "
            + ", ".join(PREFERENCE_LABELS.get(p, p) for p in query["preferences"])
        )

    context = "\n".join(
        [
            *header,
            "",
            "PROPERTY LISTINGS (cite the [REF] for each listing you use):",
            *listing_lines,
            "",
            "AREA SENTIMENT:",
            *sentiment_lines,
        ]
    )
    return context, ref_map
