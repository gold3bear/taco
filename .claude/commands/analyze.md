# /analyze — Statement-Driven TACO Analysis

Analyze a Trump statement using the Five-Factor Reversal Model and generate Two-Phase trade recommendations.

## Usage

```
/analyze --statement-id TACO-011
/analyze --batch
/analyze "Trump threatens 50% tariffs on EU imports"
/analyze --monitor
```

## Pre-flight Check

Before running, ensure:
1. `data/statements.json` exists (run `python scripts/migrate_events.py` if not)
2. `models/` directory is on Python path
3. `reports/` and `data/` directories exist

## Pipeline Steps

### Step 1: Load Statement

```bash
python scripts/run_statement_analysis.py --statement-id TACO-011
```

Input: statement ID from statements.json
Output: Full statement object with classification

### Step 2: Five-Factor Analysis

The script automatically runs:
1. **Classifier** → Statement type, intensity, target
2. **MarketReaction** → Predicted asset returns with desensitization
3. **ReversalEngine** → Five-Factor probability calculation
4. **Sentiment** → Narrative/reversal ease analysis
5. **Counterparty** → Target entity decision model

### Step 3: Two-Phase Trading

Generates:
- Phase 1: Initial reaction trade (2-3%, hold 1-3 days)
- Phase 2: Reversal trade (prob×10%, max 8%)

## Output Files

| File | Description |
|------|-------------|
| `reports/statement_analysis_{id}.md` | Human-readable analysis |
| `data/statement_analysis_{id}.json` | Machine-readable results |
| `data/probability_history_{id}.json` | Probability trajectory |

## Five-Factor Probability Output Example

```json
{
  "statement_id": "TACO-011",
  "reversal_probability": 0.293,
  "factors": {
    "factor_1_base_rate": {"type": "MILITARY", "value": 0.38},
    "factor_2_market_pain": {"vix": 20, "value": 1.0, "boost_pp": 25},
    "factor_3_counterparty": {"signal": "survival_stakes", "value": -0.30},
    "factor_4_domestic": {"gas": 3.50, "midterm": 18, "value": 0.0},
    "factor_5_polymarket": {"polymarket": 0.085, "divergence": 0.295, "WARNING": true}
  },
  "desensitization": {"nth": 1, "multiplier": 1.0}
}
```

## Two-Phase Trading Summary

| Phase | Trigger | Size | Hold | Exit |
|-------|---------|------|------|------|
| Phase 1 | Initial reaction follows prediction | 2-3% | 1-3 days | Pain exceeded OR 3 days |
| Phase 2 | Reversal signals detected | prob×10%, max 8% | Until confirmed | Reversal confirmed OR 5 days |

## Iran Case Analysis

For TACO-011 (Iran Nuclear Strike Threat):

```
Factor 1: 38% (MILITARY base rate)
Factor 2: +25pp (VIX=20 → max pain)
Factor 3: -30pp (Iran survival stakes = IRGC cannot concede)
Factor 4: 0pp (gas=$3.50, midterm=18m)
Factor 5: ~0pp (large divergence but weight=5%)

P(reversal) = 0.38 × 1.25 × 0.70 ≈ 33%
```

**Key insight:** Iran TACO probability is LOW (33%) not HIGH (93%) because:
1. IRGC controls Iran — cannot accept face-saving exit
2. Nuclear program = Khamenei/IRGC legitimacy issue
3. Even "pause" language would be seen as US capitulation

## Reversal Signals to Watch

### Positive (TACO signals)
- Trump says "great progress"
- Trump says "they called me"
- Third party (Pakistan/Qatar) announces mediation
- VIX drops >10% without news catalyst

### Negative (Anti-TACO signals)
- New harder statement from Trump
- Military action confirmed
- Iran hard rejection of negotiations
- Iran enrichment expansion

## Monte Carlo Simulation

```bash
python scripts/run_reversal_monte_carlo.py --statement-type MILITARY --n-sims 10000
```

Generates return distributions and risk metrics for the statement type.

## Real-time Monitoring

```bash
python scripts/realtime_monitor.py --daemon --poll-interval 300
```

Monitors for reversal signals and updates probabilities continuously.
