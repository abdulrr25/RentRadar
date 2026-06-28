"""
LangGraph agent for RentRadar.

Graph:
  parallel_fetch_node  →  synthesis_node  →  END

Node 1 fires 6 async fetches simultaneously (Wire + Universal Scraper).
Node 2 sends all raw data to Groq (Llama 3.1 70B) for structured synthesis.
Groq is free — sign up at console.groq.com.
"""

import asyncio
import json
import os
from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from groq import Groq

from tools.holocron import fetch_reddit, fetch_google_news, fetch_hackernews
from tools.scraper import fetch_nobroker, fetch_olx, fetch_housing
from prompts import SYSTEM_PROMPT, build_context


def _groq_client() -> Groq:
    """Create Groq client at call time so the key is always fresh from env."""
    return Groq(api_key=os.getenv("GROQ_API_KEY", ""))


class RentRadarState(TypedDict):
    query: dict           # parsed query params from parser.py
    raw_data: List[dict]  # all fetched results (6 sources)
    brief: str            # final synthesized JSON brief
    error: str            # any critical pipeline error


# ── Node 1: Parallel Fetch ──────────────────────────────────────────────────

async def parallel_fetch_node(state: RentRadarState) -> RentRadarState:
    """
    Fires all 6 data fetches simultaneously.
    - Wire: Reddit, Google News, Hacker News
    - Universal Scraper: NoBroker, MagicBricks, Housing.com

    Uses return_exceptions=True so a single timeout never kills the pipeline.
    """
    q = state["query"]
    locality = q["locality"]
    bhk = q["bhk"]
    max_rent = q["max_rent"]

    results = await asyncio.gather(
        fetch_reddit(locality, bhk),
        fetch_google_news(locality),
        fetch_hackernews(locality),
        fetch_nobroker(locality, bhk, max_rent),
        fetch_olx(locality, bhk, max_rent),
        fetch_housing(locality, bhk),
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

async def synthesis_node(state: RentRadarState) -> RentRadarState:
    """
    Sends all raw data to Groq (Llama 3.1 70B) for structured synthesis.
    Groq is free — no credits needed.
    """
    # If every data source failed (e.g. Anakin quota exhausted / network down),
    # don't waste an LLM call producing a misleading "no listings" brief — tell
    # the user the sources are unavailable so the UI can show an honest message.
    if state["raw_data"] and all(
        item.get("status") != "ok" for item in state["raw_data"]
    ):
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

    context, ref_map = build_context(state["raw_data"], state["query"])

    client = _groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=2048,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )

    brief_text = response.choices[0].message.content

    # Extract JSON even when the model wraps it in markdown fences
    import re
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

        # Deterministic budget_note: only keep it if NOTHING is at/under budget.
        # Stops the LLM contradicting itself (note vs. in-budget listings shown).
        max_rent = state["query"].get("max_rent")
        if max_rent and listings:
            within = [
                l for l in listings
                if isinstance(l, dict) and isinstance(l.get("rent"), (int, float))
                and l["rent"] <= max_rent
            ]
            if within:
                brief_obj.pop("budget_note", None)

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
