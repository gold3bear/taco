"""
scripts/backtest_five_factor.py — Five-Factor Model Backtest Framework

Backtests the Five-Factor Model against historical TACO events.
Evaluates prediction accuracy, calibration, and category performance.

Usage:
    python scripts/backtest_five_factor.py
    python scripts/backtest_five_factor.py --by-category
    python scripts/backtest_five_factor.py --output reports/backtest_results.json
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.statement import StatementType
from models.five_factor import FiveFactorModel


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"


# Map event categories to StatementTypes
CATEGORY_TO_TYPE = {
    "trade_tariff": StatementType.TRADE_TARIFF,
    "military_geopolitical": StatementType.MILITARY,
    "geopolitical": StatementType.TERRITORIAL,
    "domestic_policy": StatementType.PERSONNEL,
    "tech_ban": StatementType.TRADE_TARIFF,
}

# Known outcomes (manually curated from data)
EVENT_OUTCOMES = {
    "TACO-001": 1,  # TACO occurred
    "TACO-002": 1,
    "TACO-003": 1,
    "TACO-004": 1,
    "TACO-005": 1,
    "TACO-007": 1,  # Panama Canal - softened rhetoric, no action
    "TACO-008": 1,  # Greenland - dropped from agenda
    "TACO-009": 1,  # EU Tariff - partial deal
    "TACO-010": 1,  # China 145% - Geneva deal
    "TACO-011": None,  # PENDING - current event
    "TACO-012": 1,  # Steel/Aluminum - exemptions granted
    "TACO-013": 1,  # Fed Powell - explicit walkback
    "TACO-014": 1,  # Pharma - delayed
    "TACO-015": 1,  # Ukraine - modified position
}

# Historical VIX estimates (approximate for backtest)
# Using reasonable estimates based on market conditions at the time
VIX_ESTIMATES = {
    "TACO-001": 28.0,  # Liberation Day - high volatility
    "TACO-002": 18.0,  # Geneva truce - moderate
    "TACO-003": 22.0,  # Auto tariffs - elevated
    "TACO-004": 18.0,  # Mexico - moderate
    "TACO-005": 15.0,  # TikTok - low impact
    "TACO-007": 14.0,  # Panama - low impact
    "TACO-008": 16.0,  # Greenland - moderate
    "TACO-009": 30.0,  # EU 2nd wave - elevated
    "TACO-010": 18.0,  # China re-escalation
    "TACO-011": None,  # Current - use market_snapshot
    "TACO-012": 17.0,  # Steel/Aluminum
    "TACO-013": 22.0,  # Fed threat - elevated
    "TACO-014": 19.0,  # Pharma tariffs
    "TACO-015": 16.0,  # Ukraine
}

# Counterparty signals (manually estimated)
COUNTERPARTY_SIGNALS = {
    "TACO-001": "symbolic_concession",  # 90-day pause
    "TACO-002": "counter_offer",  # Geneva deal
    "TACO-003": "symbolic_concession",  # Industry lobby
    "TACO-004": "symbolic_concession",  # Mexico cooperation pledge
    "TACO-005": "neutral",  # Extension
    "TACO-007": "third_party_mediator",  # Panama gave assurances
    "TACO-008": "neutral",  # Greenland/Denmark rejected but Trump dropped without concession (unrealistic goal)
    "TACO-009": "counter_offer",  # EU negotiated
    "TACO-010": "counter_offer",  # Geneva deal
    "TACO-011": "survival_stakes",  # Iran - IRGC
    "TACO-012": "symbolic_concession",  # Exemptions granted
    "TACO-013": "neutral",  # Walkback
    "TACO-014": "counter_offer",  # Industry lobby
    "TACO-015": "hard_rejection",  # Ukraine/Europe resisted
}


def load_events() -> list[dict]:
    """Load TACO events from CSV."""
    events = []
    path = DATA_DIR / "taco_events.csv"

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(row)

    return events


def calculate_predicted_prob(
    category: str,
    vix: float,
    counterparty_signal: str,
    gas_price: float = 3.50,
) -> dict:
    """Calculate Five-Factor predicted probability for an event."""
    model = FiveFactorModel()

    statement_type = CATEGORY_TO_TYPE.get(category, StatementType.TRADE_TARIFF)

    result = model.calculate(
        statement_type=statement_type,
        vix_current=vix,
        counterparty_signal=counterparty_signal,
        gas_price=gas_price,
        midterm_months=18,  # Assume mid-term > 6 months
        market_drawdown=0.0,
        polymarket_prob=None,
        nth_similar_threat=1,
        base_return=None,
    )

    return result.to_dict()


def calculate_metrics(predictions: list[dict], actuals: list[int]) -> dict:
    """Calculate various accuracy metrics."""
    n = len(predictions)

    if n == 0:
        return {}

    # Basic accuracy
    correct = sum(1 for p, a in zip(predictions, actuals) if (p >= 0.5) == (a == 1))
    accuracy = correct / n

    # Brier Score (mean squared error)
    brier = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / n

    # Calibration: group predictions into bins
    bins = {
        "0-20%": [],
        "20-40%": [],
        "40-60%": [],
        "60-80%": [],
        "80-100%": [],
    }
    for p, a in zip(predictions, actuals):
        if p < 0.2:
            bins["0-20%"].append(a)
        elif p < 0.4:
            bins["20-40%"].append(a)
        elif p < 0.6:
            bins["40-60%"].append(a)
        elif p < 0.8:
            bins["60-80%"].append(a)
        else:
            bins["80-100%"].append(a)

    calibration = {}
    for bin_name, outcomes in bins.items():
        if outcomes:
            calibration[bin_name] = {
                "count": len(outcomes),
                "mean_predicted": sum(
                    [p for p, a in zip(predictions, actuals) if get_bin(p) == bin_name]
                ) / len(outcomes),
                "actual_rate": sum(outcomes) / len(outcomes),
            }

    return {
        "accuracy": accuracy,
        "brier_score": brier,
        "calibration": calibration,
        "total_events": n,
        "taco_rate_actual": sum(actuals) / n,
        "taco_rate_predicted": sum(predictions) / n,
    }


def get_bin(p: float) -> str:
    """Get calibration bin for a probability."""
    if p < 0.2:
        return "0-20%"
    elif p < 0.4:
        return "20-40%"
    elif p < 0.6:
        return "40-60%"
    elif p < 0.8:
        return "60-80%"
    else:
        return "80-100%"


def backtest(by_category: bool = False) -> dict:
    """Run backtest on all completed TACO events."""
    events = load_events()

    model = FiveFactorModel()
    results = []

    for event in events:
        event_id = event["event_id"]
        category = event["category"]

        # Skip pending events
        if event_id not in EVENT_OUTCOMES or EVENT_OUTCOMES[event_id] is None:
            print(f"  Skipping {event_id}: PENDING")
            continue

        actual = EVENT_OUTCOMES[event_id]
        vix = VIX_ESTIMATES.get(event_id, 18.0)
        counterparty = COUNTERPARTY_SIGNALS.get(event_id, "neutral")

        if vix is None:
            print(f"  Skipping {event_id}: No VIX estimate")
            continue

        # Calculate prediction
        prediction = calculate_predicted_prob(
            category=category,
            vix=vix,
            counterparty_signal=counterparty,
        )

        predicted_prob = prediction["probability"]

        results.append({
            "event_id": event_id,
            "category": category,
            "actual": actual,
            "predicted": predicted_prob,
            "vix": vix,
            "counterparty": counterparty,
            "statement_type": CATEGORY_TO_TYPE.get(category, StatementType.TRADE_TARIFF).value,
        })

        print(
            f"  {event_id}: pred={predicted_prob:.1%}, "
            f"actual={'TACO' if actual else 'No TACO'}, "
            f"type={CATEGORY_TO_TYPE.get(category, '?').value}"
        )

    # Calculate overall metrics
    predictions = [r["predicted"] for r in results]
    actuals = [r["actual"] for r in results]

    metrics = calculate_metrics(predictions, actuals)

    # Category breakdown
    if by_category:
        category_results = defaultdict(lambda: {"predictions": [], "actuals": []})
        for r in results:
            cat = r["category"]
            category_results[cat]["predictions"].append(r["predicted"])
            category_results[cat]["actuals"].append(r["actual"])

        category_metrics = {}
        for cat, data in category_results.items():
            if data["predictions"]:
                category_metrics[cat] = calculate_metrics(
                    data["predictions"], data["actuals"]
                )

        metrics["by_category"] = category_metrics

    return {
        "results": results,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }


def print_report(results: dict, by_category: bool = False):
    """Print human-readable backtest report."""
    metrics = results["metrics"]

    print("\n" + "=" * 60)
    print("FIVE-FACTOR MODEL BACKTEST RESULTS")
    print("=" * 60)

    print(f"\nOverall Metrics:")
    print(f"  Total Events: {metrics['total_events']}")
    print(f"  Accuracy: {metrics['accuracy']:.1%}")
    print(f"  Brier Score: {metrics['brier_score']:.4f} (lower is better)")
    print(f"  Actual TACO Rate: {metrics['taco_rate_actual']:.1%}")
    print(f"  Predicted TACO Rate: {metrics['taco_rate_predicted']:.1%}")

    print(f"\nCalibration:")
    print(f"  {'Bin':<12} {'Count':>6} {'Avg Pred':>10} {'Actual':>10} {'Diff':>10}")
    print(f"  {'-'*12} {'-'*6} {'-'*10} {'-'*10} {'-'*10}")

    calibration = metrics.get("calibration", {})
    for bin_name in ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]:
        if bin_name in calibration:
            c = calibration[bin_name]
            diff = c["actual_rate"] - c["mean_predicted"]
            print(
                f"  {bin_name:<12} {c['count']:>6} "
                f"{c['mean_predicted']:>10.1%} {c['actual_rate']:>10.1%} "
                f"{diff:>+10.1%}"
            )

    if by_category and "by_category" in metrics:
        print(f"\nBy Category:")
        for cat, cat_metrics in metrics["by_category"].items():
            if cat_metrics:
                print(
                    f"  {cat:<20} n={cat_metrics['total_events']} "
                    f"acc={cat_metrics['accuracy']:.1%} "
                    f"brier={cat_metrics['brier_score']:.4f}"
                )

    # Event-level results
    print(f"\nEvent-Level Results:")
    print(f"  {'Event ID':<10} {'Type':<15} {'Predicted':>10} {'Actual':>10} {'Correct':>8}")
    print(f"  {'-'*10} {'-'*15} {'-'*10} {'-'*10} {'-'*8}")

    for r in results["results"]:
        correct = "✓" if (r["predicted"] >= 0.5) == (r["actual"] == 1) else "✗"
        print(
            f"  {r['event_id']:<10} {r['statement_type']:<15} "
            f"{r['predicted']:>10.1%} {r['actual']:>10.0f} {correct:>8}"
        )

    # Key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    metrics_summary = metrics

    if metrics_summary["brier_score"] < 0.15:
        brier_verdict = "GOOD"
    elif metrics_summary["brier_score"] < 0.25:
        brier_verdict = "FAIR"
    else:
        brier_verdict = "POOR"

    print(f"\n1. Overall Calibration: {brier_verdict}")
    print(f"   Brier Score {metrics_summary['brier_score']:.4f} indicates ", end="")
    if metrics_summary["brier_score"] < 0.15:
        print("good probability calibration.")
    elif metrics_summary["brier_score"] < 0.25:
        print("moderate calibration error.")
    else:
        print("significant calibration issues.")

    # Category analysis
    if by_category and "by_category" in metrics:
        print(f"\n2. Category Performance:")
        for cat, cat_metrics in metrics["by_category"].items():
            if cat_metrics:
                acc = cat_metrics["accuracy"]
                if acc >= 0.80:
                    verdict = "GOOD"
                elif acc >= 0.60:
                    verdict = "FAIR"
                else:
                    verdict = "POOR"
                print(f"   - {cat}: {verdict} ({acc:.0%} accuracy)")


def main():
    parser = argparse.ArgumentParser(description="Backtest Five-Factor Model")
    parser.add_argument("--by-category", action="store_true", help="Show category breakdown")
    parser.add_argument("--output", type=str, help="Output JSON file")

    args = parser.parse_args()

    print("Running Five-Factor Model Backtest...")
    print("=" * 60)

    results = backtest(by_category=args.by_category)

    print_report(results, by_category=args.by_category)

    if args.output:
        output_path = BASE_DIR / args.output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()
