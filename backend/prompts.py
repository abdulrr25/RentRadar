"""
LLM synthesis prompt for RentRadar.
Produces a structured JSON rental brief from multi-source raw data.
"""

import json

# Keep total context well under 8K tokens (Groq free tier: 12K TPM).
# Each source gets at most SOURCE_CHAR_LIMIT characters.
SOURCE_CHAR_LIMIT = 900


SYSTEM_PROMPT = """You are RentRadar — a rental intelligence agent for Bangalore. Respond with valid JSON only — no prose, no markdown fences, no explanation.

Sources you receive: Reddit, Google News, Hacker News, NoBroker, MagicBricks, Housing.com.

Output EXACTLY this JSON:

{
  "locality": "string",
  "search_summary": "one line",
  "top_listings": [
    {"rank":1,"locality_detail":"e.g. Haralur Road","rent":22000,"bhk":"2BHK","source":"NoBroker","commute_note":"12 min to ORR","highlights":["Owner direct","Furnished"]}
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

Rules: extract real prices only, score locality 1-10 from sentiment, omit fields with no evidence, skip errored sources silently."""


def _trim(data, limit: int = SOURCE_CHAR_LIMIT) -> str:
    """Convert data to string and hard-trim to limit chars."""
    if isinstance(data, str):
        text = data
    else:
        try:
            # For Wire responses, extract just the inner data payload
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
        text = text[:limit] + "…[trimmed]"
    return text


def build_context(raw_data: list, query: dict) -> str:
    """Build the user message. Keeps total size under ~6K chars."""
    sections = [
        f"QUERY: {query['bhk']} in {query['locality']}, max ₹{query['max_rent']}/mo",
    ]

    for item in raw_data:
        source = item.get("source", "Unknown")
        status = item.get("status", "error")
        data = item.get("data", "")

        if status == "error":
            sections.append(f"[{source}]: unavailable")
        else:
            sections.append(f"[{source}]:\n{_trim(data)}")

    return "\n\n".join(sections)
