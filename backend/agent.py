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
from tools.scraper import fetch_nobroker, fetch_magicbricks, fetch_housing
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
    Sends all raw data to Groq (Llama 3.1 70B) for structured synthesis.
    Groq is free — no credits needed.
    """
    context = build_context(state["raw_data"], state["query"])

    client = _groq_client()
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        max_tokens=2048,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
    )

    brief_text = response.choices[0].message.content

    # Strip markdown fences if the model wraps its JSON output
    cleaned = brief_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[-1] if cleaned.count("```") >= 2 else cleaned
        cleaned = cleaned.lstrip("json").strip().rstrip("```").strip()

    # Validate JSON — wrap in safe error dict if malformed
    try:
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
