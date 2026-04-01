"""
scripts/run_reversal_monte_carlo.py — Reversal Monte Carlo for Statement-Driven TACO

Extended Monte Carlo simulation for two-phase trading:
- Phase 1: Initial reaction distributions
- Phase 2: Reversal trade distributions given signals
- Reversal timing uncertainty

Usage:
    python scripts/run_reversal_monte_carlo.py --statement-id TACO-011 --n-sims 10000
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.statement import StatementType
from models.five_factor import FiveFactorModel


# Statement-type-specific parameters for Monte Carlo
STATEMENT_TYPE_PARAMS = {
    StatementType.TRADE_TARIFF: {
        "base_sp500_return": -2.1,
        "sp500_std": 2.3,
        "base_oil_return": 1.5,
        "oil_std": 3.0,
        "reversal_sp500_return": 3.4,  # Recovery on TACO
        "reversal_oil_return": -4.5,
        "reversal_timing_days_mean": 14,
        "reversal_timing_days_std": 8,
        "reversal_probability": 0.82,
    },
    StatementType.MILITARY: {
        "base_sp500_return": -1.8,
        "sp500_std": 3.5,
        "base_oil_return": 4.5,
        "oil_std": 5.0,
        "reversal_sp500_return": 2.5,
        "reversal_oil_return": -8.0,
        "reversal_timing_days_mean": 30,
        "reversal_timing_days_std": 15,
        "reversal_probability": 0.38,
    },
    StatementType.TERRITORIAL: {
        "base_sp500_return": -0.5,
        "sp500_std": 1.5,
        "base_oil_return": 1.0,
        "oil_std": 2.0,
        "reversal_sp500_return": 0.8,
        "reversal_oil_return": -1.5,
        "reversal_timing_days_mean": 21,
        "reversal_timing_days_std": 12,
        "reversal_probability": 0.58,
    },
    StatementType.PERSONNEL: {
        "base_sp500_return": -0.8,
        "sp500_std": 1.2,
        "base_oil_return": 0.2,
        "oil_std": 0.5,
        "reversal_sp500_return": 1.2,
        "reversal_oil_return": -0.3,
        "reversal_timing_days_mean": 7,
        "reversal_timing_days_std": 3,
        "reversal_probability": 0.78,
    },
    StatementType.POLICY: {
        "base_sp500_return": -0.5,
        "sp500_std": 1.0,
        "base_oil_return": 0.2,
        "oil_std": 0.5,
        "reversal_sp500_return": 0.7,
        "reversal_oil_return": -0.2,
        "reversal_timing_days_mean": 10,
        "reversal_timing_days_std": 5,
        "reversal_probability": 0.15,
    },
}


@dataclass
class SimulationResult:
    """Result of a single Monte Carlo simulation run."""
    reversal_occurs: bool
    reversal_day: Optional[int]
    phase1_return: float
    phase2_return: Optional[float]
    total_return: float
    sp500_path: list
    oil_path: list


def simulate_single_path(
    params: dict,
    n_days: int = 60,
    desensitization: float = 1.0,
) -> SimulationResult:
    """Simulate a single market path for a statement scenario."""

    base_sp500 = params["base_sp500_return"] * desensitization
    base_oil = params["base_oil_return"]

    # Determine if reversal occurs and when
    reversal_prob = params["reversal_probability"]
    reversal_occurs = np.random.random() < reversal_prob

    if reversal_occurs:
        # Sample reversal timing from normal distribution
        reversal_day = max(1, int(np.random.normal(
            params["reversal_timing_days_mean"],
            params["reversal_timing_days_std"]
        )))
        reversal_day = min(reversal_day, n_days)
    else:
        reversal_day = None

    # Generate daily returns
    sp500_daily_std = params["sp500_std"] / np.sqrt(252)  # Annualized to daily
    oil_daily_std = params["oil_std"] / np.sqrt(252)

    sp500_path = []
    oil_path = []

    cumulative_sp500 = 0.0
    cumulative_oil = 0.0

    for day in range(1, n_days + 1):
        if reversal_day and day >= reversal_day:
            # Post-reversal: mean reversion
            sp500_daily = np.random.normal(0.1, sp500_daily_std)  # Slight positive drift
            oil_daily = np.random.normal(-0.2, oil_daily_std)
        else:
            # Pre-reversal: threat environment
            sp500_daily = np.random.normal(base_sp500 / 60, sp500_daily_std)  # Spread over days
            oil_daily = np.random.normal(base_oil / 60, oil_daily_std)

        cumulative_sp500 += sp500_daily
        cumulative_oil += oil_daily

        sp500_path.append(cumulative_sp500)
        oil_path.append(cumulative_oil)

    # Calculate returns
    phase1_return = cumulative_sp500 if (reversal_day is None or reversal_day > 3) else sp500_path[2]

    if reversal_occurs and reversal_day:
        # Phase 2 recovery
        phase2_return = (params["reversal_sp500_return"] - base_sp500) * (1 - reversal_day / n_days)
        # Adjust for time in market
        phase2_return = phase2_return * 0.8  # Friction/adjustment factor
    else:
        phase2_return = 0.0

    total_return = phase1_return + phase2_return

    return SimulationResult(
        reversal_occurs=reversal_occurs,
        reversal_day=reversal_day,
        phase1_return=phase1_return,
        phase2_return=phase2_return,
        total_return=total_return,
        sp500_path=sp500_path,
        oil_path=oil_path,
    )


def run_monte_carlo(
    statement_type: StatementType,
    n_sims: int = 10000,
    n_days: int = 60,
    desensitization: float = 1.0,
    initial_position_pct: float = 2.5,
    phase2_size_pct: float = 5.0,
) -> dict:
    """
    Run Monte Carlo simulation for statement type.

    Returns:
        Dictionary with simulation statistics and distributions
    """
    params = STATEMENT_TYPE_PARAMS.get(statement_type, STATEMENT_TYPE_PARAMS[StatementType.TRADE_TARIFF])

    np.random.seed(42)  # Reproducibility

    results = []
    reversal_days = []
    phase1_returns = []
    phase2_returns = []
    total_returns = []

    for _ in range(n_sims):
        sim = simulate_single_path(params, n_days, desensitization)
        results.append(sim)
        reversal_days.append(sim.reversal_day if sim.reversal_occurs else None)
        phase1_returns.append(sim.phase1_return)
        if sim.phase2_return is not None:
            phase2_returns.append(sim.phase2_return)
        total_returns.append(sim.total_return)

    # Calculate statistics
    reversal_rate = sum(1 for r in results if r.reversal_occurs) / n_sims

    reversal_days_valid = [d for d in reversal_days if d is not None]
    avg_reversal_day = np.mean(reversal_days_valid) if reversal_days_valid else None
    median_reversal_day = np.median(reversal_days_valid) if reversal_days_valid else None

    # Percentiles for returns
    total_returns_arr = np.array(total_returns)
    phase1_arr = np.array(phase1_returns)

    # Calculate position returns
    phase1_position_return = phase1_arr * (initial_position_pct / 100) * 100  # In dollars/percent

    # Phase 2 returns only where reversal occurred
    phase2_arr = np.array([r.phase2_return if r.phase2_return else 0 for r in results])
    phase2_position_return = phase2_arr * (phase2_size_pct / 100) * 100

    total_position_return = phase1_position_return + phase2_position_return

    return {
        "statement_type": statement_type.value,
        "n_sims": n_sims,
        "n_days": n_days,
        "desensitization": desensitization,
        "reversal_statistics": {
            "reversal_rate": reversal_rate,
            "avg_reversal_day": round(avg_reversal_day, 1) if avg_reversal_day else None,
            "median_reversal_day": round(median_reversal_day, 1) if median_reversal_day else None,
            "p25_reversal_day": round(np.percentile(reversal_days_valid, 25), 0) if reversal_days_valid else None,
            "p75_reversal_day": round(np.percentile(reversal_days_valid, 75), 0) if reversal_days_valid else None,
        },
        "sp500_return_percentiles": {
            "p5": round(np.percentile(total_returns_arr, 5), 2),
            "p25": round(np.percentile(total_returns_arr, 25), 2),
            "p50": round(np.percentile(total_returns_arr, 50), 2),
            "p75": round(np.percentile(total_returns_arr, 75), 2),
            "p95": round(np.percentile(total_returns_arr, 95), 2),
            "mean": round(np.mean(total_returns_arr), 2),
            "std": round(np.std(total_returns_arr), 2),
        },
        "position_return_percentiles": {
            "p5": round(np.percentile(total_position_return, 5), 2),
            "p25": round(np.percentile(total_position_return, 25), 2),
            "p50": round(np.percentile(total_position_return, 50), 2),
            "p75": round(np.percentile(total_position_return, 75), 2),
            "p95": round(np.percentile(total_position_return, 95), 2),
            "mean": round(np.mean(total_position_return), 2),
            "std": round(np.std(total_position_return), 2),
        },
        "probability_of_loss": {
            "phase1_only": round(np.mean(phase1_arr < 0), 3),
            "total": round(np.mean(total_returns_arr < 0), 3),
            "position": round(np.mean(total_position_return < 0), 3),
        },
        "sharpe_ratio": round(
            np.mean(total_position_return) / np.std(total_position_return)
            if np.std(total_position_return) > 0 else 0,
            2
        ),
    }


def generate_scenario_report(mc_result: dict) -> str:
    """Generate human-readable Monte Carlo report."""

    rev_stats = mc_result["reversal_statistics"]
    sp500 = mc_result["sp500_return_percentiles"]
    pos = mc_result["position_return_percentiles"]
    prob_loss = mc_result["probability_of_loss"]

    report = f"""
# Monte Carlo Simulation Results: {mc_result['statement_type'].upper()}

## Configuration
- Simulations: {mc_result['n_sims']:,}
- Time horizon: {mc_result['n_days']} days
- Desensitization: {mc_result['desensitization']:.2f}

## Reversal Statistics
| Metric | Value |
|--------|-------|
| Reversal Rate | {rev_stats['reversal_rate']:.1%} |
| Avg Reversal Day | {rev_stats['avg_reversal_day'] or 'N/A'} |
| Median Reversal Day | {rev_stats['median_reversal_day'] or 'N/A'} |
| 25th Percentile | {rev_stats['p25_reversal_day'] or 'N/A'} |
| 75th Percentile | {rev_stats['p75_reversal_day'] or 'N/A'} |

## S&P 500 Return Distribution
| Percentile | Return |
|------------|--------|
| 5th (Worst) | {sp500['p5']:.2f}% |
| 25th | {sp500['p25']:.2f}% |
| 50th (Median) | {sp500['p50']:.2f}% |
| 75th | {sp500['p75']:.2f}% |
| 95th (Best) | {sp500['p95']:.2f}% |
| Mean | {sp500['mean']:.2f}% |
| Std Dev | {sp500['std']:.2f}% |

## Two-Phase Position Return (${mc_result.get('initial_position_pct', 2.5):.1f}% Phase1 + ${mc_result.get('phase2_size_pct', 5.0):.1f}% Phase2)
| Percentile | Return |
|------------|--------|
| 5th (Worst) | {pos['p5']:.2f}% |
| 25th | {pos['p25']:.2f}% |
| 50th (Median) | {pos['p50']:.2f}% |
| 75th | {pos['p75']:.2f}% |
| 95th (Best) | {pos['p95']:.2f}% |
| Mean | {pos['mean']:.2f}% |
| Std Dev | {pos['std']:.2f}% |

## Risk Metrics
| Metric | Value |
|--------|-------|
| Probability of Loss (Total) | {prob_loss['total']:.1%} |
| Sharpe Ratio | {mc_result['sharpe_ratio']:.2f} |

## Key Insights
"""

    # Add insights based on results
    if mc_result['sharpe_ratio'] > 1.0:
        report += "- ✅ Positive expected return with favorable risk/reward\n"
    elif mc_result['sharpe_ratio'] > 0.5:
        report += "- ⚠️ Moderate expected return\n"
    else:
        report += "- ❌ Poor risk-adjusted return\n"

    if rev_stats['reversal_rate'] > 0.6:
        report += "- ✅ High reversal probability supports TACO strategy\n"
    elif rev_stats['reversal_rate'] < 0.4:
        report += "- ❌ Low reversal probability — avoid Phase 2\n"

    if prob_loss['total'] < 0.3:
        report += "- ✅ Low probability of loss\n"
    elif prob_loss['total'] > 0.5:
        report += "- ⚠️ High probability of loss — reduce position size\n"

    return report


def main():
    parser = argparse.ArgumentParser(description="TACO Reversal Monte Carlo")
    parser.add_argument("--statement-type", type=str, default="MILITARY",
                        choices=["TRADE_TARIFF", "MILITARY", "TERRITORIAL", "PERSONNEL", "POLICY"],
                        help="Statement type to simulate")
    parser.add_argument("--n-sims", type=int, default=10000, help="Number of simulations")
    parser.add_argument("--n-days", type=int, default=60, help="Simulation days")
    parser.add_argument("--desensitization", type=float, default=1.0, help="Desensitization multiplier")
    parser.add_argument("--output", type=str, help="Output JSON file")
    parser.add_argument("--report", action="store_true", help="Generate text report")

    args = parser.parse_args()

    # Convert uppercase CLI argument to lowercase enum value
    type_mapping = {
        "TRADE_TARIFF": "trade_tariff",
        "MILITARY": "military",
        "TERRITORIAL": "territorial",
        "PERSONNEL": "personnel",
        "POLICY": "policy",
    }
    type_value = type_mapping.get(args.statement_type, args.statement_type.lower())
    statement_type = StatementType(type_value)

    print(f"Running Monte Carlo for {statement_type.value}...")
    print(f"Simulations: {args.n_sims}, Days: {args.n_days}, Desensitization: {args.desensitization}")

    result = run_monte_carlo(
        statement_type=statement_type,
        n_sims=args.n_sims,
        n_days=args.n_days,
        desensitization=args.desensitization,
    )

    if args.report:
        print(generate_scenario_report(result))

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to {output_path}")

    return result


if __name__ == "__main__":
    main()
