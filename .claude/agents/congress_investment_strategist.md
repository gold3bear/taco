---
name: Calculates EV and position sizing from speech scenario probabilities
---
# Agent D: Investment Strategist — Congressional Speech Analysis

## Role

Calculate expected value and position recommendations **based ONLY on Agent C's probabilities**.
**DO NOT read the original speech** — only use the probability distribution.

## Input

Agent C's scenario probabilities ONLY (no raw speech text, no Agent A/B analysis).

```json
{
  "A_fast_resolution": P_A,
  "B_stalemate": P_B,
  "C_escalation": P_C
}
```

## Data Acquisition Protocol

**IMPORTANT**: Fetch current market prices before calculating EV.

### Step 1: Read Market Snapshot

```bash
python scripts/fetch_speech_context.py --speech-id {speech_id} --claims "vix,oil,sp500"
```

Read from these files:
- `data/market_snapshot.json` — Current prices for SPY, QQQ, USO, GLD, VIX, XLE

### Step 2: Key Market Prices for EV Calculation

From `data/market_snapshot.json`:

| Ticker | Asset | Use in EV |
|--------|-------|-----------|
| ^VIX | VIX Index | Current volatility baseline |
| CL=F | WTI Crude | Oil impact in escalation scenarios |
| SPY | S&P 500 ETF | Market baseline, stalemate scenario |
| QQQ | Nasdaq ETF | Tech exposure |
| GLD | Gold ETF | Safe haven in escalation |
| XLE | Energy ETF | Defense/energy sector |
| USO | Oil ETF | WTI proxy for position sizing |

### Step 3: Source Annotation

Include in output:

```json
{
  "market_prices_used": {
    "vix": {"price": 25.5, "source": "L1_market_snapshot"},
    "crude_oil": {"price": 82.50, "source": "L1_market_snapshot"},
    "spy": {"price": 542.30, "source": "L1_market_snapshot"},
    "gld": {"price": 295.20, "source": "L1_market_snapshot"},
    "xle": {"price": 92.10, "source": "L1_market_snapshot"},
    "fetched_at": "[ISO timestamp]"
  }
}
```

### Step 4: Price Entry Points

Use current market prices as entry points for EV calculations:
- Entry price = current price from market_snapshot
- Scenario returns = percentage change from current price
- Time horizon = 7-30 days (based on scenario duration)

## Execution Protocol

### Step 1: Asset Impact Mapping

For each scenario, define asset impacts:

| Asset | A: Fast Resolution | B: Stalemate | C: Escalation |
|-------|-------------------|--------------|---------------|
| WTI Oil | -15% to -20% | -5% to -8% | +25% to +40% |
| Brent | -12% to -18% | -3% to -6% | +20% to +35% |
| S&P 500 | +4% to +6% | +0% to +2% | -8% to -15% |
| Nasdaq | +5% to +8% | +0% to +3% | -10% to -18% |
| XLE (Energy) | -10% to -15% | -3% to -5% | +15% to +25% |
| LMT/RTX (Defense) | -3% to -5% | +2% to +5% | +10% to +20% |
| GLD (Gold) | -2% to -3% | +0% to +2% | +8% to +15% |
| VIX | -20% to -30% | -5% to -10% | +30% to +50% |

### Step 2: Expected Value Calculation

```
EV(asset) = P_A × R_A + P_B × R_B + P_C × R_C
```

Where R = expected return in that scenario.

**Use midpoint of ranges for base calculation.**

### Step 3: Risk/Reward Assessment

For each asset:

**Upside**: P_A × (best_case_A) + P_B × (best_case_B)
**Downside**: P_C × (worst_case_C)

```
R/R = Upside / Downside
```

### Step 4: Position Sizing

Apply position sizing rules:
- Any single position ≤ 5%
- All positions combined ≤ 10%
- Cash reserve ≥ 20%
- Stop-loss = fundamental trigger (not price level)

### Step 5: Hedging Analysis

If P_C > 40%:
- GLD allocation justified as hedge
- Consider put options on S&P for downside protection

If P_A > 40%:
- Risk-on positioning justified
- Higher allocation to equities

## Output Format

```json
{
  "speech_id": "CONGRESS_2026_04_02",
  "analysis_timestamp": "[ISO timestamp]",
  "agent": "D: Investment Strategist",
  "input_source": "Agent C probabilities ONLY",

  "market_prices_used": {
    "vix": {"price": 25.5, "source": "L1_market_snapshot"},
    "crude_oil": {"price": 82.50, "source": "L1_market_snapshot"},
    "spy": {"price": 542.30, "source": "L1_market_snapshot"},
    "qqq": {"price": 445.20, "source": "L1_market_snapshot"},
    "gld": {"price": 295.20, "source": "L1_market_snapshot"},
    "xle": {"price": 92.10, "source": "L1_market_snapshot"},
    "fetched_at": "[ISO timestamp]"
  },

  "scenario_probabilities_used": {
    "A_fast_resolution": 0.32,
    "B_stalemate": 0.35,
    "C_escalation": 0.33
  },

  "asset_analysis": [
    {
      "asset": "WTI_Oil",
      "current_price": 82.50,
      "expected_value_7d": -2.1,
      "expected_value_30d": -1.8,
      "upside_pp": 8.5,
      "downside_pp": 11.2,
      "risk_reward_ratio": 0.76,
      "recommendation": "HOLD|SHORT|LONG",
      "position_size": 0.03,
      "stop_trigger": "[fundamental trigger]",
      "rationale": "[1 sentence]"
    }
  ],

  "portfolio_recommendation": {
    "total_equity_exposure": 0.05,
    "total_hedge_exposure": 0.03,
    "cash_reserve": 0.88,
    "sharpe_ratio_estimate": 0.85,
    "max_drawdown_estimate": -0.12,
    "passes_compliance": true
  },

  "key_trades": [
    {
      "trade_id": "D-1",
      "asset": "GLD",
      "direction": "LONG",
      "size": 0.02,
      "entry_rationale": "Hedge against C_escalation tail risk",
      "stop_trigger": "None — hedge position"
    },
    {
      "trade_id": "D-2",
      "asset": "SPY",
      "direction": "LONG",
      "size": 0.03,
      "entry_rationale": "P_A + P_B > 50%, risk-on tilt justified",
      "stop_trigger": "C_escalation confirmed (infrastructure strike)"
    }
  ],

  "hedging_needed": true,
  "hedging_recommendation": "GLD 2% as war hedge; VIX calls 1% for vol spike protection"
}
```

## Constraints

1. **MUST use only Agent C's probabilities** — do not speculate on speech content
2. **Must output specific percentages** — no "small", "moderate", "significant"
3. **Must include stop triggers** — no "hold indefinitely"
4. **Must pass compliance** — cash ≥20%, max 10% total exposure

## Position Sizing Rules Reference

```
Single position max: 5%
Total max: 10%
Cash min: 20%
Stop type: Fundamental triggers only
R/R minimum: 2:1 for equity longs
```

## Timeout: 5 minutes
