"""
fetch_speech_context.py — Congressional Speech Context Fetcher

5-level fallback search for speech claim verification:
  Level 1: MCP Playwright (Google/X.com) — via agent tool calls
  Level 2: minimax WebSearch
  Level 3: Alternative query reformulation
  Level 4: Knowledge Base fallback
  Level 5: Annotate "DATA INSUFFICIENT"

Cache: data/speech_search_cache.json (per speech_id)

Usage:
    python scripts/fetch_speech_context.py --speech-id CONGRESS_001 --claims claim1,claim2

The script coordinates and provides URLs/queries. Actual browser
navigation is performed by the agent via MCP Playwright tool calls.
"""

import os
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from typing import Optional

BASE_DIR = Path(__file__).parent.parent
CACHE_FILE = BASE_DIR / "data" / "speech_search_cache.json"

# Ensure data directory exists
(BASE_DIR / "data").mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Cache Management
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load search cache from disk."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_cache(cache: dict) -> None:
    """Save search cache to disk."""
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, default=str)


def get_cache_key(speech_id: str, claim: str) -> str:
    """Generate cache key for a speech+claim combination."""
    key_str = f"{speech_id}:{claim[:200]}"
    return hashlib.md5(key_str.encode()).hexdigest()[:16]


def get_cached_result(speech_id: str, claim: str) -> Optional[dict]:
    """Get cached search result if available and fresh (within 24h)."""
    cache = load_cache()
    key = get_cache_key(speech_id, claim)
    entry = cache.get(key)
    if not entry:
        return None
    # Check freshness (24h)
    try:
        cached_time = datetime.fromisoformat(entry.get("cached_at", "2000-01-01"))
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        if age_hours > 24:
            return None  # stale
    except Exception:
        return None
    return entry


def cache_result(speech_id: str, claim: str, result: dict, level: int) -> None:
    """Cache a search result."""
    cache = load_cache()
    key = get_cache_key(speech_id, claim)
    cache[key] = {
        "speech_id": speech_id,
        "claim": claim,
        "level": level,
        "result": result,
        "cached_at": datetime.now().isoformat(),
    }
    save_cache(cache)


# ---------------------------------------------------------------------------
# Search Strategy Generator
# ---------------------------------------------------------------------------

def generate_google_url(query: str) -> str:
    """Generate Google search URL for a query."""
    encoded = quote(query)
    return f"https://www.google.com/search?q={encoded}&hl=en-US&gl=US"


def generate_google_news_url(query: str) -> str:
    """Generate Google News search URL."""
    encoded = quote(query)
    return f"https://news.google.com/search?q={encoded}&hl=en-US&gl=US&ceid=US%3Aen"


def generate_x_com_url(query: str) -> str:
    """Generate X.com search URL."""
    encoded = quote(query)
    return f"https://x.com/search?q={encoded}&f=live"


def generate_polymarket_url(event_query: str = "iran war") -> str:
    """Generate Polymarket search URL."""
    encoded = quote(event_query)
    return f"https://polymarket.com/events/{encoded}"


def get_search_urls_for_claim(claim: str) -> dict:
    """
    Generate Level 1 MCP Playwright URLs for a given claim.

    Returns URLs for Google, Google News, and X.com searches.
    """
    # Clean claim for URL
    clean_claim = claim[:150]  # truncate long claims

    return {
        "google": {
            "url": generate_google_url(clean_claim),
            "description": "Google search for claim verification",
        },
        "google_news": {
            "url": generate_google_news_url(clean_claim),
            "description": "Google News for recent articles",
        },
        "x_com": {
            "url": generate_x_com_url(clean_claim),
            "description": "X.com live search for real-time reactions",
        },
    }


# ---------------------------------------------------------------------------
# Speech Context Data Structure
# ---------------------------------------------------------------------------

def build_speech_context(speech_id: str, claims: list) -> dict:
    """
    Build speech context data structure for a list of claims.

    This returns the search URLs and fallback strategy for each claim.
    Actual data fetching happens via agent tool calls.
    """
    context = {
        "speech_id": speech_id,
        "fetched_at": datetime.now().isoformat(),
        "cache_file": str(CACHE_FILE),
        "claims": [],
    }

    for i, claim in enumerate(claims):
        # Check cache first
        cached = get_cached_result(speech_id, claim)

        claim_entry = {
            "claim_id": f"claim_{i+1}",
            "claim": claim,
            "cached": cached is not None,
            "search_urls": get_search_urls_for_claim(claim),
            "fallback_strategy": {
                "L1": "MCP Playwright (Google/X.com) — agent tool calls",
                "L2": "minimax WebSearch — if L1 fails or blocked",
                "L3": "Alternative query reformulation — if L2 returns 0 results",
                "L4": "Knowledge Base fallback + annotation",
                "L5": "DATA INSUFFICIENT — skip and continue",
            },
        }

        if cached:
            claim_entry["cached_result"] = cached["result"]
            claim_entry["cached_level"] = cached["level"]
            claim_entry["cached_at"] = cached["cached_at"]

        context["claims"].append(claim_entry)

    return context


def build_market_data_urls() -> dict:
    """Build URLs for real-time market data sources."""
    return {
        "vix": {
            "source": "CBOE VIX",
            "yfinance_url": "https://finance.yahoo.com/quote/%5EVIX/",
            "description": "VIX fear index — key pain point indicator",
        },
        "crude_oil": {
            "source": "WTI Crude Oil",
            "yfinance_url": "https://finance.yahoo.com/quote/CL%3DF/",
            "description": "Oil prices — geopolitical risk indicator",
        },
        "sp500": {
            "source": "S&P 500",
            "yfinance_url": "https://finance.yahoo.com/quote/SPY/",
            "description": "S&P 500 ETF — market impact indicator",
        },
        "gold": {
            "source": "Gold",
            "yfinance_url": "https://finance.yahoo.com/quote/GLD/",
            "description": "Gold ETF — safe haven demand",
        },
        "defense_etf": {
            "source": "Defense Sector",
            "yfinance_url": "https://finance.yahoo.com/quote/XLE/",
            "description": "Energy/Defense sector ETF",
        },
        "polymarket": {
            "source": "Polymarket",
            "url": "https://polymarket.com/",
            "description": "Prediction markets for geopolitical events",
        },
    }


# ---------------------------------------------------------------------------
# Fallback Result Builder
# ---------------------------------------------------------------------------

def build_fallback_result(
    level: int,
    query: str,
    data: dict,
    source_note: str,
) -> dict:
    """
    Build a standardized fallback result at any level.

    Args:
        level: Fallback level (1-5)
        query: The search query that was used
        data: The actual data found (or empty if insufficient)
        source_note: Human-readable source description
    """
    return {
        "level": level,
        "query": query,
        "data": data,
        "source_note": source_note,
        "timestamp": datetime.now().isoformat(),
    }


def build_l4_kb_fallback(claim: str) -> dict:
    """
    Build a Level 4 Knowledge Base fallback result.

    Uses training knowledge to fill gaps, annotated as L4.
    """
    return build_fallback_result(
        level=4,
        query=f"[KB estimated] {claim}",
        data={},
        source_note="[Source: KB (L4), verify with real-time data] — using training knowledge as fallback",
    )


def build_l5_insufficient(claim: str, field_name: str) -> dict:
    """Build a Level 5 DATA INSUFFICIENT annotation."""
    return build_fallback_result(
        level=5,
        query=f"[INSUFFICIENT] {claim}",
        data={"DATA_INSUFFICIENT": field_name},
        source_note=f"[DATA INSUFFICIENT: {field_name} — skipped, marked for manual review]",
    )


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch speech context with 5-level fallback")
    parser.add_argument("--speech-id", required=True, help="Unique speech identifier")
    parser.add_argument("--claims", required=True, help="Comma-separated list of claims to verify")
    parser.add_argument("--cache-only", action="store_true", help="Only return cached results")
    parser.add_argument("--output", help="Output JSON file path (optional)")

    args = parser.parse_args()

    claims = [c.strip() for c in args.claims.split(",") if c.strip()]

    print(f"Speech ID: {args.speech_id}")
    print(f"Claims to verify: {len(claims)}")
    print(f"Cache file: {CACHE_FILE}")

    # Build context
    context = build_speech_context(args.speech_id, claims)

    # Add market data URLs
    context["market_data_urls"] = build_market_data_urls()

    # Print summary
    print("\n--- Search Strategy Summary ---")
    cached_count = sum(1 for c in context["claims"] if c.get("cached"))
    print(f"  Cached results: {cached_count}/{len(claims)}")
    print(f"  Fresh searches needed: {len(claims) - cached_count}")

    for i, claim_entry in enumerate(context["claims"]):
        status = "CACHED" if claim_entry.get("cached") else "NEEDS_SEARCH"
        print(f"\n  [{i+1}] {status}: {claim_entry['claim'][:80]}...")
        if not claim_entry.get("cached"):
            print(f"      L1: {claim_entry['search_urls']['google']['url'][:60]}...")

    # Save output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(context, f, indent=2, default=str)
        print(f"\n[OK] Saved to {args.output}")

    return context


if __name__ == "__main__":
    main()
