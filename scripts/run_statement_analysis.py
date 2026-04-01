"""
scripts/run_statement_analysis.py — Statement-Driven TACO Analysis

Main analysis pipeline for the statement-driven TACO architecture.
Runs the 5-agent analysis on a statement and generates trade recommendations.

Usage:
    python scripts/run_statement_analysis.py --statement-id TACO-011
    python scripts/run_statement_analysis.py --batch  # analyze all active statements
    python scripts/run_statement_analysis.py --statement "Trump threatens Iran"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.statement import (
    Statement, StatementType, RhetoricIntensity, StatementStatus,
    TYPE_ASSET_MAP, BASE_REVERSAL_RATES
)
from models.five_factor import FiveFactorModel
from models.position_calculator import TwoPhasePositionCalculator
from core.bayesian_updater import BayesianReversalUpdater, get_initial_prior


BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"


def load_statements() -> list[Statement]:
    """Load statements from statements.json."""
    path = DATA_DIR / "statements.json"
    if not path.exists():
        raise FileNotFoundError(f"statements.json not found at {path}. Run migrate_events.py first.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Statement.from_dict(s) for s in data]


def load_market_context() -> dict:
    """Load current market context from market_snapshot.json."""
    path = DATA_DIR / "market_snapshot.json"
    if not path.exists():
        # Return defaults if file doesn't exist
        return {
            "vix": 20.0,
            "sp500": 5000.0,
            "oil_price": 85.0,
            "gas_price": 3.50,
            "midterm_months": 18,
            "market_drawdown": 0.0,
        }

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract VIX from assets structure (NEW-004 fix)
    vix = 20.0
    if "assets" in data and "^VIX" in data["assets"]:
        vix = data["assets"]["^VIX"].get("current_price", 20.0)

    # Extract S&P500 from assets
    sp500 = 5000.0
    if "assets" in data and "SPY" in data["assets"]:
        sp500 = data["assets"]["SPY"].get("current_price", 5000.0)

    return {
        "vix": vix,
        "sp500": sp500,
        "oil_price": data.get("oil_price", 85.0),
        "gas_price": data.get("gas_price", 3.50),
        "midterm_months": data.get("midterm_months", 18),
        "market_drawdown": data.get("market_drawdown", 0.0),
    }


def load_polymarket() -> Optional[dict]:
    """Load Polymarket data if available."""
    path = DATA_DIR / "polymarket_geopolitics.json"
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_market_reaction_estimate(statement: Statement) -> float:
    """Get estimated S&P return for statement type."""
    TYPE_REACTIONS = {
        StatementType.TRADE_TARIFF: -2.1,
        StatementType.MILITARY: -1.8,
        StatementType.TERRITORIAL: -0.5,
        StatementType.PERSONNEL: -0.8,
        StatementType.POLICY: -0.5,
        StatementType.SANCTIONS: -1.2,
        StatementType.DIPLOMATIC: -0.4,
    }
    return TYPE_REACTIONS.get(statement.statement_type, -1.0)


def run_five_factor_analysis(
    statement: Statement,
    market_context: dict,
    polymarket_data: Optional[dict] = None,
) -> dict:
    """Run Five-Factor Model analysis on a statement."""
    model = FiveFactorModel()

    # Extract polymarket probability if available
    # IMPORTANT: FiveFactorModel expects BACKDOWN probability, not war probability
    polymarket_prob = None
    if polymarket_data:
        entity = statement.target_entity.lower()
        if entity == "iran" and "iran_war_prob" in polymarket_data:
            # Convert war_prob to backdown_prob
            war_prob = polymarket_data.get("iran_war_prob", 0.925)
            polymarket_prob = 1.0 - war_prob
        elif "trump_backdown_prob" in polymarket_data:
            polymarket_prob = polymarket_data.get("trump_backdown_prob")
        elif "iran_war_prob" in polymarket_data:
            war_prob = polymarket_data.get("iran_war_prob", 0.5)
            polymarket_prob = 1.0 - war_prob

    # Get base return for desensitization
    base_return = get_market_reaction_estimate(statement)

    # Determine counterparty signal based on target entity
    # Iran is controlled by IRGC with survival stakes - cannot accept face-saving exit
    counterparty_signal = market_context.get("counterparty_signal", "neutral")
    if statement.target_entity.lower() == "iran":
        counterparty_signal = "survival_stakes"

    # Run model
    result = model.calculate(
        statement_type=statement.statement_type,
        vix_current=market_context.get("vix", 20.0),
        counterparty_signal=counterparty_signal,
        gas_price=market_context.get("gas_price", 3.50),
        midterm_months=market_context.get("midterm_months", 18),
        market_drawdown=market_context.get("market_drawdown", 0.0),
        polymarket_prob=polymarket_prob,
        nth_similar_threat=statement.nth_similar_threat,
        base_return=base_return,
    )

    return result.to_dict()


def run_bayesian_analysis(
    statement: Statement,
    five_factor_probability: float,
    market_context: dict,
    signals: Optional[list[tuple[str, str]]] = None,
) -> dict:
    """
    Run Bayesian Reversal Updater on top of Five-Factor P₀.

    Architecture:
        Five-Factor Model → P₀ (initial prior, static)
        Bayesian Updater  → P_t (posterior, updated with signals)

    Args:
        statement: Statement being analyzed
        five_factor_probability: P₀ from Five-Factor Model
        market_context: Market context (oil_price, gas_price)
        signals: Optional list of (timestamp, signal_name) tuples

    Returns:
        dict with P₀, P_t, trajectory, and calibration check
    """
    updater = BayesianReversalUpdater()

    # Build context for LR modifiers
    context = {
        "oil_price": market_context.get("oil_price", 0),
        "gas_price": market_context.get("gas_price", 0),
    }

    # Use statement type prior as P₀ baseline, then apply Five-Factor adjustments
    # Five-Factor probability is already the refined P₀
    initial_prior = five_factor_probability

    # Default monitoring signals if none provided
    if signals is None:
        signals = [
            ("Day 3", "trump_extends_deadline"),
            ("Day 5", "counterparty_hard_rejection"),
        ]

    # Run Bayesian trajectory
    trajectory = updater.update_sequence(initial_prior, signals, context=context)

    # Polymarket calibration check
    pm_data = market_context.get("polymarket_data", {})
    polymarket_backdown = pm_data.get("trump_backdown_prob") or pm_data.get("polymarket_trump_backdown_prob")
    polymarket_calibration_signal = None
    if polymarket_backdown is not None:
        polymarket_calibration_signal = updater.check_polymarket_calibration(
            initial_prior, polymarket_backdown
        )

    # Get current posterior (last entry in trajectory)
    current_posterior = trajectory[-1].posterior if trajectory else initial_prior

    return {
        "p0_initial_prior": initial_prior,
        "p_t_current_posterior": current_posterior,
        "trajectory": [
            {
                "time": r.time,
                "signal": r.signal,
                "prior": r.prior,
                "posterior": r.posterior,
                "delta_pp": round(r.delta * 100, 1),
                "lr_applied": r.lr_applied,
                "context_adjusted": r.context_adjusted,
            }
            for r in trajectory
        ],
        "polymarket_calibration": (
            {"signal": polymarket_calibration_signal[0], "lr": polymarket_calibration_signal[1]}
            if polymarket_calibration_signal else None
        ),
        "bayesian_formatted": updater.format_trajectory(
            trajectory, statement.statement_type.value
        ),
    }


def run_two_phase_analysis(
    statement: Statement,
    reversal_probability: float,
    market_context: dict,
) -> dict:
    """Run two-phase trading analysis."""
    calculator = TwoPhasePositionCalculator()

    # Get predicted return
    predicted_return = get_market_reaction_estimate(statement)

    # Apply desensitization
    desensitized_return = predicted_return * (0.85 ** (statement.nth_similar_threat - 1))

    result = calculator.calculate_two_phase(
        statement_type=statement.statement_type,
        predicted_return=desensitized_return,
        reversal_probability=reversal_probability,
        vix_current=market_context.get("vix", 20.0),
    )

    return {
        "phase1": result.phase1.__dict__ if result.phase1 else None,
        "phase2": result.phase2.__dict__ if result.phase2 else None,
        "total_max_exposure": result.total_max_exposure,
        "reasoning": result.reasoning,
    }


def analyze_statement(
    statement: Statement,
    market_context: dict,
    polymarket_data: Optional[dict] = None,
    signals: Optional[list[tuple[str, str]]] = None,
) -> dict:
    """Run complete 5-agent analysis on a single statement."""

    # Get base return estimate
    predicted_return = get_market_reaction_estimate(statement)
    desensitized_return = predicted_return * (0.85 ** (statement.nth_similar_threat - 1))

    # Five-Factor reversal probability
    five_factor = run_five_factor_analysis(statement, market_context, polymarket_data)

    # Add boost_pp to five_factor for report generation
    f2_value = five_factor["factors"]["factor_2_market_pain"]["value"]
    five_factor["factors"]["factor_2_market_pain"]["boost_pp"] = round(0.25 * f2_value, 1)

    # Two-phase trading
    two_phase = run_two_phase_analysis(
        statement,
        five_factor["probability"],
        market_context,
    )

    # Bayesian Reversal Updater (new architecture)
    # Five-Factor P₀ → Bayesian → P_t (real-time posterior)
    market_context_with_pm = dict(market_context)
    market_context_with_pm["polymarket_data"] = polymarket_data or {}

    bayesian = run_bayesian_analysis(
        statement,
        five_factor["probability"],
        market_context_with_pm,
        signals=signals,
    )

    return {
        "statement_id": statement.id,
        "statement_summary": {
            "type": statement.statement_type.value,
            "intensity": statement.rhetoric_intensity.value,
            "target": statement.target_entity,
            "has_deadline": statement.has_deadline,
            "deadline_date": statement.deadline_date.isoformat() if statement.deadline_date else None,
            "nth_similar": statement.nth_similar_threat,
            "status": statement.status.value,
        },
        "five_factor": five_factor,
        "bayesian_updater": bayesian,
        "two_phase_trading": two_phase,
        "market_context": market_context,
        "analyzed_at": datetime.now().isoformat(),
    }


def generate_report(analysis: dict) -> str:
    """Generate human-readable analysis report."""

    summary = analysis["statement_summary"]
    ff = analysis["five_factor"]
    tp = analysis["two_phase_trading"]
    mc = analysis.get("market_context", {})
    bayesian = analysis.get("bayesian_updater", {})

    # Determine TACO verdict — use Bayesian posterior if available, else Five-Factor
    prob = bayesian.get("p_t_current_posterior", ff["probability"])
    if prob >= 0.70:
        verdict = "HIGH TACO PROBABILITY"
        color = "🟢"
    elif prob >= 0.40:
        verdict = "MODERATE TACO PROBABILITY"
        color = "🟡"
    else:
        verdict = "LOW TACO PROBABILITY"
        color = "🔴"

    p0 = bayesian.get("p0_initial_prior", ff["probability"])

    report = f"""
# TACO Statement Analysis: {analysis['statement_id']}

## Statement Summary
- **Type:** {summary['type']}
- **Intensity:** {summary['intensity']}
- **Target:** {summary['target']}
- **Deadline:** {"Yes" if summary['has_deadline'] else "No"} {f"({summary['deadline_date']})" if summary['deadline_date'] else ""}
- **Similar Threat #:** {summary['nth_similar']}
- **Status:** {summary['status']}

## {verdict} {color}

**> Reversal Probability (P_t): {prob:.1%}**  ← Bayesian posterior
*(Five-Factor P₀: {p0:.1%} | delta: {(prob - p0) * 100:+.1f}pp)*

### Five-Factor Breakdown

| Factor | Value | Contribution |
|--------|-------|--------------|
| Base Rate ({summary['type']}) | {ff['factors']['factor_1_base_rate']['value']:.0%} | {ff['factors']['factor_1_base_rate']['value']:.0%} |
| Market Pain (VIX={mc.get('vix', 'N/A')}) | {ff['factors']['factor_2_market_pain']['value']:.1f} | +{ff['factors']['factor_2_market_pain']['boost_pp']:.0f}pp |
| Counterparty Signal | {ff['factors']['factor_3_counterparty']['value']:+.0f} | {ff['factors']['factor_3_counterparty']['value']*100:.0f}pp |
| Domestic Pressure | {ff['factors']['factor_4_domestic']['value']:+.0f} | {ff['factors']['factor_4_domestic']['value']*100:.0f}pp |
| Polymarket Calibration | {ff['factors']['factor_5_polymarket']['value']:+.2f} | {ff['factors']['factor_5_polymarket']['value']*100:.1f}pp |

**Confidence:** {ff['confidence']:.0%}

### Bayesian Reversal Trajectory (New Architecture)

| Time | Signal | Posterior | Delta | LR |
|------|--------|-----------|-------|----|
"""

    # Add trajectory rows
    for entry in bayesian.get("trajectory", []):
        arrow = "↑" if entry["delta_pp"] >= 0 else "↓"
        ctx = " *" if entry["context_adjusted"] else ""
        report += f"| {entry['time']} | {entry['signal']} | {entry['posterior']*100:.1f}% | {arrow}{abs(entry['delta_pp']):.1f}pp | {entry['lr_applied']:.2f}{ctx} |\n"

    # Polymarket calibration note
    pm_cal = bayesian.get("polymarket_calibration")
    if pm_cal:
        report += f"\n**Polymarket divergence signal:** {pm_cal['signal']} (LR={pm_cal['lr']:.2f})\n"

    report += f"""
### Time Decay Forecast (Five-Factor P₀ baseline)

| Day | Probability |
|-----|-------------|
| 3 | {ff['probability'] * 1.02:.0%} (estimated) |
| 7 | {ff['probability'] * 1.05:.0%} (estimated peak) |
| 14 | {ff['probability'] * 0.95:.0%} (estimated) |
| 30 | {ff['probability'] * 0.80:.0%} (estimated) |
| 60 | {ff['probability'] * 0.50:.0%} (estimated) |

## Two-Phase Trading Recommendation

### Phase 1: Initial Reaction
"""
    if tp["phase1"]:
        p1 = tp["phase1"]
        report += f"""
| Element | Value |
|---------|-------|
| Direction | {p1['direction']} {p1['asset']} |
| Size | {p1['size_pct']}% |
| Entry | {p1['entry_trigger']} |
| Hold | {p1['hold_days_min']}-{p1['hold_days_max']} days |
| Exit | {p1['exit_trigger']} |
| Expected Return | {p1['expected_return']:.1f}% |
"""
    else:
        report += "No Phase 1 trade recommended\n"

    report += "\n### Phase 2: Reversal Trade\n"

    if tp["phase2"]:
        p2 = tp["phase2"]
        report += f"""
| Element | Value |
|---------|-------|
| Direction | {p2['direction']} {p2['asset']} |
| Size | {p2['size_pct']}% |
| Entry Trigger | {p2['entry_trigger']} |
| Hold | {p2['hold_days_min']}-{p2['hold_days_max']} days |
| Exit | {p2['exit_trigger']} |
| Expected Return | {p2['expected_return']:.1f}% |
"""
    else:
        report += "No Phase 2 trade yet — reversal signals required\n"

    report += f"""
### Total Max Exposure: {tp['total_max_exposure']:.1f}%**

## Key Signals to Monitor

### Positive (TACO signals)
"""
    for signal in ff.get("reversal_signals_to_watch", []):
        report += f"- {signal}\n"

    report += "\n### Negative (Anti-TACO signals)\n"
    for signal in ff.get("anti_taco_signals", []):
        report += f"- {signal}\n"

    report += f"""
---
*Analysis generated: {analysis['analyzed_at']}*
"""

    return report


# Global for convenience
market_context = {}


def main():
    global market_context

    parser = argparse.ArgumentParser(description="TACO Statement Analysis")
    parser.add_argument("--statement-id", type=str, help="Statement ID to analyze")
    parser.add_argument("--batch", action="store_true", help="Analyze all active statements")
    parser.add_argument("--output", type=str, help="Output JSON file (optional)")
    parser.add_argument(
        "--signals", type=str,
        help="Comma-separated signals to inject into Bayesian updater, "
             "e.g. 'Day2:trump_extends_deadline,Day3:counterparty_hard_rejection'",
    )

    args = parser.parse_args()

    # Parse signals if provided
    signals = None
    if args.signals:
        signals = []
        for item in args.signals.split(","):
            item = item.strip()
            if ":" in item:
                time, signal = item.split(":", 1)
                signals.append((time.strip(), signal.strip()))

    # Load data
    print("Loading statements...")
    statements = load_statements()
    print(f"Loaded {len(statements)} statements")

    print("Loading market context...")
    market_context = load_market_context()
    print(f"VIX: {market_context.get('vix', 'N/A')}")

    print("Loading Polymarket data...")
    polymarket_data = load_polymarket()

    # Select statements to analyze
    if args.statement_id:
        target = [s for s in statements if s.id == args.statement_id]
        if not target:
            print(f"Statement {args.statement_id} not found")
            sys.exit(1)
    elif args.batch:
        target = [s for s in statements if s.status == StatementStatus.ACTIVE]
        if not target:
            target = statements[:1]  # Fallback to first
    else:
        # Default: analyze most recent active or first pending
        active = [s for s in statements if s.status == StatementStatus.ACTIVE]
        if active:
            target = [active[0]]
        else:
            target = [statements[0]]

    # Analyze
    results = []
    for stmt in target:
        print(f"\nAnalyzing {stmt.id}: {stmt.statement_type.value} targeting {stmt.target_entity}")
        if signals:
            print(f"  Injecting {len(signals)} signals into Bayesian updater")
        analysis = analyze_statement(stmt, market_context, polymarket_data, signals=signals)
        results.append(analysis)

        # Generate and print report
        report = generate_report(analysis)
        print(report)

    # Save JSON if output specified
    if args.output:
        output_path = BASE_DIR / args.output
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved analysis to {output_path}")


if __name__ == "__main__":
    main()
