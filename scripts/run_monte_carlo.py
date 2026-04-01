"""
run_monte_carlo.py — TACO Scenario Monte Carlo Simulator

Builds 3 scenarios (Base TACO / Bullish TACO / Bearish No-TACO) using:
- Bayesian updated probabilities from pattern bible + Iran context
- Monte Carlo simulation (10,000 paths per scenario)
- Student-t fat tails for No-TACO war scenario

Outputs: reports/03_scenarios.json

Usage:
    python scripts/run_monte_carlo.py
"""

import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

N_SIMULATIONS = 10_000
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Load Inputs
# ---------------------------------------------------------------------------
def load_inputs() -> tuple:
    bible_path = DATA_DIR / "taco_pattern_bible.json"
    context_path = DATA_DIR / "iran_context.json"
    snapshot_path = DATA_DIR / "market_snapshot.json"

    if not bible_path.exists():
        raise FileNotFoundError("data/taco_pattern_bible.json missing. Run run_event_study.py first.")
    if not context_path.exists():
        raise FileNotFoundError("data/iran_context.json missing. Run fetch_iran_context.py first.")

    with open(bible_path) as f:
        bible = json.load(f)
    with open(context_path) as f:
        context = json.load(f)

    snapshot = {}
    if snapshot_path.exists():
        with open(snapshot_path) as f:
            snapshot = json.load(f)

    return bible, context, snapshot


# ---------------------------------------------------------------------------
# Bayesian Probability Calculation
# ---------------------------------------------------------------------------
def compute_scenario_probs(bible: dict, context: dict) -> dict:
    """
    Compute scenario probabilities using Bayesian updating.

    Base rate: historical TACO success rate
    Adjustments:
      - VIX pain point hit → +15% (more market pain = more pressure to TACO)
      - Oil above $85 → -33% (reduces TACO rate by ~33% historically)
      - Military context → -18% (structural penalty vs trade TACOs)
      - Polymarket TACO signal → directional adjustment
      - Days since threat → increasing pressure on Base TACO, reduces Bullish
    """
    base_rate = bible.get("taco_success_rate_overall", 0.857)
    oil_above_85 = context.get("oil_above_85", False)
    vix_pain = context.get("pain_point_vix_hit", False)
    sp_pain = context.get("pain_point_sp_hit", False)
    pm_backdown = context.get("polymarket_trump_backdown_prob", 0.62)
    days = context.get("days_since_threat", 1)

    # Start with base rate
    p_taco = base_rate

    # Oil adjustment
    if oil_above_85:
        oil_ratio = bible.get("oil_conditional", {}).get("heuristic_taco_rate_oil_above_85", 0.55) / \
                    bible.get("oil_conditional", {}).get("heuristic_taco_rate_oil_below_85", 0.88)
        p_taco *= oil_ratio

    # VIX/market pain → more likely to TACO faster
    if vix_pain or sp_pain:
        p_taco = min(0.92, p_taco * 1.15)

    # Military/nuclear context penalty
    p_taco *= 0.82

    # Polymarket Bayesian update (treat as independent signal, 30% weight)
    p_taco = 0.70 * p_taco + 0.30 * pm_backdown

    # Days since threat: after 30 days, probability of fast TACO drops
    if days > 30:
        p_taco *= 0.85

    p_taco = float(np.clip(p_taco, 0.20, 0.90))

    # Split TACO probability between Base and Bullish
    # Bullish = TACO resolves fast (≤7 days) — about 35% of all TACOs historically
    p_bullish = p_taco * 0.35
    p_base = p_taco * 0.65
    p_war = 1.0 - p_taco

    # Normalize to sum to 1
    total = p_base + p_bullish + p_war
    return {
        "base_taco": round(p_base / total, 3),
        "bullish_taco": round(p_bullish / total, 3),
        "bearish_war": round(p_war / total, 3),
        "total_taco_prob": round(p_taco, 3),
        "methodology": "Bayesian: base_rate × oil_adj × military_penalty + 30% Polymarket weight"
    }


# ---------------------------------------------------------------------------
# Monte Carlo Return Distributions
# ---------------------------------------------------------------------------
def get_return_params(bible: dict, context: dict) -> dict:
    """
    Parameters for asset return distributions under each scenario.
    Sourced from: pattern bible CAR data + historical Iran/oil shock data.
    """
    # From pattern bible
    es = bible.get("event_study", {})
    car_backdown = es.get("backdown_day", {}).get("sp500_car_mean_pct", 3.4)
    car_backdown_std = es.get("backdown_day", {}).get("sp500_car_std_pct", 2.0)
    car_threat = es.get("threat_day", {}).get("sp500_ar_mean_pct", -2.1)

    # Current context adjustments
    sp_since_threat = abs(context.get("sp500_since_threat_pct", -2.5))
    overshoot_factor = max(1.0, sp_since_threat / 2.1)  # bigger dip → bigger rebound

    params = {
        "base_taco": {
            "horizon_days": [7, 14, 30],
            "assets": {
                "SPY": {
                    "7d_mean": car_backdown * 0.7 * overshoot_factor,
                    "7d_std": car_backdown_std * 1.2,
                    "30d_mean": car_backdown * 1.8 * overshoot_factor,
                    "30d_std": car_backdown_std * 2.0,
                },
                "QQQ": {
                    "7d_mean": car_backdown * 0.95 * overshoot_factor,
                    "7d_std": car_backdown_std * 1.5,
                    "30d_mean": car_backdown * 2.2 * overshoot_factor,
                    "30d_std": car_backdown_std * 2.5,
                },
                "USO": {
                    "7d_mean": -4.5,   # oil falls on de-escalation
                    "7d_std": 3.0,
                    "30d_mean": -9.0,
                    "30d_std": 5.0,
                },
                "GLD": {
                    "7d_mean": -1.5,   # gold dips on risk-on
                    "7d_std": 2.0,
                    "30d_mean": -2.0,
                    "30d_std": 3.0,
                },
                "BTC-USD": {
                    "7d_mean": 6.0,    # crypto risk-on
                    "7d_std": 8.0,
                    "30d_mean": 12.0,
                    "30d_std": 15.0,
                },
                "XLE": {
                    "7d_mean": -5.0,   # energy falls on de-escalation
                    "7d_std": 3.5,
                    "30d_mean": -10.0,
                    "30d_std": 6.0,
                },
            }
        },
        "bullish_taco": {
            "horizon_days": [7, 14, 30],
            "assets": {
                "SPY": {
                    "7d_mean": car_backdown * 1.3 * overshoot_factor,
                    "7d_std": car_backdown_std * 1.0,
                    "30d_mean": car_backdown * 2.5 * overshoot_factor,
                    "30d_std": car_backdown_std * 1.8,
                },
                "QQQ": {
                    "7d_mean": car_backdown * 1.7 * overshoot_factor,
                    "7d_std": car_backdown_std * 1.2,
                    "30d_mean": car_backdown * 3.0 * overshoot_factor,
                    "30d_std": car_backdown_std * 2.0,
                },
                "USO": {
                    "7d_mean": -7.0,
                    "7d_std": 4.0,
                    "30d_mean": -14.0,
                    "30d_std": 6.0,
                },
                "GLD": {
                    "7d_mean": -2.5,
                    "7d_std": 2.0,
                    "30d_mean": -4.0,
                    "30d_std": 3.5,
                },
                "BTC-USD": {
                    "7d_mean": 10.0,
                    "7d_std": 8.0,
                    "30d_mean": 20.0,
                    "30d_std": 18.0,
                },
                "XLE": {
                    "7d_mean": -8.0,
                    "7d_std": 4.0,
                    "30d_mean": -15.0,
                    "30d_std": 7.0,
                },
            }
        },
        "bearish_war": {
            "horizon_days": [7, 14, 30],
            "assets": {
                "SPY": {
                    "7d_mean": -7.0,   # major equity sell-off
                    "7d_std": 4.0,
                    "30d_mean": -15.0,  # prolonged bear scenario
                    "30d_std": 8.0,
                    "distribution": "student_t",
                    "df": 4,
                },
                "QQQ": {
                    "7d_mean": -9.0,
                    "7d_std": 5.0,
                    "30d_mean": -18.0,
                    "30d_std": 10.0,
                    "distribution": "student_t",
                    "df": 4,
                },
                "USO": {
                    "7d_mean": 15.0,   # oil spike (Hormuz risk)
                    "7d_std": 6.0,
                    "30d_mean": 30.0,
                    "30d_std": 12.0,
                    "distribution": "student_t",
                    "df": 4,
                },
                "GLD": {
                    "7d_mean": 5.0,    # gold safe haven
                    "7d_std": 2.5,
                    "30d_mean": 10.0,
                    "30d_std": 4.0,
                },
                "BTC-USD": {
                    "7d_mean": -10.0,  # crypto risk-off
                    "7d_std": 10.0,
                    "30d_mean": -20.0,
                    "30d_std": 18.0,
                    "distribution": "student_t",
                    "df": 4,
                },
                "XLE": {
                    "7d_mean": 12.0,   # energy rallies
                    "7d_std": 5.0,
                    "30d_mean": 20.0,
                    "30d_std": 9.0,
                },
            }
        }
    }
    return params


# ---------------------------------------------------------------------------
# Run Monte Carlo
# ---------------------------------------------------------------------------
def run_simulation(scenario_name: str, asset_params: dict, n_sim: int) -> dict:
    """Run Monte Carlo for a single scenario."""
    rng = np.random.default_rng(RANDOM_SEED)
    results = {}

    for asset, p in asset_params.items():
        dist = p.get("distribution", "normal")
        df_t = p.get("df", 4)

        for horizon in ["7d", "30d"]:
            mean = p.get(f"{horizon}_mean", 0)
            std = p.get(f"{horizon}_std", 2)

            if dist == "student_t":
                raw = rng.standard_t(df=df_t, size=n_sim)
                # standard_t has var = df/(df-2); to get var = std²: scale by std * sqrt((df-2)/df)
                raw = raw * std * np.sqrt((df_t - 2) / df_t) + mean
            else:
                raw = rng.normal(mean, std, size=n_sim)

            key = f"{asset}_{horizon}"
            results[key] = {
                "mean": round(float(np.mean(raw)), 3),
                "median": round(float(np.median(raw)), 3),
                "std": round(float(np.std(raw)), 3),
                "p5": round(float(np.percentile(raw, 5)), 3),
                "p25": round(float(np.percentile(raw, 25)), 3),
                "p75": round(float(np.percentile(raw, 75)), 3),
                "p95": round(float(np.percentile(raw, 95)), 3),
                "prob_positive": round(float(np.mean(raw > 0)), 3),
            }

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("TACO Monte Carlo Scenario Simulator")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulations: {N_SIMULATIONS:,} per scenario")
    print("=" * 60)

    bible, context, snapshot = load_inputs()

    print("\n[1/3] Computing scenario probabilities...")
    probs = compute_scenario_probs(bible, context)
    print(f"  Base TACO:    {probs['base_taco']*100:.1f}%")
    print(f"  Bullish TACO: {probs['bullish_taco']*100:.1f}%")
    print(f"  Bearish War:  {probs['bearish_war']*100:.1f}%")
    print(f"  Total TACO:   {probs['total_taco_prob']*100:.1f}%")

    print("\n[2/3] Building return parameters...")
    return_params = get_return_params(bible, context)

    print("\n[3/3] Running Monte Carlo simulations...")
    scenarios = {}
    scenario_configs = [
        ("base_taco", "Base TACO", "Trump backs down within 14 days. Deal/pause announced. Markets front-run recovery.",
         14, "Medium-confidence TACO. Oil elevated reduces certainty vs pure trade TACOs."),
        ("bullish_taco", "Bullish TACO (Fast)", "Trump backs down within 7 days due to market pain exceeding threshold. Rapid V-shaped recovery.",
         7, "Faster resolution triggered by VIX spike or S&P crossing 5% drawdown."),
        ("bearish_war", "Bearish No-TACO (War)", "Military escalation. Iran closes Hormuz or US strikes. No deal in 30-day window.",
         45, "TACO failure case. Oil shock, equity bear market, recession risk."),
    ]

    for scenario_key, scenario_name, description, timeline_days, trigger_note in scenario_configs:
        print(f"  Running {scenario_name}...")
        mc_results = run_simulation(
            scenario_key,
            return_params[scenario_key]["assets"],
            N_SIMULATIONS
        )

        scenarios[scenario_key] = {
            "name": scenario_name,
            "probability": probs[scenario_key],
            "description": description,
            "trigger_note": trigger_note,
            "timeline_days": timeline_days,
            "monte_carlo": mc_results,
            # Summary table for quick reference
            "summary": {
                asset: {
                    "7d_range": f"{mc_results.get(f'{asset}_7d', {}).get('p25', 0):.1f}% to {mc_results.get(f'{asset}_7d', {}).get('p75', 0):.1f}%",
                    "7d_mean": f"{mc_results.get(f'{asset}_7d', {}).get('mean', 0):.1f}%",
                    "30d_range": f"{mc_results.get(f'{asset}_30d', {}).get('p25', 0):.1f}% to {mc_results.get(f'{asset}_30d', {}).get('p75', 0):.1f}%",
                    "30d_mean": f"{mc_results.get(f'{asset}_30d', {}).get('mean', 0):.1f}%",
                    "prob_positive_30d": mc_results.get(f'{asset}_30d', {}).get('prob_positive', 0.5),
                }
                for asset in ["SPY", "QQQ", "USO", "GLD", "BTC-USD", "XLE"]
            }
        }

    output = {
        "generated_at": datetime.now().isoformat(),
        "n_simulations": N_SIMULATIONS,
        "probability_methodology": probs["methodology"],
        "scenario_probabilities": probs,
        "scenarios": scenarios,
        "key_watch_triggers": {
            "fast_taco_signal": "VIX spikes above 32 OR S&P drops >5% intraday → Base TACO accelerates to Bullish",
            "war_signal": "US military assets move to Gulf OR Iran closes Hormuz → Bearish scenario imminent",
            "deal_signal": "Trump tweets 'great deal' or 'progress' with Iran → Bullish TACO confirmed",
            "extended_risk": "No resolution after 30 days → Bearish probability increases by ~15pp"
        }
    }

    out_path = REPORTS_DIR / "03_scenarios.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[OK] Scenarios saved to {out_path}")

    # Print summary table
    print("\n--- Scenario Summary (7-day mean returns) ---")
    print(f"{'Asset':<12} {'Base TACO':>12} {'Bull TACO':>12} {'Bear War':>12}")
    print("-" * 50)
    for asset in ["SPY", "QQQ", "USO", "GLD", "BTC-USD", "XLE"]:
        base_7d = scenarios["base_taco"]["summary"].get(asset, {}).get("7d_mean", "N/A")
        bull_7d = scenarios["bullish_taco"]["summary"].get(asset, {}).get("7d_mean", "N/A")
        bear_7d = scenarios["bearish_war"]["summary"].get(asset, {}).get("7d_mean", "N/A")
        print(f"{asset:<12} {base_7d:>12} {bull_7d:>12} {bear_7d:>12}")

    return output


if __name__ == "__main__":
    main()
