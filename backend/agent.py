"""
LangGraph agent for RentRadar.

Graph:
  parallel_fetch_node  →  synthesis_node  →  END

Node 1 fires 8 async fetches simultaneously (free sentiment APIs + SearXNG search).
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
from groq import AsyncGroq

from tools.sentiment_sources import fetch_google_news, fetch_hackernews
from tools.scraper import (
    fetch_nobroker,
    fetch_olx,
    fetch_housing,
    fetch_99acres,
    fetch_magicbricks,
)
from tools.community import fetch_community
from prompts import SYSTEM_PROMPT, build_context
from channels.email import send_admin_alert
import source_health


def _groq_client() -> AsyncGroq:
    """Create Groq client at call time so the key is always fresh from env."""
    return AsyncGroq(api_key=os.getenv("GROQ_API_KEY", ""))


# asyncio only holds a weak reference to a task created via create_task — with
# nothing else referencing it, the task can be garbage-collected mid-flight,
# silently dropping the outage alert exactly when it matters most. Keeping a
# strong reference here until it finishes (discarded via the done-callback)
# is the fix asyncio's own docs recommend.
_background_tasks: set = set()


def _fire_and_forget(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


class RentRadarState(TypedDict):
    query: dict           # parsed query params from parser.py
    raw_data: List[dict]  # all fetched results (8 sources)
    brief: str            # final synthesized JSON brief
    error: str            # any critical pipeline error


# ── Node 1: Parallel Fetch ──────────────────────────────────────────────────

async def parallel_fetch_node(state: RentRadarState) -> RentRadarState:
    """
    Fires all 8 data fetches simultaneously.
    - Free APIs:   Google News, Hacker News
    - SearXNG:     NoBroker, OLX, Housing.com, 99acres, MagicBricks
    - Telegram:    Community (user-submitted listings — see tools/community.py)

    99acres and MagicBricks are added as additional SearXNG-searchable sources
    because their individual listing pages are well-indexed by public search
    engines (Google/Bing find specific flat pages, not just browse pages),
    unlike NoBroker/OLX/Housing.com whose search-indexed pages are mostly
    browse/category pages. Having 5 portal sources increases the chance that
    at least 2-3 return specific listings for any given locality.

    Uses return_exceptions=True so a single timeout never kills the pipeline.
    """
    q = state["query"]
    locality = q["locality"]
    bhk = q["bhk"]
    max_rent = q["max_rent"]
    min_rent = q.get("min_rent")

    results = await asyncio.gather(
        fetch_google_news(locality),
        fetch_hackernews(locality),
        fetch_nobroker(locality, bhk, max_rent),
        fetch_olx(locality, bhk, max_rent),
        fetch_housing(locality, bhk, max_rent),
        fetch_99acres(locality, bhk, max_rent),
        fetch_magicbricks(locality, bhk, max_rent),
        fetch_community(locality, bhk, max_rent, min_rent),
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
    """Coerce LLM rent value (int or string) to int; return None if unparseable.

    The model sees comma-formatted prices in its own input (prompts.py tags
    snippets with "[PRICE: ₹45,000]") and can echo that formatting back in
    "rent" instead of a bare int — int("45,000") raises ValueError, which
    would otherwise make a real over-budget listing look like an unknown
    price and slip past the hard budget filter below.
    """
    if val is None:
        return None
    if isinstance(val, str):
        val = val.replace(",", "").replace("₹", "").strip()
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _cited(claim, ref_map: dict) -> dict | None:
    """
    Turn one LLM area claim into a source-backed one, or reject it.

    No citation, no claim. The model is asked (prompts.py EVIDENCE RULE) to
    tag every flag / scam alert / trend note with the [REF] of the headline
    it came from; anything citing a ref we didn't actually give it is an
    unsupported assertion dressed as a finding, which is precisely what made
    these read as fabricated — a city-wide leasing fraud rendered as "this
    locality has a scam problem", with nothing a reader could check. Same
    discipline already applied to listing URLs above.

    Plain strings are rejected for the same reason: no ref, no source.
    """
    if not isinstance(claim, dict):
        return None
    text = (claim.get("text") or "").strip()
    source = ref_map.get(claim.get("ref"))
    if not text or not source or not source.get("url"):
        return None
    return {
        "text": text,
        "url": source["url"],
        "source": source.get("source"),
        "published_at": source.get("published_at"),
        "locality_specific": bool(source.get("mentions_locality")),
    }


async def synthesis_node(state: RentRadarState) -> RentRadarState:
    """
    Sends all raw data to Groq (gpt-oss-120b) for structured synthesis.
    Groq is free — no credits needed.
    """
    raw = state["raw_data"]
    query_desc = f"{state['query'].get('bhk', '?')} in {state['query'].get('locality', 'Bangalore')}"

    # Two different questions, deliberately kept separate:
    #   - scraped_all_failed: are the sources RentRadar actually depends on
    #     for infrastructure health (portals + News/HN) down?
    #     This drives source_health + the admin outage alert.
    #   - has_community_listing: did a Telegram-submitted listing match?
    #     This is a normal, slow-moving adoption signal (most searches find
    #     nothing there for a long time) — it must never count toward "are
    #     the scraped sources down", or an empty Community result would
    #     mask a real outage every single search.
    # Conflating the two would get either wrong: counting Community toward
    # scraped_all_failed makes the admin alert fire on every quiet search;
    # excluding it from the skip-synthesis decision below would throw away
    # a real submitted listing just because the scraped sources happened to
    # be down at the same time.
    scraped = [
        item for item in raw
        if item.get("source") not in ("Community",)
    ]
    community_item = next((item for item in raw if item.get("source") == "Community"), None)
    has_community_listing = bool(community_item and community_item.get("status") == "ok")

    scraped_all_failed = bool(scraped) and all(item.get("status") != "ok" for item in scraped)

    if scraped_all_failed:
        is_new_outage = source_health.mark_degraded(
            "All live data sources failed on the last search — likely the "
            "search backend or a network issue."
        )
        # Only page the admin on the moment of transition into an outage, not
        # on every subsequent search while it's still down.
        if is_new_outage:
            _fire_and_forget(send_admin_alert(
                "RentRadar alert: all live data sources are down",
                f'A user just searched for "{query_desc}" and every live data source failed.\n\n'
                "Check the Render logs for the exact error — could be the SearXNG "
                "instance being rate-limited upstream, or a network/API outage.\n\n"
                'Users will keep seeing a "sources unavailable" message until this is fixed.',
            ))
        # Still worth an LLM call if a community listing matched — that's a
        # real result the user shouldn't lose just because the scraped
        # sources happened to be down on the same search.
        if not has_community_listing:
            return {
                **state,
                "brief": json.dumps({
                    "sources_unavailable": True,
                    "locality": state["query"].get("locality", "Bangalore"),
                    "message": "All live data sources are currently unavailable. "
                               "Please try again shortly.",
                }),
            }
    else:
        # At least one scraped source came back — sources are healthy again.
        source_health.mark_healthy()

    context, ref_map = build_context(state["raw_data"], state["query"])

    client = _groq_client()
    response = await client.chat.completions.create(
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
        # Filter non-dict entries immediately — a malformed LLM completion
        # can put a bare string in this array, and every loop below assumes
        # dict access (.get()/.pop()) with no guard of its own.
        listings = [l for l in brief_obj.get("top_listings", []) if isinstance(l, dict)]
        for listing in listings:
            # Map the cited ref to its exact page URL AND authoritative source,
            # so the displayed platform always matches the link it opens.
            ref = listing.pop("ref", None)
            mapped = ref_map.get(ref) if ref else None
            if mapped:
                listing["url"] = mapped["url"]
                listing["source"] = mapped["source"]
            else:
                listing["url"] = None

        # Captured before the community merge below: did the LLM itself see
        # any listings at all? It never sees community submissions (see
        # above), so if this is empty its "verdict" prose was written
        # believing nothing was available — stale and contradictory the
        # moment a community listing gets merged in afterward. Used below to
        # decide whether the verdict needs a deterministic override, the
        # same way budget_note already gets one.
        llm_had_listings = bool(listings)

        # Community listings are already structured (parsed once at
        # submission time — see community_store.py) and never touched the
        # LLM prompt, so they skip the ref-resolution loop above entirely
        # and join here instead. From this point on they go through the
        # exact same budget filter, diversity cap, and re-rank as every
        # LLM-extracted listing — no special-casing needed past this line.
        if has_community_listing:
            listings.extend(community_item["listings"])

        # Resolve the budget early so the filter and budget_note both use it
        max_rent = state["query"].get("max_rent")
        min_rent = state["query"].get("min_rent")

        # Hard budget filter — always enforce regardless of LLM behaviour.
        # Rules:
        #   known rent within bounds → keep (normalise to int)
        #   known rent out of bounds → drop
        #   rent is null/unknown     → KEEP (we cannot verify it's out of
        #     range; dropping it silently causes "no listings found" when
        #     real properties exist but their price wasn't in the snippet)
        # `is not None` rather than truthy: a max_rent of 0 must still filter
        # (everything is over budget), not silently skip filtering entirely.
        if max_rent is not None or min_rent is not None:
            filtered = []
            for l in listings:
                rv = _to_int_rent(l.get("rent"))
                if rv is None:
                    filtered.append(l)          # unknown price — keep
                    continue
                if max_rent is not None and rv > max_rent:
                    continue                    # confirmed over budget — drop
                if min_rent is not None and rv < min_rent:
                    continue                    # below the floor they asked for
                l["rent"] = rv                  # normalise to int
                filtered.append(l)
            listings = filtered

        # Adaptive diversity guarantee: when more than one platform contributed,
        # cap each platform at 2 so no single source can dominate the results.
        # When only one platform has data, keep up to 4 from it.
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

        # Enforce the EVIDENCE RULE rather than trusting the model to have
        # followed it: every area claim must resolve to a headline we
        # actually supplied, or it doesn't ship. See _cited().
        for field in ("green_flags", "red_flags", "scam_alerts"):
            brief_obj[field] = [
                c for c in (_cited(x, ref_map) for x in brief_obj.get(field) or []) if c
            ]
        brief_obj["trend_note"] = _cited(brief_obj.get("trend_note"), ref_map)
        if brief_obj["trend_note"] is None:
            # An uncited trend note leaves "price_trend" as a bare
            # rising/falling arrow with nothing behind it — drop both.
            brief_obj.pop("trend_note", None)
            brief_obj.pop("price_trend", None)

        # hn_signal is a free-text "tech-worker view" summary, not a cited
        # claim — so it's only trustworthy when Hacker News actually returned
        # something. When HN is empty/unavailable (common), drop it rather
        # than let the model invent a sentiment read from nothing.
        hn_ok = any(
            item.get("source") == "Hacker News" and item.get("status") == "ok" and item.get("items")
            for item in raw
        )
        if not hn_ok:
            brief_obj.pop("hn_signal", None)

        # Same for the locality scores: keep only dimensions the model named
        # a resolvable headline for. One-decimal scores drawn from nothing
        # are the single most authoritative-looking thing in the whole brief.
        evidence = brief_obj.pop("scores_evidence", None) or {}
        scores = brief_obj.get("locality_scores")
        if isinstance(scores, dict):
            kept_scores = {
                dim: val for dim, val in scores.items()
                if dim != "overall" and ref_map.get(evidence.get(dim))
            }
            # "overall" is a summary of the others — it only survives if
            # something it could summarise did.
            if kept_scores and isinstance(scores.get("overall"), (int, float)):
                kept_scores["overall"] = scores["overall"]
            brief_obj["locality_scores"] = kept_scores
        else:
            brief_obj["locality_scores"] = {}

        # Deterministic budget_note handling:
        # - If we have in-budget listings, remove any LLM budget_note (not needed)
        # - If hard filter removed ALL listings, set an honest budget_note
        if max_rent is not None:
            if listings:
                # All remaining listings are in-budget (hard filter ran above)
                brief_obj.pop("budget_note", None)
            elif min_rent is not None:
                brief_obj["budget_note"] = (
                    f"No listings found between ₹{min_rent:,} and ₹{max_rent:,}/mo "
                    "in this area. The prices shown in search results were outside "
                    "that range."
                )
            else:
                brief_obj["budget_note"] = (
                    f"No listings found at or below ₹{max_rent:,}/mo in this area. "
                    "The prices shown in search results were above your budget."
                )

        # The LLM wrote "verdict" (and everything else) believing there were
        # no listings at all — that prose is stale and self-contradicting
        # the moment a community submission is the only reason listings is
        # non-empty now. Override with something that's actually true
        # rather than show "no listings available" directly above a card
        # that is one.
        if listings and not llm_had_listings:
            # Count flats, not submitters: two listings from one person is
            # not "2 people have submitted", and we don't expose who sent
            # what here anyway.
            count = len(listings)
            brief_obj["verdict"] = (
                "No listings from the scraped portals matched this search, but "
                f"{count} matching {'flat was' if count == 1 else 'flats were'} "
                "submitted directly via RentRadar's Telegram bot — see below. "
                "Scraped-portal coverage for this area may just be thin right now; "
                "try again later for more options."
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
