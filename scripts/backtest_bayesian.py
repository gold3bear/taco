"""
scripts/backtest_bayesian.py — Bayesian Reversal Updater Backtest

Backtests the Bayesian Reversal Updater against historical TACO events.
Validates whether tracking signal trajectories improves prediction accuracy
vs static Five-Factor P₀.

Usage:
    python scripts/backtest_bayesian.py
    python scripts/backtest_bayesian.py --output reports/backtest_bayesian.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.statement import StatementType
from core.bayesian_updater import BayesianReversalUpdater, STATEMENT_TYPE_PRIORS


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"


# ── Historical Signal Sequences ────────────────────────────────────────────
# Manually reconstructed from event descriptions.
# Each event maps to: (statement_type, P₀, [signal_sequence], actual_outcome)
# outcome: 1 = TACO occurred, 0 = no TACO (war/escalation)

HISTORICAL_SIGNALS: dict[str, tuple] = {
    # TACO-001: Liberation Day → TACO in 7 days
    # Signals: initial threat → deadline extended → deal announced
    "TACO-001": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 2", "trump_extends_deadline"),        # 90-day pause announced
            ("Day 7", "trump_signals_deal_imminent"),   # Substantial progress
        ],
        1,  # TACO occurred
    ),

    # TACO-002: China 145% → Geneva deal → TACO in 11 days
    "TACO-002": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 3", "counterparty_hard_rejection"),    # China rejected terms
            ("Day 5", "trump_says_great_progress"),     # Geneva negotiations
            ("Day 11", "trump_signals_deal_imminent"),  # Deal confirmed
        ],
        1,
    ),

    # TACO-003: Canada Auto → TACO in 2 days (fastest)
    "TACO-003": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 1", "counterparty_symbolic_concession"),  # Industry lobbied
            ("Day 2", "trump_extends_deadline"),            # 1-month reprieve
        ],
        1,
    ),

    # TACO-004: Mexico 25% → TACO in 2 days
    "TACO-004": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 1", "counterparty_symbolic_concession"),   # Mexico pledged cooperation
            ("Day 2", "trump_extends_deadline"),            # Pause announced
        ],
        1,
    ),

    # TACO-005: TikTok → TACO
    "TACO-005": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 3", "trump_hedges_language"),              # Softened stance
            ("Day 7", "trump_signals_deal_imminent"),       # Deal framework
        ],
        1,
    ),

    # TACO-007: Panama Canal → Softened, no military action
    "TACO-007": (
        StatementType.TERRITORIAL,
        0.58,
        [
            ("Day 3", "trump_hedges_language"),
            ("Day 10", "ally_publicly_opposes_retreat"),    # NATO concerns
            ("Day 14", "trump_extends_deadline"),
        ],
        1,
    ),

    # TACO-008: Greenland → Dropped from agenda
    "TACO-008": (
        StatementType.TERRITORIAL,
        0.58,
        [
            ("Day 5", "ally_publicly_opposes_retreat"),     # Denmark/Greenland pushback
            ("Day 12", "trump_hedges_language"),            # No longer priority
        ],
        1,
    ),

    # TACO-009: EU Tariff → Partial deal
    "TACO-009": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 4", "third_party_mediator_enters"),       # Trade rep negotiations
            ("Day 8", "trump_says_great_progress"),
            ("Day 15", "trump_signals_deal_imminent"),
        ],
        1,
    ),

    # TACO-010: China 145% → Geneva deal
    "TACO-010": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 2", "trump_says_no_deal_possible"),      # Initial hardline
            ("Day 4", "counterparty_hard_rejection"),       # China refused
            ("Day 7", "third_party_mediator_enters"),      # US invited talks
            ("Day 12", "trump_says_great_progress"),       # Geneva meeting
        ],
        1,
    ),

    # TACO-012: Steel/Aluminum → Exemptions granted
    "TACO-012": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 3", "counterparty_symbolic_concession"),  # Industry exemption request
            ("Day 5", "trump_extends_deadline"),
        ],
        1,
    ),

    # TACO-013: Fed Powell → Explicit walkback
    "TACO-013": (
        StatementType.PERSONNEL,
        0.78,
        [
            ("Day 2", "trump_hedges_language"),             # Clarified comments
            ("Day 4", "trump_says_no_deal_possible"),      # Powell firing off table
        ],
        1,
    ),

    # TACO-014: Pharma → Delayed
    "TACO-014": (
        StatementType.TRADE_TARIFF,
        0.82,
        [
            ("Day 3", "back_channel_rumor"),
            ("Day 8", "trump_extends_deadline"),
        ],
        1,
    ),

    # TACO-015: Ukraine → Modified position
    "TACO-015": (
        StatementType.MILITARY,
        0.38,  # Military type → lower base
        [
            ("Day 5", "third_party_mediator_enters"),
            ("Day 10", "trump_hedges_language"),
        ],
        1,
    ),
}


# ── Anti-TACO Events (no reversal) ──────────────────────────────────────
# For completeness, we need at least some non-TACO cases.
# These are rare in the historical record (selection bias).

ANTI_TACO_EVENTS: dict[str, tuple] = {
    # No real anti-TACO events in our dataset yet — all 13 known events resolved as TACO.
    # This is the key limitation: backtest is on successful TACOs only.
    # In production, add events where Trump followed through on threat.
}


def run_backtest():
    """Run backtest on historical events."""
    results = []
    p0_predictions = []
    pt_predictions = []

    updater = BayesianReversalUpdater()

    print("Bayesian Reversal Updater Backtest")
    print("=" * 60)
    print(f"Events tested: {len(HISTORICAL_SIGNALS)}")
    print("")

    for event_id, (stmt_type, p0, signals, outcome) in HISTORICAL_SIGNALS.items():
        # Run Bayesian trajectory
        trajectory = updater.update_sequence(p0, signals)

        # Get final P_t
        p_t = trajectory[-1].posterior

        # Calculate where we would have been right
        # For trading: if P_t > threshold, predict TACO
        threshold = 0.50

        p0_pred = 1 if p0 >= threshold else 0
        pt_pred = 1 if p_t >= threshold else 0

        p0_correct = (p0_pred == outcome)
        pt_correct = (pt_pred == outcome)

        # Magnitude of error
        p0_error = abs(p0 - outcome)
        pt_error = abs(p_t - outcome)

        result = {
            "event_id": event_id,
            "statement_type": stmt_type.value,
            "p0_initial_prior": p0,
            "signals": [s[1] for s in signals],
            "p_t_final_posterior": p_t,
            "actual_outcome": outcome,
            "p0_prediction": p0_pred,
            "pt_prediction": pt_pred,
            "p0_correct": p0_correct,
            "pt_correct": pt_correct,
            "p0_error": round(p0_error, 3),
            "pt_error": round(pt_error, 3),
            "trajectory": [
                {
                    "time": r.time,
                    "signal": r.signal,
                    "posterior": r.posterior,
                    "delta": r.delta,
                }
                for r in trajectory
            ],
        }
        results.append(result)
        p0_predictions.append(p0_correct)
        pt_predictions.append(pt_correct)

    # Summary statistics
    p0_accuracy = sum(p0_predictions) / len(p0_predictions)
    pt_accuracy = sum(pt_predictions) / len(pt_predictions)
    avg_p0_error = sum(r["p0_error"] for r in results) / len(results)
    avg_pt_error = sum(r["pt_error"] for r in results) / len(results)

    # Mean Absolute Error
    mae_p0 = avg_p0_error
    mae_pt = avg_pt_error

    print(f"Overall Accuracy (threshold=50%):")
    print(f"  Five-Factor P₀:  {p0_accuracy:.1%}  ({sum(p0_predictions)}/{len(p0_predictions)} correct)")
    print(f"  Bayesian P_t:     {pt_accuracy:.1%}  ({sum(pt_predictions)}/{len(pt_predictions)} correct)")
    print(f"")
    print(f"Mean Absolute Error:")
    print(f"  Five-Factor P₀:  {mae_p0:.3f}")
    print(f"  Bayesian P_t:     {mae_pt:.3f}")
    print(f"")

    # By statement type
    by_type: dict = defaultdict(list)
    for r in results:
        by_type[r["statement_type"]].append(r)

    print("By Statement Type:")
    print("-" * 60)
    for stmt_type, type_results in sorted(by_type.items()):
        p0_acc = sum(1 for r in type_results if r["p0_correct"]) / len(type_results)
        pt_acc = sum(1 for r in type_results if r["pt_correct"]) / len(type_results)
        print(f"  {stmt_type:<20}: P₀ acc={p0_acc:.0%}, P_t acc={pt_acc:.0%}  (n={len(type_results)})")

    print("")
    print("Per-Event Detail:")
    print("-" * 60)
    for r in results:
        p0_marker = "✓" if r["p0_correct"] else "✗"
        pt_marker = "✓" if r["pt_correct"] else "✗"
        print(f"  {r['event_id']} ({r['statement_type']}): "
              f"P₀={r['p0_initial_prior']:.0%} {p0_marker} → "
              f"P_t={r['p_t_final_posterior']:.0%} {pt_marker}  "
              f"[{', '.join(r['signals'][:2])}]")

    return {
        "generated_at": datetime.now().isoformat(),
        "n_events": len(results),
        "p0_accuracy": round(p0_accuracy, 3),
        "pt_accuracy": round(pt_accuracy, 3),
        "mae_p0": round(mae_p0, 3),
        "mae_pt": round(mae_pt, 3),
        "events": results,
        "note": "Backtest on historical TACOs only. Anti-TACO events needed for complete calibration.",
    }


def main():
    parser = argparse.ArgumentParser(description="Bayesian Reversal Updater Backtest")
    parser.add_argument("--output", type=str, help="Output JSON file")
    args = parser.parse_args()

    report = run_backtest()

    if args.output:
        out_path = BASE_DIR / args.output
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved backtest results to {out_path}")


if __name__ == "__main__":
    main()
