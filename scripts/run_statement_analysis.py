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

    return {
        "vix": data.get("vix", 20.0),
        "sp500": data.get("sp500", 5000.0),
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
    polymarket_prob = None
    if polymarket_data:
        # Try to find relevant probability
        entity = statement.target_entity.lower()
        if entity == "iran" and "iran_war_prob" in polymarket_data:
            polymarket_prob = polymarket_data.get("iran_war_prob")
        elif "trump_backdown_prob" in polymarket_data:
            polymarket_prob = 1.0 - polymarket_data.get("iran_war_prob", 0.5)

    # Get base return for desensitization
    base_return = get_market_reaction_estimate(statement)

    # Run model
    result = model.calculate(
        statement_type=statement.statement_type,
        vix_current=market_context.get("vix", 20.0),
        counterparty_signal=market_context.get("counterparty_signal", "neutral"),
        gas_price=market_context.get("gas_price", 3.50),
        midterm_months=market_context.get("midterm_months", 18),
        market_drawdown=market_context.get("market_drawdown", 0.0),
        polymarket_prob=polymarket_prob,
        nth_similar_threat=statement.nth_similar_threat,
        base_return=base_return,
    )

    return result.to_dict()


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
        "two_phase_trading": two_phase,
        "market_context": market_context,
        "analyzed_at": datetime.now().isoformat(),
    }


def generate_report(analysis: dict) -> str:
    """Generate human-readable analysis report."""

    summary = analysis["statement_summary"]
    ff = analysis["five_factor"]
    tp = analysis["two_phase_trading"]

    # Determine TACO verdict
    prob = ff["probability"]
    if prob >= 0.70:
        verdict = "HIGH TACO PROBABILITY"
        color = "🟢"
    elif prob >= 0.40:
        verdict = "MODERATE TACO PROBABILITY"
        color = "🟡"
    else:
        verdict = "LOW TACO PROBABILITY"
        color = "🔴"

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

**Reversal Probability: {prob:.1%}**

### Five-Factor Breakdown

| Factor | Value | Contribution |
|--------|-------|--------------|
| Base Rate ({summary['type']}) | {ff['factors']['factor_1_base_rate']['value']:.0%} | {ff['factors']['factor_1_base_rate']['value']:.0%} |
| Market Pain (VIX={market_context.get('vix', 'N/A')}) | {ff['factors']['factor_2_market_pain']['value']:.1f} | +{ff['factors']['factor_2_market_pain']['boost_pp']:.0f}pp |
| Counterparty Signal | {ff['factors']['factor_3_counterparty']['value']:+.0f} | {ff['factors']['factor_3_counterparty']['value']*100:.0f}pp |
| Domestic Pressure | {ff['factors']['factor_4_domestic']['value']:+.0f} | {ff['factors']['factor_4_domestic']['value']*100:.0f}pp |
| Polymarket Calibration | {ff['factors']['factor_5_polymarket']['value']:+.2f} | {ff['factors']['factor_5_polymarket']['value']*100:.1f}pp |

**Confidence:** {ff['confidence']:.0%}

### Time Decay Forecast

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

    args = parser.parse_args()

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
        analysis = analyze_statement(stmt, market_context, polymarket_data)
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
