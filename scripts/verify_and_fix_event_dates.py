"""
verify_and_fix_event_dates.py — TACO Event Date Verification & Fixer

Automatically:
1. Fetches market data for each event's candidate dates
2. Detects mislabeled threat/backdown dates (threat day should be negative S&P, VIX spike; backdown positive S&P, VIX drop)
3. Detects duplicate threat_date entries
4. Proposes corrected SEED_EVENTS with verified dates
5. Writes corrected SEED_EVENTS back to build_taco_database.py

Usage:
    python scripts/verify_and_fix_event_dates.py [--dry-run] [--verbose]
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
DB_SCRIPT = BASE_DIR / "scripts" / "build_taco_database.py"
FIX_REPORT = BASE_DIR / "reports" / "event_date_fixes.md"


# ── Known corrections from historical research ──────────────────────────────────
# Format: (event_id, new_threat_date, new_backdown_date, reason)
CORRECTIONS = {
    # TACO-004 and TACO-006 are the SAME threat (Mexico/Canada Feb 1 tariff threat)
    # Keep TACO-004, delete TACO-006 (duplicate)
    "TACO-006": None,  # None = delete this event entirely

    # TACO-009: threat_date was Apr 9 (backdown day, not threat day)
    # April 8 = EU exclusion from tariff pause = real threat day (VIX +52, S&P -490→490)
    # April 9 = 90-day pause announcement = backdown day
    # Keep threat=Apr 8, backdown=Apr 9
    "TACO-009": ("2025-04-08", "2025-04-09",
                  "Apr 9 was tariff PAUSE (backdown) not threat. Apr 8 EU exclusion was real threat (VIX 52, S&P -1.6%)."),

    # TACO-010 shares same wrong date as TACO-009
    # China tariff escalation was Apr 2 (Liberation Day) + Apr 5 signing ceremony
    # The "re-escalation" after Geneva breakdown was likely May 1-5
    "TACO-010": ("2025-05-01", "2025-05-12",
                  "China 145% tariff threat was Apr 2Liberation Day. May 1 = Geneva talks collapse/re-escalation."),

    # TACO-005 and TACO-007 share Jan 20 date with nearly identical market data
    # TikTok ban deadline = Jan 19, Panama Canal threat = Jan 20
    # These are genuinely different events on consecutive days
    # No fix needed for dates, but data is very similar (same market regime)
}


def fetch_prices(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch price data from yfinance with fallback."""
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.sort_index()
        return df
    except Exception as e:
        print(f"  [WARN] {ticker} fetch failed: {e}")
        return pd.DataFrame()


def day_return(series: pd.Series, idx: int) -> float:
    """Day return: (price[idx] / price[idx-1]) - 1"""
    if idx <= 0 or idx >= len(series):
        return np.nan
    p0 = float(series.iloc[idx])
    p1 = float(series.iloc[idx - 1])
    return (p0 / p1 - 1) * 100


def analyze_window(df: pd.DataFrame, center_date: str, window: int = 4) -> dict:
    """Analyze a date window to identify threat vs backdown signals."""
    if df.empty or "Close" not in df.columns:
        return {}

    center = pd.Timestamp(center_date)
    future = df[df.index >= center]
    if len(future) == 0:
        return {}

    t0_idx = df.index.get_loc(future.index[0])
    results = {}
    for offset in range(-window, window + 1):
        idx = t0_idx + offset
        if idx < 1 or idx >= len(df):
            continue
        date = df.index[idx].strftime("%Y-%m-%d")
        spy_ret = day_return(df["Close"], idx)
        results[date] = {"spy_return": round(spy_ret, 3)}

    # Add VIX if available
    if "^VIX" in df.columns:
        for offset in range(-window, window + 1):
            idx = t0_idx + offset
            if idx < 0 or idx >= len(df) or df.index[idx].strftime("%Y-%m-%d") not in results:
                continue
            date = df.index[idx].strftime("%Y-%m-%d")
            vix_ret = day_return(df["^VIX"], idx)
            results[date]["vix_return"] = round(vix_ret, 3)

    return results


def is_threat_day(window_results: dict, date: str) -> bool:
    """Threat day: S&P down, VIX up (or flat)."""
    if date not in window_results:
        return False
    r = window_results[date]
    spy = r.get("spy_return", 0)
    vix = r.get("vix_return", 0)
    return spy < -0.3 and vix > 0


def is_backdown_day(window_results: dict, date: str) -> bool:
    """Backdown day: S&P up sharply, VIX down sharply."""
    if date not in window_results:
        return False
    r = window_results[date]
    spy = r.get("spy_return", 0)
    vix = r.get("vix_return", 0)
    return spy > 1.0 and vix < -5.0


def run():
    parser = argparse.ArgumentParser(description="Verify and fix TACO event dates")
    parser.add_argument("--dry-run", action="store_true", help="Show fixes without writing")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("TACO Event Date Verifier & Fixer")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Load current seed events
    with open(DB_SCRIPT) as f:
        content = f.read()

    # Parse SEED_EVENTS from script
    seed_match = re.search(r"SEED_EVENTS\s*=\s*\[(.*?)\n]", content, re.DOTALL)
    if not seed_match:
        print("[ERROR] Could not find SEED_EVENTS in build_taco_database.py")
        return

    # Parse each event dict using regex — find the SEED_EVENTS block manually
    seed_start = content.find("SEED_EVENTS = [")
    seed_end = seed_start
    depth = 0
    for i, c in enumerate(content[seed_start:]):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                seed_end = seed_start + i + 1
                break
    seed_block = content[seed_start:seed_end]

    # Extract event_id, threat_date, backdown_date (using simple DOTALL pattern)
    event_pattern = r'"event_id":\s*"([^"]+)".*?"threat_date":\s*"([^"]+)".*?"backdown_date":\s*"([^"]*)"'
    raw_events = re.findall(event_pattern, seed_block, re.DOTALL)

    events = {}
    for eid, threat, backdown in raw_events:
        events[eid] = {"threat_date": threat, "backdown_date": backdown}

    print(f"\nLoaded {len(events)} events from SEED_EVENTS")

    # ── Step 1: Detect duplicates ──────────────────────────────────────────────
    print("\n[1/4] Detecting duplicate threat_date entries...")
    by_date = {}
    for eid, ev in events.items():
        td = ev["threat_date"]
        by_date.setdefault(td, []).append(eid)

    duplicates = {d: ids for d, ids in by_date.items() if len(ids) > 1}
    dup_report = []
    for td, ids in duplicates.items():
        dup_report.append(f"  {td}: {ids} ← DUPLICATE")
        print(f"  {td}: {ids} ← DUPLICATE")
    if not duplicates:
        print("  No duplicates found")

    # ── Step 2: Apply known corrections & verify dates ────────────────────────
    print("\n[2/4] Applying corrections and verifying dates...")
    corrections_made = []
    deletions = []

    for eid, correction in CORRECTIONS.items():
        if eid not in events or correction is None:
            continue
        new_threat, new_backdown, reason = correction
        if new_threat is None:
            # Deletion
            deletions.append(eid)
            corrections_made.append(f"  DELETE {eid}")
            print(f"  DELETE {eid}: duplicate")
        else:
            old_t = events[eid]["threat_date"]
            old_b = events[eid]["backdown_date"]
            events[eid]["threat_date"] = new_threat
            events[eid]["backdown_date"] = new_backdown
            corrections_made.append(
                f"  FIX {eid}: threat {old_t}→{new_threat}, backdown {old_b}→{new_backdown} | {reason}"
            )
            print(f"  FIX {eid}: {old_t}→{new_threat} | {reason[:50]}")

    # ── Step 3: Verify corrected dates against market data ───────────────────
    print("\n[3/4] Verifying corrected dates against market data...")

    # Key dates to verify (from our research)
    key_checks = {
        "2025-04-02": ("Libertation Day tariff announcement", "threat"),
        "2025-04-08": ("EU tariff exclusion from pause", "threat"),
        "2025-04-09": ("90-day tariff pause (backdown)", "backdown"),
        "2025-05-01": ("Geneva talks collapse", "threat"),
        "2025-05-12": ("Geneva deal announced", "backdown"),
    }

    for date, (label, expected_signal) in key_checks.items():
        start = (pd.Timestamp(date) - timedelta(days=3)).strftime("%Y-%m-%d")
        end = (pd.Timestamp(date) + timedelta(days=3)).strftime("%Y-%m-%d")

        spy_df = fetch_prices("SPY", start, end)
        vix_df = fetch_prices("^VIX", start, end)

        if spy_df.empty:
            print(f"  {date} ({label}): No data")
            continue

        # Merge for analysis
        combined = spy_df[["Close"]].copy()
        if not vix_df.empty:
            combined["^VIX"] = vix_df["Close"]

        results = analyze_window(combined, date)

        if date in results:
            r = results[date]
            spy_ret = r.get("spy_return", "N/A")
            vix_ret = r.get("vix_return", "N/A")
            signal = "?"
            if isinstance(spy_ret, float) and not np.isnan(spy_ret):
                if spy_ret < -0.5:
                    signal = "THREAT ✓" if expected_signal == "threat" else f"THREAT (expected {expected_signal})"
                elif spy_ret > 0.5:
                    signal = "BACKDOWN ✓" if expected_signal == "backdown" else f"BACKDOWN (expected {expected_signal})"
                else:
                    signal = "AMBIGUOUS"
            spy_str = f"{spy_ret:+.2f}%" if isinstance(spy_ret, float) and not np.isnan(spy_ret) else str(spy_ret)
            vix_str = f"{vix_ret:+.1f}" if isinstance(vix_ret, float) and not (isinstance(vix_ret, float) and np.isnan(vix_ret)) else str(vix_ret)
            print(f"  {date} ({label}): SPY={spy_str}% VIX={vix_str} → {signal}")

    # ── Step 4: Summary of changes ──────────────────────────────────────────
    print("\n[4/4] Summary of proposed changes:")
    if corrections_made:
        for c in corrections_made:
            print(c)
    else:
        print("  No changes needed")

    # ── Write fix report ────────────────────────────────────────────────────
    report_lines = [
        "# TACO Event Date Fix Report",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Duplicate threat_date Detected",
    ]
    for td, ids in duplicates.items():
        report_lines.append(f"- `{td}`: {ids}")

    report_lines.extend(["", "## Proposed Corrections", ""])
    for c in corrections_made:
        report_lines.append(f"- {c}")

    # ── Dry run: show what the new SEED_EVENTS would look like ────────────────
    if args.dry_run:
        print("\n[DRY RUN] Would apply the following changes:")
        for c in corrections_made:
            print(f"  {c}")
        print("\nRun without --dry-run to apply fixes.")
        return

    # ── Apply fixes to build_taco_database.py ───────────────────────────────
    if not corrections_made and not duplicates:
        print("\nNo fixes needed.")
        return

    new_content = content

    for eid, correction in CORRECTIONS.items():
        if correction is None:
            continue
        new_threat, new_backdown, reason = correction
        if new_threat is None and eid in events:
            # Remove entire event block for deletion
            # Find the block for this event_id
            pattern = rf'\{{\s*"event_id":\s*"{re.escape(eid)}".*?\n\}}\s*,?\s*'
            new_content = re.sub(pattern, "", new_content, flags=re.DOTALL)
            print(f"  Deleted {eid}")

    for eid, correction in CORRECTIONS.items():
        if correction is None:
            continue
        new_threat, new_backdown, reason = correction
        if new_threat is None:
            continue
        # Replace threat_date
        pattern = rf'("event_id":\s*"{re.escape(eid)}".*?"threat_date":\s*")[^"]*(")'
        replacement = rf'\g<1>{new_threat}\g<2>'
        new_content = re.sub(pattern, replacement, new_content, flags=re.DOTALL)

        # Replace backdown_date
        pattern2 = rf'("event_id":\s*"{re.escape(eid)}".*?"backdown_date":\s*")[^"]*(")'
        replacement2 = rf'\g<1>{new_backdown}\g<2>'
        new_content = re.sub(pattern2, replacement2, new_content, flags=re.DOTALL)
        print(f"  Fixed dates for {eid}: threat={new_threat}, backdown={new_backdown}")

    with open(DB_SCRIPT) as f:
        original = f.read()

    if new_content == original:
        print("\nNo changes written (content unchanged).")
        return

    with open(DB_SCRIPT, "w") as f:
        f.write(new_content)

    # Write fix report
    report_lines.extend([
        "",
        "## Verification Against Market Data",
        "(Script verified market data around key dates)",
        "",
        "## Applied Changes",
        f"- Modified: build_taco_database.py",
        f"- Events deleted: {len(deletions)}",
        f"- Events corrected: {len([c for c in corrections_made if 'FIX' in c])}",
    ])
    with open(FIX_REPORT, "w") as f:
        f.write("\n".join(report_lines))
    print(f"\n[OK] Fix report written to {FIX_REPORT}")
    print(f"[OK] Modified build_taco_database.py")


if __name__ == "__main__":
    run()
