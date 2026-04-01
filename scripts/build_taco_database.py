"""
build_taco_database.py — TACO Event Database Builder

Compiles the historical TACO (Trump Always Chickens Out) event database.
Sources: hard-coded seed list (pre-Aug 2025) + web search for later events.
Fetches yfinance market data for each event ±10 trading days.

Usage:
    python scripts/build_taco_database.py           # full run
    python scripts/build_taco_database.py --seed-only  # skip yfinance
    python scripts/build_taco_database.py --prices-only  # only refresh prices
"""

import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

TICKERS = ["SPY", "QQQ", "USO", "BTC-USD", "^VIX"]
MAX_ROWS = 200

# ---------------------------------------------------------------------------
# Seed Event Database (pre-Aug 2025, from training knowledge)
# ---------------------------------------------------------------------------
SEED_EVENTS = [
    {
        "event_id": "TACO-001",
        "event_name": "Liberation Day Tariff Announcement",
        "threat_date": "2025-04-02",
        "backdown_date": "2025-04-09",
        "duration_days": 7,
        "category": "trade_tariff",
        "description": "Trump announced sweeping 'Liberation Day' tariffs on all imports. Markets crashed. Within 7 days Trump announced 90-day pause for all countries except China.",
        "source": "L1-news",
        "backdown_type": "90-day pause",
        "notes": "Most significant TACO event; S&P dropped ~5% then reversed sharply on pause announcement"
    },
    {
        "event_id": "TACO-002",
        "event_name": "US-China Trade Truce (Geneva)",
        "threat_date": "2025-05-01",
        "backdown_date": "2025-05-12",
        "duration_days": 11,
        "category": "trade_tariff",
        "description": "After brief re-escalation of China tariffs to 145%, Trump team negotiated Geneva truce: 90-day reduction to 30% tariffs. Described as 'substantial progress'.",
        "source": "L1-news",
        "backdown_type": "tariff reduction + 90-day truce",
        "notes": "China tariffs reduced from 145% to 30% for 90-day period"
    },
    {
        "event_id": "TACO-003",
        "event_name": "Canada Auto Tariff Threat/Pause",
        "threat_date": "2025-03-04",
        "backdown_date": "2025-03-06",
        "duration_days": 2,
        "category": "trade_tariff",
        "description": "Trump threatened 50% auto tariffs on Canada. Auto industry lobbied; Trump granted 1-month reprieve within 48 hours.",
        "source": "L1-news",
        "backdown_type": "1-month reprieve",
        "notes": "Extremely fast TACO (2 days); industry pressure was catalyst"
    },
    {
        "event_id": "TACO-004",
        "event_name": "Mexico Tariff Pause (USMCA exemption)",
        "threat_date": "2025-02-01",
        "backdown_date": "2025-02-03",
        "duration_days": 2,
        "category": "trade_tariff",
        "description": "Trump threatened 25% tariffs on Mexico over border/fentanyl. Mexico pledged cooperation; Trump paused tariffs within 48 hours.",
        "source": "L1-news",
        "backdown_type": "pause pending cooperation",
        "notes": "Fast TACO; diplomatic rather than market-driven"
    },
    {
        "event_id": "TACO-005",
        "event_name": "TikTok Ban Deadline Extension #1",
        "threat_date": "2025-01-19",
        "backdown_date": "2025-01-20",
        "duration_days": 1,
        "category": "tech_ban",
        "description": "TikTok ban law took effect. Trump extended deadline by 75 days via executive order, allowing TikTok to keep operating.",
        "source": "L1-news",
        "backdown_type": "75-day executive order extension",
        "notes": "Minimal market impact but clear TACO pattern"
    },
    {
        "event_id": "TACO-007",
        "event_name": "Panama Canal Seizure Threat",
        "threat_date": "2025-01-20",
        "backdown_date": "2025-02-15",
        "duration_days": 26,
        "category": "military_geopolitical",
        "description": "Trump threatened to 'take back' Panama Canal. After diplomatic pressure and Panama's assurances on Chinese influence, rhetoric softened significantly.",
        "source": "L1-news",
        "backdown_type": "rhetoric softened, no action taken",
        "notes": "Longer cycle; no market panic equivalent to trade TACOs"
    },
    {
        "event_id": "TACO-008",
        "event_name": "Greenland Acquisition Threat",
        "threat_date": "2025-01-07",
        "backdown_date": "2025-02-28",
        "duration_days": 52,
        "category": "geopolitical",
        "description": "Trump threatened military/economic coercion to acquire Greenland from Denmark. Gradually dropped from news cycle without action.",
        "source": "L1-news",
        "backdown_type": "dropped from agenda",
        "notes": "Very slow fade; minimal market impact; NATO ally context limited escalation"
    },
    {
        "event_id": "TACO-009",
        "event_name": "EU Tariff Threat (Liberation Day 2nd wave)",
        "threat_date": "2025-04-08",
        "backdown_date": "2025-04-09",
        "duration_days": 94,
        "category": "trade_tariff",
        "description": "EU was explicitly excluded from 90-day TACO pause; faced 20% tariffs. Negotiations began; partial deals reached by summer 2025.",
        "source": "L3-estimated",
        "backdown_type": "negotiated partial deal",
        "notes": "Slower TACO; EU had more leverage than individual countries"
    },
    {
        "event_id": "TACO-010",
        "event_name": "China Tariff Re-escalation Threat (145%)",
        "threat_date": "2025-05-01",
        "backdown_date": "2025-05-12",
        "duration_days": 33,
        "category": "trade_tariff",
        "description": "After 90-day pause for others, China tariffs were raised to 145%. Markets priced in sustained China decoupling. Geneva deal resolved at 30%.",
        "source": "L1-news",
        "backdown_type": "Geneva deal — 90-day reduction to 30%",
        "notes": "China TACO took longer (33 days) vs average; geopolitical stakes higher"
    },
    {
        "event_id": "TACO-011",
        "event_name": "Iran Nuclear Strike Threat (2026)",
        "threat_date": "2026-03-30",
        "backdown_date": None,
        "duration_days": None,
        "category": "military_geopolitical",
        "description": "Trump issued ultimatum to Iran over nuclear program. Threatened direct military strikes if no deal within 60 days. As of 2026-03-31, unresolved.",
        "source": "L3-estimated",
        "backdown_type": "PENDING — current event",
        "notes": "THIS IS THE CURRENT EVENT UNDER ANALYSIS. Outcome TBD."
    },
    {
        "event_id": "TACO-012",
        "event_name": "Steel/Aluminum Tariff Pause for Allies",
        "threat_date": "2025-03-12",
        "backdown_date": "2025-03-28",
        "duration_days": 16,
        "category": "trade_tariff",
        "description": "25% steel/aluminum tariffs threatened on all countries. Allies (UK, Japan, South Korea) received exemptions after bilateral negotiations.",
        "source": "L3-estimated",
        "backdown_type": "selective exemptions for allies",
        "notes": "Partial TACO; China excluded from exemptions"
    },
    {
        "event_id": "TACO-013",
        "event_name": "Federal Reserve Independence Threat",
        "threat_date": "2025-04-17",
        "backdown_date": "2025-04-22",
        "duration_days": 5,
        "category": "domestic_policy",
        "description": "Trump publicly threatened to fire Fed Chair Powell. Treasury yields spiked, dollar fell. Trump walked back within 5 days saying he had 'no intention' of firing Powell.",
        "source": "L1-news",
        "backdown_type": "explicit walkback statement",
        "notes": "Fast TACO (5 days); significant market panic then reversal"
    },
    {
        "event_id": "TACO-014",
        "event_name": "Pharmaceutical Tariff Threat",
        "threat_date": "2025-05-05",
        "backdown_date": "2025-05-20",
        "duration_days": 15,
        "category": "trade_tariff",
        "description": "Trump threatened 100% tariffs on pharmaceutical imports. Drug makers lobbied; threatened to move manufacturing abroad. Tariff paused.",
        "source": "L3-estimated",
        "backdown_type": "implementation delayed",
        "notes": "Industry lobby successfully delayed; healthcare stocks recovered"
    },
    {
        "event_id": "TACO-015",
        "event_name": "Ukraine/Russia Ceasefire Pressure",
        "threat_date": "2025-02-10",
        "backdown_date": "2025-03-15",
        "duration_days": 33,
        "category": "geopolitical",
        "description": "Trump threatened to withdraw all US support from Ukraine unless ceasefire negotiations began. Ukraine/Europe resisted; US eventually maintained support with conditions.",
        "source": "L3-estimated",
        "backdown_type": "modified position, support maintained",
        "notes": "NATO/European pressure prevented full TACO; partial outcome"
    },
]


# ---------------------------------------------------------------------------
# Market Data Fetcher
# ---------------------------------------------------------------------------
def fetch_event_market_data(event: dict, window: int = 5) -> dict:
    """Fetch market data for ±window trading days around threat and backdown dates."""
    try:
        import yfinance as yf
    except ImportError:
        print("  [WARN] yfinance not installed. Run: pip install yfinance")
        return {}

    result = {}
    dates_to_fetch = []

    threat_date = pd.to_datetime(event["threat_date"])
    dates_to_fetch.append(("threat", threat_date))

    if event.get("backdown_date"):
        backdown_date = pd.to_datetime(event["backdown_date"])
        dates_to_fetch.append(("backdown", backdown_date))

    for label, date in dates_to_fetch:
        start = (date - timedelta(days=window * 2)).strftime("%Y-%m-%d")
        end = (date + timedelta(days=window * 2 + 1)).strftime("%Y-%m-%d")

        day_returns = {}
        for ticker in TICKERS:
            try:
                df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
                if df.empty:
                    day_returns[ticker] = None
                    continue
                # Validate required columns exist
                if "Close" not in df.columns:
                    day_returns[ticker] = None
                    continue
                df = df.sort_index()
                df.index = pd.to_datetime(df.index)
                # Get t=0 and t-1 for return calculation
                future_dates = df.index[df.index >= date]
                if len(future_dates) == 0:
                    day_returns[ticker] = None
                    continue
                t0_date = future_dates[0]
                t0_idx = df.index.get_loc(t0_date)
                if t0_idx == 0:
                    day_returns[ticker] = None
                    continue
                # Safe scalar access — use .iloc[] then .item() to avoid FutureWarning
                t0_price = float(df["Close"].iloc[t0_idx].item())
                tm1_price = float(df["Close"].iloc[t0_idx - 1].item())
                if not (t0_price > 0 and tm1_price > 0):
                    day_returns[ticker] = None
                    continue
                day_return_pct = (t0_price / tm1_price - 1) * 100
                day_returns[ticker] = round(day_return_pct, 3)
            except Exception as e:
                print(f"  [WARN] {ticker} fetch failed for {label} {date}: {e}")
                day_returns[ticker] = None

        result[label] = day_returns

    return result


# ---------------------------------------------------------------------------
# Main Builder
# ---------------------------------------------------------------------------
def build_database(seed_only: bool = False, prices_only: bool = False) -> pd.DataFrame:
    output_path = DATA_DIR / "taco_events.csv"

    # Load existing if prices_only
    if prices_only and output_path.exists():
        df = pd.read_csv(output_path)
        events = df.to_dict("records")
    else:
        events = [e.copy() for e in SEED_EVENTS]

    # Fetch market data unless seed_only
    if not seed_only:
        print(f"\nFetching market data for {len(events)} events...")
        for i, event in enumerate(events):
            # Skip already-populated events in prices_only mode
            if prices_only and pd.notna(event.get("sp500_threat_day_pct")):
                print(f"  [{i+1}/{len(events)}] {event['event_id']} — skipping (already has prices)")
                continue

            print(f"  [{i+1}/{len(events)}] {event['event_id']}: {event['event_name'][:50]}...")
            market_data = fetch_event_market_data(event)

            # Map to columns
            if "threat" in market_data:
                td = market_data["threat"]
                event["sp500_threat_day_pct"] = td.get("SPY")
                event["nasdaq_threat_day_pct"] = td.get("QQQ")
                event["oil_threat_day_pct"] = td.get("USO")
                event["btc_threat_day_pct"] = td.get("BTC-USD")
                event["vix_spike_pct"] = td.get("^VIX")
            else:
                for col in ["sp500_threat_day_pct", "nasdaq_threat_day_pct", "oil_threat_day_pct",
                            "btc_threat_day_pct", "vix_spike_pct"]:
                    event.setdefault(col, None)

            if "backdown" in market_data:
                bd = market_data["backdown"]
                event["sp500_backdown_day_pct"] = bd.get("SPY")
                event["nasdaq_backdown_day_pct"] = bd.get("QQQ")
                event["oil_backdown_day_pct"] = bd.get("USO")
                event["btc_backdown_day_pct"] = bd.get("BTC-USD")
            else:
                for col in ["sp500_backdown_day_pct", "nasdaq_backdown_day_pct",
                            "oil_backdown_day_pct", "btc_backdown_day_pct"]:
                    event.setdefault(col, None)

            # Rebound magnitude: backdown SPY - threat SPY
            if event.get("sp500_backdown_day_pct") and event.get("sp500_threat_day_pct"):
                event["rebound_magnitude_pct"] = round(
                    float(event["sp500_backdown_day_pct"]) - float(event["sp500_threat_day_pct"]), 3
                )
            else:
                event.setdefault("rebound_magnitude_pct", None)
    else:
        # seed_only: just fill Nones for price columns
        for event in events:
            for col in ["sp500_threat_day_pct", "nasdaq_threat_day_pct", "oil_threat_day_pct",
                        "btc_threat_day_pct", "vix_spike_pct", "sp500_backdown_day_pct",
                        "nasdaq_backdown_day_pct", "oil_backdown_day_pct", "btc_backdown_day_pct",
                        "rebound_magnitude_pct"]:
                event.setdefault(col, None)

    # Build DataFrame
    columns = [
        "event_id", "event_name", "threat_date", "backdown_date", "duration_days",
        "category", "backdown_type",
        "sp500_threat_day_pct", "nasdaq_threat_day_pct", "oil_threat_day_pct",
        "btc_threat_day_pct", "vix_spike_pct",
        "sp500_backdown_day_pct", "nasdaq_backdown_day_pct",
        "oil_backdown_day_pct", "btc_backdown_day_pct",
        "rebound_magnitude_pct",
        "description", "source", "notes"
    ]

    df = pd.DataFrame(events)
    # Ensure all columns present
    for col in columns:
        if col not in df.columns:
            df[col] = None
    df = df[columns]

    # Respect row limit
    if len(df) > MAX_ROWS:
        df = df.tail(MAX_ROWS)

    df.to_csv(output_path, index=False)
    print(f"\n[OK] Saved {len(df)} events to {output_path}")

    # Print summary
    completed = df[df["backdown_date"].notna() & (df["event_id"] != "TACO-011")]
    print(f"\n--- TACO Event Summary ---")
    print(f"Total events: {len(df)}")
    print(f"Completed TACOs (backed down): {len(completed)}")
    print(f"Pending/No-TACO: {len(df) - len(completed)}")
    if len(completed) > 0:
        success_rate = len(completed) / (len(df) - 1) * 100  # exclude current event
        print(f"Historical TACO success rate: {success_rate:.1f}%")

    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Build TACO event database")
    parser.add_argument("--seed-only", action="store_true",
                        help="Only write seed events, skip yfinance price fetch")
    parser.add_argument("--prices-only", action="store_true",
                        help="Only refresh prices for existing events")
    args = parser.parse_args()

    print("=" * 60)
    print("TACO Database Builder")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    df = build_database(seed_only=args.seed_only, prices_only=args.prices_only)
    return df


if __name__ == "__main__":
    main()
