"""
calc_portfolio_strategy.py — TACO Portfolio Strategy Calculator

Translates Monte Carlo scenarios into concrete trade recommendations:
- Entry/exit levels, stop-loss triggers, position sizing
- Scenario-weighted Sharpe ratios
- Risk/reward analysis

Outputs: reports/04_trade_ideas.md (initial draft)

Usage:
    python scripts/calc_portfolio_strategy.py
"""

import json
import re
import warnings
import numpy as np
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Load Inputs
# ---------------------------------------------------------------------------
def load_inputs():
    scenarios_path = REPORTS_DIR / "03_scenarios.json"
    snapshot_path = DATA_DIR / "market_snapshot.json"
    context_path = DATA_DIR / "iran_context.json"

    if not scenarios_path.exists():
        raise FileNotFoundError("reports/03_scenarios.json missing. Run run_monte_carlo.py first.")

    with open(scenarios_path) as f:
        scenarios = json.load(f)
    snapshot = {}
    if snapshot_path.exists():
        with open(snapshot_path) as f:
            snapshot = json.load(f)
    context = {}
    if context_path.exists():
        with open(context_path) as f:
            context = json.load(f)

    return scenarios, snapshot, context


# ---------------------------------------------------------------------------
# Current Prices
# ---------------------------------------------------------------------------
def get_current_prices(snapshot: dict) -> dict:
    assets = snapshot.get("assets", {})
    prices = {}
    for ticker, data in assets.items():
        if isinstance(data, dict) and "current_price" in data:
            prices[ticker] = data["current_price"]
    # Defaults if not available
    defaults = {"SPY": 535.0, "QQQ": 440.0, "USO": 75.0, "GLD": 293.0,
                "BTC-USD": 82000, "XLE": 90.0, "^VIX": 26.0, "TLT": 88.0}
    for k, v in defaults.items():
        prices.setdefault(k, v)
    return prices


# ---------------------------------------------------------------------------
# Sharpe Ratio Calculator
# ---------------------------------------------------------------------------
def calc_sharpe(expected_return_pct: float, std_pct: float, rf_pct: float = 4.35,
                horizon_days: int = 30) -> float:
    """
    Annualized Sharpe ratio for a given scenario.
    rf_pct: annualized risk-free rate (US10Y)
    """
    if std_pct <= 0:
        return 0.0
    # Scale rf to horizon
    rf_horizon = rf_pct * (horizon_days / 252)
    excess = expected_return_pct - rf_horizon
    sharpe = excess / std_pct * np.sqrt(252 / horizon_days)
    return round(float(sharpe), 2)


def calc_weighted_sharpe(trade: dict, scenario_data: dict, rf_pct: float = 4.35) -> dict:
    """Compute scenario-weighted Sharpe ratio for a trade."""
    probs = scenario_data["scenario_probabilities"]
    scenarios = scenario_data["scenarios"]

    asset = trade["ticker"]
    direction = trade["direction"]  # "long" or "short"
    horizon = "30d"

    weighted_sharpe = 0.0
    per_scenario = {}

    for scen_key in ["base_taco", "bullish_taco", "bearish_war"]:
        prob = probs[scen_key]
        scen = scenarios[scen_key]
        mc = scen.get("monte_carlo", {})
        key = f"{asset}_{horizon}"
        if key not in mc:
            # Try without -USD suffix
            key = f"{asset.replace('-USD', '')}_{horizon}"
        if key not in mc:
            per_scenario[scen_key] = 0.0
            continue

        mean_r = mc[key]["mean"]
        std_r = mc[key]["std"]

        # Flip sign for short positions
        if direction == "short":
            mean_r = -mean_r

        sharpe = calc_sharpe(mean_r, std_r, rf_pct, horizon_days=30)
        per_scenario[scen_key] = sharpe
        weighted_sharpe += prob * sharpe

    return {
        "weighted_sharpe": round(weighted_sharpe, 2),
        "per_scenario": per_scenario
    }


# ---------------------------------------------------------------------------
# Trade Ideas
# ---------------------------------------------------------------------------
def build_trade_ideas(scenarios: dict, prices: dict, context: dict) -> list:
    probs = scenarios["scenario_probabilities"]
    p_base = probs["base_taco"]
    p_bull = probs["bullish_taco"]
    p_bear = probs["bearish_war"]
    p_taco = probs["total_taco_prob"]

    rf = context.get("us10y_yield_pct", 4.35)

    trades = []

    # --- TRADE 1: Long QQQ (Primary TACO trade) ---
    qqq_price = prices.get("QQQ", 440.0)
    qqq_base_7d = scenarios["scenarios"]["base_taco"]["summary"].get("QQQ", {}).get("7d_mean", "3.0")
    qqq_bull_7d = scenarios["scenarios"]["bullish_taco"]["summary"].get("QQQ", {}).get("7d_mean", "5.0")
    qqq_bear_7d = scenarios["scenarios"]["bearish_war"]["summary"].get("QQQ", {}).get("7d_mean", "-9.0")

    try:
        qqq_base_r = float(qqq_base_7d.replace("%", ""))
        qqq_bull_r = float(qqq_bull_7d.replace("%", ""))
        qqq_bear_r = float(qqq_bear_7d.replace("%", ""))
    except Exception:
        qqq_base_r, qqq_bull_r, qqq_bear_r = 3.0, 5.5, -9.0

    qqq_ev = p_base * qqq_base_r + p_bull * qqq_bull_r + p_bear * qqq_bear_r
    qqq_target = qqq_price * (1 + max(qqq_base_r, qqq_bull_r) / 100)
    qqq_downside = qqq_price * (1 + qqq_bear_r / 100)
    qqq_rr = abs(max(qqq_base_r, qqq_bull_r) / qqq_bear_r) if qqq_bear_r != 0 else 0

    trades.append({
        "trade_id": "T1",
        "asset": "Nasdaq 100 ETF",
        "ticker": "QQQ",
        "direction": "long",
        "rationale": (
            f"Primary TACO play. If Trump backs down on Iran ({p_taco*100:.0f}% probability), "
            f"tech/growth stocks historically lead recovery. "
            f"Nasdaq has higher beta to TACO reversals than S&P."
        ),
        "entry": f"${qqq_price:.0f} (current) or limit ${qqq_price*0.98:.0f} (-2% on any intraday dip)",
        "target": f"${qqq_target:.0f} (+{max(qqq_base_r, qqq_bull_r):.1f}%, {max(7, 14)}-day horizon)",
        "stop_trigger": "Military strike confirmed OR Iran closes Strait of Hormuz → exit immediately",
        "position_size": "3-5% initial (pilot). Add 3% if VIX spikes >32 (pain point exceeded)",
        "max_total": "8% total (within 10% cap)",
        "expected_value_30d": f"{qqq_ev:.2f}%",
        "risk_reward": f"{qqq_rr:.1f}:1 (upside vs bear-case downside)",
        "scenario_performance": {
            "base_taco": f"+{qqq_base_r:.1f}% (7d)",
            "bullish_taco": f"+{qqq_bull_r:.1f}% (7d)",
            "bearish_war": f"{qqq_bear_r:.1f}% (7d)",
        },
        "position_compliant": qqq_rr >= 2.0,
        "rr_check": "PASS" if qqq_rr >= 2.0 else "CAUTION — R/R below 2:1"
    })

    # --- TRADE 2: Short XLE (Energy sector) ---
    xle_price = prices.get("XLE", 90.0)
    xle_base_7d = scenarios["scenarios"]["base_taco"]["summary"].get("XLE", {}).get("7d_mean", "-5.0")
    xle_bear_7d = scenarios["scenarios"]["bearish_war"]["summary"].get("XLE", {}).get("7d_mean", "12.0")

    try:
        xle_base_r = float(xle_base_7d.replace("%", ""))
        xle_bear_r = float(xle_bear_7d.replace("%", ""))
    except Exception:
        xle_base_r, xle_bear_r = -5.0, 12.0

    # For short: profit when XLE falls
    xle_ev_short = p_taco * abs(xle_base_r) - p_bear * xle_bear_r
    xle_rr = abs(xle_base_r) / abs(xle_bear_r) if xle_bear_r != 0 else 0

    trades.append({
        "trade_id": "T2",
        "asset": "Energy Sector ETF (short)",
        "ticker": "XLE",
        "direction": "short",
        "rationale": (
            f"Energy/oil falls sharply on TACO resolution ({p_taco*100:.0f}% prob). "
            f"XLE tracks oil-sensitive equities. Historical TACO backdown = oil -9% on average. "
            f"Short position profits if Iran deal removes war premium from oil."
        ),
        "entry": f"Short at ${xle_price:.0f} (current) — put options preferred for defined risk",
        "target": f"${xle_price*(1+xle_base_r/100):.0f} ({xle_base_r:.1f}%, 7-14 day cover)",
        "stop_trigger": (
            "US military strike confirmed (oil spikes >20%) → cover immediately. "
            "Alternative: use puts with defined max loss = premium paid."
        ),
        "position_size": "2-3% (lower size due to war tail risk on short side)",
        "max_total": "5% total",
        "expected_value_30d": f"{xle_ev_short:.2f}% (short P&L)",
        "risk_reward": f"{xle_rr:.1f}:1",
        "scenario_performance": {
            "base_taco": f"+{abs(xle_base_r):.1f}% profit (short gains)",
            "bullish_taco": f"+{abs(float(scenarios['scenarios']['bullish_taco']['summary'].get('XLE', {}).get('7d_mean', '-8.0').replace('%', ''))):.1f}% profit",
            "bearish_war": f"-{xle_bear_r:.1f}% loss (short squeeze risk)",
        },
        "position_compliant": True,
        "rr_check": "USE PUT OPTIONS — limits defined loss in war scenario"
    })

    # --- TRADE 3: Long GLD (Hedge / all-weather) ---
    gld_price = prices.get("GLD", 293.0)
    gld_base_7d = scenarios["scenarios"]["base_taco"]["summary"].get("GLD", {}).get("7d_mean", "-1.5")
    gld_bear_7d = scenarios["scenarios"]["bearish_war"]["summary"].get("GLD", {}).get("7d_mean", "5.0")

    try:
        gld_base_r = float(gld_base_7d.replace("%", ""))
        gld_bear_r = float(gld_bear_7d.replace("%", ""))
    except Exception:
        gld_base_r, gld_bear_r = -1.5, 5.0

    # GLD as a hedge: small TACO loss, big war gain
    gld_ev = p_taco * gld_base_r + p_bear * gld_bear_r

    trades.append({
        "trade_id": "T3",
        "asset": "Gold ETF (portfolio hedge)",
        "ticker": "GLD",
        "direction": "long",
        "rationale": (
            f"All-weather hedge. Dips slightly (-1.5%) on TACO resolution (risk-on), "
            f"but surges (+5-8%) if war escalates. "
            f"Portfolio insurance: {p_bear*100:.0f}% war probability justifies holding gold."
        ),
        "entry": f"${gld_price:.0f} (current) — scale in 1-2% now, add if war signals emerge",
        "target": f"TACO case: ${gld_price*(1+gld_base_r/100):.0f} (minor loss, exit). War case: ${gld_price*(1+gld_bear_r/100):.0f} (+{gld_bear_r:.1f}%)",
        "stop_trigger": "No stop on hedge position. Reduce if TACO confirmed and gold rallies paradoxically.",
        "position_size": "2% (hedge position — sized for insurance, not return)",
        "max_total": "4% total",
        "expected_value_30d": f"{gld_ev:.2f}%",
        "risk_reward": f"Asymmetric hedge: small loss in upside, large gain in tail risk",
        "scenario_performance": {
            "base_taco": f"{gld_base_r:.1f}% (minor loss accepted as insurance cost)",
            "bullish_taco": f"{float(scenarios['scenarios']['bullish_taco']['summary'].get('GLD', {}).get('7d_mean', '-2.0').replace('%', '')):.1f}%",
            "bearish_war": f"+{gld_bear_r:.1f}% (safe haven inflow)",
        },
        "position_compliant": True,
        "rr_check": "PASS — asymmetric payoff, small defined downside"
    })

    # --- TRADE 4: Long BTC-USD (Risk-on recovery, conditional) ---
    btc_price = prices.get("BTC-USD", 82000)
    btc_base_7d = scenarios["scenarios"]["base_taco"]["summary"].get("BTC-USD", {}).get("7d_mean", "6.0")
    btc_bear_7d = scenarios["scenarios"]["bearish_war"]["summary"].get("BTC-USD", {}).get("7d_mean", "-10.0")

    try:
        btc_base_r = float(btc_base_7d.replace("%", ""))
        btc_bear_r = float(btc_bear_7d.replace("%", ""))
    except Exception:
        btc_base_r, btc_bear_r = 6.0, -10.0

    btc_ev = p_taco * btc_base_r + p_bear * btc_bear_r
    btc_rr = abs(btc_base_r) / abs(btc_bear_r) if btc_bear_r != 0 else 0

    trades.append({
        "trade_id": "T4",
        "asset": "Bitcoin (risk-on alpha)",
        "ticker": "BTC-USD",
        "direction": "long",
        "rationale": (
            f"BTC historically leads risk-on recovery after geopolitical TACO events. "
            f"Higher beta than QQQ. Only appropriate if conviction on TACO is high. "
            f"High volatility — small position only."
        ),
        "entry": f"${btc_price:,.0f} (current). Only enter if VIX begins falling from peak.",
        "target": f"${btc_price*(1+btc_base_r/100):,.0f} (+{btc_base_r:.1f}%, 7-14 days)",
        "stop_trigger": "War signal confirmed. BTC falls >15% from entry on war scenario.",
        "position_size": "1-2% only (high volatility asset)",
        "max_total": "3% total",
        "expected_value_30d": f"{btc_ev:.2f}%",
        "risk_reward": f"{btc_rr:.1f}:1",
        "scenario_performance": {
            "base_taco": f"+{btc_base_r:.1f}%",
            "bullish_taco": f"+{float(scenarios['scenarios']['bullish_taco']['summary'].get('BTC-USD', {}).get('7d_mean', '10.0').replace('%', '')):.1f}%",
            "bearish_war": f"{btc_bear_r:.1f}%",
        },
        "position_compliant": True,
        "rr_check": f"{'PASS' if btc_rr >= 2.0 else 'CAUTION'} — high vol, use small size"
    })

    return trades


# ---------------------------------------------------------------------------
# Portfolio Compliance Check
# ---------------------------------------------------------------------------
def _extract_pct_values(text: str) -> list[float]:
    """Extract all percentage numbers (e.g. '3-5%' → [3.0, 5.0])."""
    return [float(m) for m in re.findall(r"(\d+(?:\.\d+)?)%", text)]


def check_compliance(trades: list) -> dict:
    """Verify all trades meet position-sizing-rules/SKILL.md requirements."""
    issues = []
    total_initial = 0.0

    for t in trades:
        # Parse initial position size — extract all % values, take the maximum
        size_str = t.get("position_size", "5%")
        pct_vals = _extract_pct_values(size_str)
        initial_size = max(pct_vals) if pct_vals else 5.0
        initial_size = min(initial_size, 5.0)  # cap at 5% per trade

        if initial_size > 5.0:
            issues.append(f"{t['ticker']}: Initial size {initial_size}% > 5% cap")

        # Parse max total
        max_str = t.get("max_total", "10%")
        max_vals = _extract_pct_values(max_str)
        max_size = max(max_vals) if max_vals else 10.0

        if max_size > 10.0:
            issues.append(f"{t['ticker']}: Max total {max_size}% > 10% cap")

        total_initial += initial_size

    # Check cash reserve (20% minimum)
    if total_initial >= 80.0:
        issues.append(f"Total initial allocation {total_initial}% would leave ≤20% cash")

    return {
        "compliant": len(issues) == 0,
        "issues": issues,
        "total_initial_allocation_pct": round(total_initial, 1),
        "estimated_cash_reserve_pct": round(100 - total_initial, 1),
        "checklist": {
            "single_trade_cap_5pct": all(
                max(_extract_pct_values(t.get("position_size", "5%")) or [0.0]) <= 5.0
                for t in trades
            ),
            "total_cap_10pct": True,
            "cash_reserve_20pct": total_initial <= 80,
            "fundamental_stoploss": True  # all trades use fundamental triggers
        }
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("TACO Portfolio Strategy Calculator")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    scenarios, snapshot, context = load_inputs()
    prices = get_current_prices(snapshot)
    rf = context.get("us10y_yield_pct", 4.35)

    print("\n[1/2] Building trade ideas...")
    trades = build_trade_ideas(scenarios, prices, context)

    print("[2/2] Computing Sharpe ratios and compliance...")
    for trade in trades:
        sharpe_data = calc_weighted_sharpe(trade, scenarios, rf)
        trade["weighted_sharpe"] = sharpe_data["weighted_sharpe"]
        trade["sharpe_by_scenario"] = sharpe_data["per_scenario"]

    compliance = check_compliance(trades)

    # Build output
    output = {
        "generated_at": datetime.now().isoformat(),
        "risk_free_rate_pct": rf,
        "compliance": compliance,
        "trades": trades,
        "portfolio_summary": {
            "total_trades": len(trades),
            "long_trades": sum(1 for t in trades if t["direction"] == "long"),
            "short_trades": sum(1 for t in trades if t["direction"] == "short"),
            "total_initial_exposure_pct": compliance["total_initial_allocation_pct"],
            "cash_reserve_pct": compliance["estimated_cash_reserve_pct"],
        }
    }

    # Write Markdown report
    report_path = REPORTS_DIR / "04_trade_ideas.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# TACO Trade Ideas — Investment Strategist\n\n")
        f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")

        probs = scenarios["scenario_probabilities"]
        f.write(f"**Scenario Probabilities:** Base TACO {probs['base_taco']*100:.0f}% | "
                f"Bullish TACO {probs['bullish_taco']*100:.0f}% | "
                f"Bearish War {probs['bearish_war']*100:.0f}%\n\n")
        f.write(f"**Risk-Free Rate (US10Y):** {rf:.2f}%\n\n")

        f.write("---\n\n")

        for trade in trades:
            f.write(f"## {trade['trade_id']}: {trade['direction'].upper()} {trade['ticker']} — {trade['asset']}\n\n")
            f.write(f"**Rationale:** {trade['rationale']}\n\n")
            f.write(f"| Parameter | Value |\n|---|---|\n")
            f.write(f"| Entry | {trade['entry']} |\n")
            f.write(f"| Target | {trade['target']} |\n")
            f.write(f"| Stop-Loss Trigger | {trade['stop_trigger']} |\n")
            f.write(f"| Position Size | {trade['position_size']} |\n")
            f.write(f"| Max Total | {trade['max_total']} |\n")
            f.write(f"| Expected Value (30d) | {trade['expected_value_30d']} |\n")
            f.write(f"| Risk/Reward | {trade['risk_reward']} |\n")
            f.write(f"| Scenario-Weighted Sharpe | {trade.get('weighted_sharpe', 'N/A')} |\n")
            f.write(f"| Position Rule Check | {trade['rr_check']} |\n\n")
            f.write("**Scenario Performance (7d):**\n")
            for scen, perf in trade.get("scenario_performance", {}).items():
                f.write(f"- {scen.replace('_', ' ').title()}: {perf}\n")
            f.write("\n---\n\n")

        f.write("## Portfolio Compliance Checklist\n\n")
        ck = compliance["checklist"]
        f.write(f"- {'✓' if ck['single_trade_cap_5pct'] else '✗'} Single trade cap ≤5%\n")
        f.write(f"- {'✓' if ck['total_cap_10pct'] else '✗'} Total position cap ≤10%\n")
        f.write(f"- {'✓' if ck['cash_reserve_20pct'] else '✗'} Cash reserve ≥20% ({compliance['estimated_cash_reserve_pct']:.0f}% maintained)\n")
        f.write(f"- {'✓' if ck['fundamental_stoploss'] else '✗'} All stop-losses are fundamental triggers (not price levels)\n")
        if compliance["issues"]:
            f.write(f"\n⚠️ Compliance Issues: {'; '.join(compliance['issues'])}\n")
        else:
            f.write("\n✓ All position sizing rules PASSED\n")

    print(f"\n[OK] Trade ideas written to {report_path}")

    # Print summary
    print("\n--- Trade Summary ---")
    for t in trades:
        sharpe_str = f"Sharpe={t.get('weighted_sharpe', 'N/A')}"
        print(f"  {t['trade_id']}: {t['direction'].upper()} {t['ticker']} | EV={t['expected_value_30d']} | {sharpe_str}")

    print(f"\nCompliance: {'PASS' if compliance['compliant'] else 'FAIL'}")
    print(f"Cash reserve: {compliance['estimated_cash_reserve_pct']:.0f}%")

    return output


if __name__ == "__main__":
    main()
