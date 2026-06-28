"""
LangGraph agent for RentRadar.

Graph:
  parallel_fetch_node  →  synthesis_node  →  END

Node 1 fires 7 async fetches simultaneously (Wire + Universal Scraper).
Node 2 sends all raw data to Claude Sonnet for structured synthesis.
"""

import asyncio
import json
import os
from typing import TypedDict, List

from langgraph.graph import StateGraph, END
from anthropic import Anthropic

from tools.holocron import fetch_reddit, fetch_google_trends, fetch_hackernews, fetch_twitter
from tools.scraper import fetch_nobroker, fetch_magicbricks, fetch_housing
from prompts import SYSTEM_PROMPT, build_context

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class RentRadarState(TypedDict):
    query: dict           # parsed query params from parser.py
    raw_data: List[dict]  # all fetched results (7 sources)
    brief: str            # final synthesized JSON brief
    error: str            # any critical pipeline error


# ── Node 1: Parallel Fetch ──────────────────────────────────────────────────

async def parallel_fetch_node(state: RentRadarState) -> RentRadarState:
    """
    Fires all 7 data fetches simultaneously.
    - Wire (Holocron): Reddit, Google Trends, Hacker News, Twitter/X
    - Universal Scraper: NoBroker, MagicBricks, Housing.com

    Uses return_exceptions=True so a single timeout never kills the pipeline.
    """
    q = state["query"]
    locality = q["locality"]
    bhk = q["bhk"]
    max_rent = q["max_rent"]

    results = await asyncio.gather(
        fetch_reddit(locality, bhk),
        fetch_google_trends(locality),
        fetch_hackernews(locality),
        fetch_twitter(locality),
        fetch_nobroker(locality, bhk, max_rent),
        fetch_magicbricks(locality, bhk, max_rent),
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
    Sends all raw data to Claude Sonnet.
    Returns a structured JSON rental brief.
    """
    context = build_context(state["raw_data"], state["query"])

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    brief_text = response.content[0].text

    # Validate Claude returned parseable JSON; if not, wrap it so the
    # frontend fallback card handles it gracefully instead of crashing.
    try:
        cleaned = brief_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        json.loads(cleaned)
        brief = cleaned
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
