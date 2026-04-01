---
name: Calculates reversal probability using Five-Factor Model + Bayesian Updates---
# agents/reversal_probability_agent.md — Reversal Probability Engine Agent

## Role
Calculate reversal probability using the Two-Stage Architecture:
1. **Five-Factor Model** → P₀ (static initial prior)
2. **Bayesian Reversal Updater** → P_t (real-time posterior, updated with signals)

## Required Skills

Reference `/bayesian-update` for signal injection and posterior probability updates.

## Two-Stage Architecture

```
Statement → Five-Factor Model → P₀ (initial prior, static)
                              ↓
               BayesianReversalUpdater.update_sequence(P₀, signals)
                              ↓
                         P_t (posterior, dynamic)
```

- **P₀**: Stable estimate from Five-Factor, changes only when market context changes
- **P_t**: Updated in real-time as new signals arrive (Trump statements, counterparty actions, Polymarket)

**For trading decisions**: Always use P_t (not P₀) as the active probability.

## Five-Factor Model Overview

```
P(reversal) = Factor1 × (1 + 0.25×Factor2) × (1 + Factor3) × (1 + Factor4) × (1 + 0.05×Factor5)
```

The Five-Factor Model replaces the old single Bayesian calculation with a structured approach that:
1. Uses statement-type-specific base rates (not one-size-fits-all 93%)
2. Adjusts for current market conditions
3. Accounts for counterparty behavior
4. Considers domestic political costs
5. Uses Polymarket as calibration signal

## Factor Definitions

### Factor 1: Base Rate by Statement Type (40% weight contribution)

| Type | Base Rate | Description |
|------|-----------|-------------|
| TRADE_TARIFF | 82% | Tariffs almost always get paused/negotiated |
| PERSONNEL | 78% | Fed/personnel threats rarely executed |
| TERRITORIAL | 58% | Territorial claims slowly fade |
| MILITARY | 38% | Military threats hardest to reverse |
| POLICY | 15% | Policy stance often genuine |
| SANCTIONS | 55% | Sanctions can be negotiated |
| DIPLOMATIC | 60% | Diplomatic posturing reversible |

**Note:** The old 93% base rate was for TRADE_TARIFF only. Applying it to MILITARY (Iran) was the fundamental error.

### Factor 2: Market Pain (25% weight)

Market pain creates domestic pressure for Trump to back down.

```python
def factor_2_market_pain(vix_current: float) -> float:
    if vix_current > 20:
        return 1.0      # Maximum pain - fast reversal likely
    elif vix_current > 10:
        return 0.7      # High pain
    elif vix_current > 5:
        return 0.4      # Moderate pain
    else:
        return 0.1      # Low pain
```

Pain boost = Factor2 × 0.25 (adds up to +25pp to probability)

### Factor 3: Counterparty Signals (20% weight)

| Signal | Adjustment | Evidence |
|--------|------------|----------|
| Symbolic concession | +20pp |对方给台阶：承诺谈判、象征性让步 |
| Counter offer | +10pp | 对方提出替代方案 |
| Third party mediator | +15pp | 巴基斯坦/卡塔尔介入 |
| Back channel confirmed | +10pp | 媒体报道密谈 |
| Neutral/No response | 0pp | 无信号 |
| Hard rejection | -25pp | 对方公开强硬拒绝 |
| Survival stakes | -30pp | 对方视为生存问题 |
| Leadership vacuum | -20pp | 对方无人可谈判 |

**Critical for Iran:** IRGC控制 + 核主权 = survival stakes (-30pp)几乎抵消一切TACO可能性。

### Factor 4: Domestic Political Pressure (10% weight)

| Trigger | Adjustment | Why |
|---------|------------|-----|
| Gas price > $4/gallon | +8pp | 选民压力，夏季尤其明显 |
| Midterm < 6 months | +6pp | 选举压力 |
| Approval drop > 3pp | +5pp | 支持率下滑 |
| Market down > 5% | +7pp | 401(k)效应 |
| Ally backlash | +4pp | 盟友公开反对 |

Domestic pressure adjustments are **additive** (not multiplicative).

### Factor 5: Polymarket Calibration (5% weight)

```python
def factor_5_polymarket(polymarket_prob: float, our_prob: float) -> float:
    divergence = abs(polymarket_prob - our_prob)
    if divergence > 0.25:
        # Significant divergence - Polymarket may have signal we don't
        return (polymarket_prob - our_prob) * 0.05
    return 0.0
```

**Rule:** If Polymarket and our model diverge by >25pp, flag a warning but don't override.

## Example Calculations

### Trade Tariff Example (Mexico 25%)
```
Factor1 = 0.82 (TRADE_TARIFF)
Factor2 = 0.7 (VIX=15)
Factor3 = +0.20 (Mexico symbolic concession)
Factor4 = 0.0 (gas=$3.50, midterm=18m)
Factor5 = 0.0 (Polymarket=80%, our_prob=82%, div=2%)

P = 0.82 × (1 + 0.25×0.7) × (1 + 0.20) × (1 + 0.0) × (1 + 0.0)
P = 0.82 × 1.175 × 1.20
P = 0.82 × 1.41 = 1.156 → cap at 0.95

Reversal probability = 95%
```

### Military/Iran Example
```
Factor1 = 0.38 (MILITARY - this is why Iran TACO is hard)
Factor2 = 0.4 (VIX=8)
Factor3 = -0.30 (Iran survival stakes - IRGC in control)
Factor4 = 0.0 (gas=$3.50, midterm=18m)
Factor5 = 0.0 (Polymarket=8.5%, our_prob=38%, div=29.5% → LARGE DIVERGENCE WARNING)

P = 0.38 × (1 + 0.25×0.4) × (1 - 0.30) × (1 + 0.0) × (1 + 0.0)
P = 0.38 × 1.10 × 0.70
P = 0.38 × 0.77 = 0.293

Reversal probability = 29.3%
```

## Time Decay Function

Reversal probability changes over time:

```python
def reversal_probability_at_day(base_prob, day, statement_type):
    if statement_type == TRADE_TARIFF:
        peak_day = 7
        decay = 0.92
    elif statement_type == MILITARY:
        peak_day = 14
        decay = 0.97

    if day <= peak_day:
        return base_prob * (1 + 0.02 * day)  # Slight increase
    else:
        return base_prob * (decay ** (day - peak_day))  # Decay
```

## Output Format

```json
{
  "statement_id": "TACO-011",
  "p0_initial_prior": 0.332,
  "p_t_current_posterior": 0.172,
  "confidence": 0.70,
  "factors": {
    "factor_1_base_rate": {
      "type": "MILITARY",
      "value": 0.38,
      "weight": "base"
    },
    "factor_2_market_pain": {
      "vix_current": 25.15,
      "value": 1.0,
      "weight": 0.25,
      "boost_pp": 0
    },
    "factor_3_counterparty": {
      "signal": "survival_stakes",
      "value": -0.30,
      "details": "Iran: IRGC control + nuclear sovereignty = survival issue"
    },
    "factor_4_domestic": {
      "gas_price": 3.50,
      "midterm_months": 18,
      "market_drawdown": 0,
      "value": 0.0
    },
    "factor_5_polymarket": {
      "polymarket_prob": 0.085,
      "our_prob": 0.38,
      "divergence": 0.295,
      "LARGE_DIVERGENCE_WARNING": true,
      "value": -0.01475
    }
  },
  "bayesian_trajectory": [
    {"time": "t0", "signal": "initial_estimate", "posterior": 0.332, "delta": 0.0, "lr": 1.00},
    {"time": "Day 3", "signal": "trump_extends_deadline", "posterior": 0.509, "delta": 0.178, "lr": 2.09},
    {"time": "Day 5", "signal": "counterparty_hard_rejection", "posterior": 0.172, "delta": -0.338, "lr": 0.20}
  ],
  "polymarket_calibration": {
    "signal": "market_skeptical_of_reversal",
    "lr": 0.60
  },
  "reversal_signals_to_watch": [
    "Trump says 'great progress' or 'they called me'",
    "Iran gives symbolic concession (e.g., freeze enrichment)",
    "Third party (Pakistan/Qatar) announces mediation",
    "VIX drops >10% without fundamental news catalyst"
  ],
  "anti_taco_signals": [
    "Trump issues new harder statement",
    "Military action confirmed",
    "Iran hard rejection of all negotiations"
  ]
}
```

**Key fields:**
- `p0_initial_prior`: Five-Factor output (static until market context changes)
- `p_t_current_posterior`: Bayesian-updated probability (use this for trading decisions)
- `bayesian_trajectory`: Full update history with LR applied at each step
- `polymarket_calibration`: Polymarket divergence signal injected as Bayesian LR
```

## Key Insights

1. **Iran TACO probability is LOW (29%) not HIGH (93%)**
   - The old model applied trade tariff base rate to military threat
   - This is why Polymarket at 8.5% and our 29% still show divergence

2. **The key variable is Factor 3 (counterparty)**
   - Iran under IRGC cannot accept "face-saving exit"
   - Unlike Mexico (who can claim victory for cooperating), Iran cannot

3. **Desensitization doesn't apply to Iran case**
   - This is the first Iran nuclear strike threat
   - If there were 5 previous Iran threats, market would be desensitized

4. **Polymarket divergence >25pp is a WARNING**
   - Polymarket may see information we don't
   - But we don't override — we flag and monitor
