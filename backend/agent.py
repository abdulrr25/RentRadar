"""
LangGraph agent for RentRadar.

Graph:
  parallel_fetch_node  →  synthesis_node  →  END

Node 1 fires 5 async fetches simultaneously (free sentiment APIs + Anakin search).
Node 2 sends all raw data to Groq (gpt-oss-120b) for structured synthesis.
Groq is free — sign up at console.groq.com.
"""

import asyncio
import json
import os
import re
import warnings
from typing import TypedDict, List

# Suppress LangGraph internal deprecation warning about checkpoint allowed_objects
# (fired at import time; we don't use a checkpointer so the default is irrelevant)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langgraph")
warnings.filterwarnings("ignore", message=".*allowed_objects.*")

from langgraph.graph import StateGraph, END
from groq import Groq

from tools.sentiment_sources import fetch_google_news, fetch_hackernews
from tools.scraper import fetch_nobroker, fetch_olx, fetch_housing
from prompts import SYSTEM_PROMPT, build_context
from channels.email import send_admin_alert
import source_health


def _groq_client() -> Groq:
    """Create Groq client at call time so the key is always fresh from env."""
    return Groq(api_key=os.getenv("GROQ_API_KEY", ""))


class RentRadarState(TypedDict):
    query: dict           # parsed query params from parser.py
    raw_data: List[dict]  # all fetched results (5 sources)
    brief: str            # final synthesized JSON brief
    error: str            # any critical pipeline error


# ── Node 1: Parallel Fetch ──────────────────────────────────────────────────

async def parallel_fetch_node(state: RentRadarState) -> RentRadarState:
    """
    Fires all 5 data fetches simultaneously.
    - Free APIs:   Google News, Hacker News
    - Anakin API:  NoBroker, OLX, Housing.com

    Uses return_exceptions=True so a single timeout never kills the pipeline.
    """
    q = state["query"]
    locality = q["locality"]
    bhk = q["bhk"]
    max_rent = q["max_rent"]

    results = await asyncio.gather(
        fetch_google_news(locality),
        fetch_hackernews(locality),
        fetch_nobroker(locality, bhk, max_rent),
        fetch_olx(locality, bhk, max_rent),
        fetch_housing(locality, bhk, max_rent),
        return_exceptions=True,
    )

    clean_results = []
    for r in results:
        if isinstance(r, Exception):
            clean_results.append({
                "source": "unknown",
                "status": "error",
                "data": f"{type(r).__name__}: {r}",
            })
        elif isinstance(r, dict):
            clean_results.append(r)
        else:
            clean_results.append({
                "source": "unknown",
                "status": "error",
                "data": f"Unexpected type: {type(r).__name__}",
            })

    return {**state, "raw_data": clean_results}


# ── Node 2: LLM Synthesis ───────────────────────────────────────────────────

def _to_int_rent(val) -> int | None:
    """Coerce LLM rent value (int or string) to int; return None if unparseable."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


async def synthesis_node(state: RentRadarState) -> RentRadarState:
    """
    Sends all raw data to Groq (gpt-oss-120b) for structured synthesis.
    Groq is free — no credits needed.
    """
    raw = state["raw_data"]
    query_desc = f"{state['query'].get('bhk', '?')} in {state['query'].get('locality', 'Bangalore')}"

    exhausted_sources = [
        item.get("source", "unknown")
        for item in raw
        if isinstance(item, dict) and item.get("credit_exhausted")
    ]
    all_failed = bool(raw) and all(item.get("status") != "ok" for item in raw)

    # Credit exhaustion is checked independently of whether EVERY source
    # failed. It used to be nested inside the total-outage branch, so a
    # partial exhaustion — plausible if Anakin's search and wire APIs bill
    # from separate pools — degraded results silently: some sources still
    # returned data, the code took the healthy path, and nobody was told
    # that the thing costing money had run out.
    if exhausted_sources:
        if source_health.mark_credit_exhausted():
            scope = (
                "every live data source"
                if all_failed
                else f"some data sources ({', '.join(exhausted_sources)})"
            )
            consequence = (
                'Users will keep seeing a "sources unavailable" message until this is fixed.'
                if all_failed
                else "Searches still work but return fewer results than they should, with no "
                     "visible error — so this will not be obvious from the site itself."
            )
            asyncio.create_task(send_admin_alert(
                "Urgent- RentRadar Credits expired",
                f'A user just searched for "{query_desc}" and {scope} failed with an error '
                "indicating the Anakin API credits have run out.\n\n"
                "Action needed: recharge your Anakin account balance, or rotate "
                f"ANAKIN_API_KEY if you've switched keys.\n\n{consequence}",
            ))
    else:
        source_health.clear_credit_exhausted()

    # If every data source failed (e.g. Anakin quota exhausted / network down),
    # don't waste an LLM call producing a misleading "no listings" brief — tell
    # the user the sources are unavailable so the UI can show an honest message.
    if all_failed:
        is_new_outage = source_health.mark_degraded(
            "Anakin credits exhausted" if exhausted_sources else
            "All live data sources failed on the last search — likely Anakin "
            "credits exhausted or a network issue."
        )
        # Only page the admin on the moment of transition into an outage, not
        # on every subsequent search while it's still down. A credit-specific
        # alert has already gone out above, so this covers the other causes.
        if is_new_outage and not exhausted_sources:
            asyncio.create_task(send_admin_alert(
                "RentRadar alert: all live data sources are down",
                f'A user just searched for "{query_desc}" and every live data source failed.\n\n'
                "This could be Anakin credits running out or a network/API outage — check "
                "the Render logs for the exact error.\n\n"
                'Users will keep seeing a "sources unavailable" message until this is fixed.',
            ))
        return {
            **state,
            "brief": json.dumps({
                "sources_unavailable": True,
                "locality": state["query"].get("locality", "Bangalore"),
                "message": "All live data sources are currently unavailable. "
                           "This usually means the Anakin API credits are exhausted "
                           "or the network is down. Please try again shortly.",
            }),
        }

    # At least one source came back — sources are healthy again.
    source_health.mark_healthy()

    context, ref_map = build_context(state["raw_data"], state["query"])

    client = _groq_client()
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=2048,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )

    brief_text = response.choices[0].message.content

    # Extract JSON even when the model wraps it in markdown fences
    cleaned = brief_text.strip()
    # Try regex first: grab content between first { and last }
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(0)

    # Validate JSON — wrap in safe error dict if malformed
    try:
        brief_obj = json.loads(cleaned)
        listings = brief_obj.get("top_listings", [])
        for listing in listings:
            if isinstance(listing, dict):
                # Map the cited ref to its exact page URL AND authoritative source,
                # so the displayed platform always matches the link it opens.
                ref = listing.pop("ref", None)
                mapped = ref_map.get(ref) if ref else None
                if mapped:
                    listing["url"] = mapped["url"]
                    listing["source"] = mapped["source"]
                else:
                    listing["url"] = None

        # Resolve max_rent early so budget filter and budget_note can both use it
        max_rent = state["query"].get("max_rent")

        # Hard budget filter — always enforce regardless of LLM behaviour.
        # Rules:
        #   known rent ≤ max  → keep (normalise to int)
        #   known rent > max  → drop (over budget)
        #   rent is null/unknown → KEEP (we cannot verify it's over budget;
        #     dropping it silently causes "no listings found" when real
        #     properties exist but their price wasn't in the snippet)
        if max_rent:
            filtered = []
            for l in listings:
                rv = _to_int_rent(l.get("rent"))
                if rv is None:
                    filtered.append(l)          # unknown price — keep
                elif rv <= max_rent:
                    l["rent"] = rv              # normalise to int
                    filtered.append(l)
                # else: confirmed over budget — drop
            listings = filtered

        # Adaptive diversity guarantee: when more than one platform contributed,
        # cap each platform at 2 so no single source can dominate the results.
        # When only one platform has data, keep up to 4 from it.
        listings = [l for l in listings if isinstance(l, dict)]
        distinct_sources = {l.get("source") for l in listings}
        if len(distinct_sources) > 1:
            per_source_cap, seen = 2, {}
            kept = []
            for l in listings:
                src = l.get("source")
                if seen.get(src, 0) < per_source_cap:
                    seen[src] = seen.get(src, 0) + 1
                    kept.append(l)
            listings = kept
        else:
            listings = listings[:4]
        # Re-rank 1..N after filtering
        for i, l in enumerate(listings, start=1):
            l["rank"] = i
        brief_obj["top_listings"] = listings

        # Deterministic budget_note handling:
        # - If we have in-budget listings, remove any LLM budget_note (not needed)
        # - If hard filter removed ALL listings, set an honest budget_note
        if max_rent:
            if listings:
                # All remaining listings are in-budget (hard filter ran above)
                brief_obj.pop("budget_note", None)
            else:
                brief_obj["budget_note"] = (
                    f"No listings found at or below ₹{max_rent:,}/mo in this area. "
                    "The prices shown in search results were above your budget."
                )

        brief = json.dumps(brief_obj)
    except (json.JSONDecodeError, ValueError):
        brief = json.dumps({"error": "synthesis_failed", "raw": brief_text})

    return {**state, "brief": brief}


# ── Build Graph ─────────────────────────────────────────────────────────────

def build_agent():
    graph = StateGraph(RentRadarState)
    graph.add_node("parallel_fetch", parallel_fetch_node)
    graph.add_node("synthesis", synthesis_node)
    graph.set_entry_point("parallel_fetch")
    graph.add_edge("parallel_fetch", "synthesis")
    graph.add_edge("synthesis", END)
    return graph.compile()


agent = build_agent()
