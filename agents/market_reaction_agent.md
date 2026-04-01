# agents/market_reaction_agent.md — Market Reaction Predictor Agent

## Role
Predict initial market reaction to a classified Trump statement.

## Input
- Statement: Classified Statement object from Classifier Agent
- Historical reactions: Same statement_type's historical reactions from statements.json

## Historical Reaction Data (from TACO pattern bible)

### By Statement Type

```python
TYPE_REACTION_MODEL = {
    StatementType.TRADE_TARIFF: {
        "sp500_mean": -2.1,      # percent
        "sp500_std": 2.3,
        "vix_mean": 8.5,
        "oil_mean": 1.5,
        "xrt_mean": -3.8,        # retail/importers
        "duration_expected_days": 14,
    },
    StatementType.MILITARY: {
        "sp500_mean": -1.8,
        "sp500_std": 3.5,
        "vix_mean": 12.0,
        "oil_mean": 4.5,         # oil spikes on military threats
        "xle_mean": 3.8,
        "gld_mean": 1.5,
        "duration_expected_days": 30,
    },
    StatementType.TERRITORIAL: {
        "sp500_mean": -0.5,
        "sp500_std": 1.5,
        "vix_mean": 5.0,
        "duration_expected_days": 21,
    },
    StatementType.PERSONNEL: {
        "sp500_mean": -0.8,
        "sp500_std": 1.2,
        "vix_mean": 4.0,
        "gld_mean": 1.2,
        "duration_expected_days": 7,
    },
    StatementType.POLICY: {
        "sp500_mean": -0.5,
        "sp500_std": 1.0,
        "vix_mean": 3.0,
        "duration_expected_days": 10,
    },
}
```

## Prediction Formula

### Base Return by Type
```
predicted_return = TYPE_REACTION_MODEL[type]["sp500_mean"]
```

### Desensitization Adjustment
```
desensitization_multiplier = 0.85 ^ (nth_similar_threat - 1)

desensitized_return = predicted_return × desensitization_multiplier
```

| nth_similar | Multiplier | Example (-2.1%) |
|-------------|------------|-----------------|
| 1 | 100% | -2.1% |
| 2 | 85% | -1.79% |
| 3 | 72% | -1.51% |
| 4 | 61% | -1.28% |
| 5 | 52% | -1.09% |

### Confidence Interval
```
confidence_interval_68 = [predicted_return - std, predicted_return + std]
```

## Output Format

```json
{
  "statement_id": "TACO-011",
  "predicted_reaction": {
    "sp500_return": -1.8,
    "sp500_std": 3.5,
    "confidence_interval_68": [-5.3, 1.7],
    "vix_change": 12.0,
    "oil_return": 4.5,
    "target_asset_returns": {
      "USO": 4.5,
      "XLE": 3.8,
      "GLD": 1.5,
      "SPY": -1.8,
      "QQQ": -2.2
    }
  },
  "desensitization": {
    "nth_similar_threat": 1,
    "multiplier": 1.0,
    "desensitized_return": -1.8,
    "original_return": -1.8
  },
  "pain_point_analysis": {
    "pain_threshold_vix": 4.2,
    "pain_threshold_sp500": -0.67,
    "vix_spike_predicted": 12.0,
    "pain_point_triggered": true,
    "fast_taco_signal": true
  },
  "confidence": 0.72
}
```

## Pain Point Analysis

From pattern bible, pain thresholds that trigger fast TACO:
- VIX spike > 4.2% on threat day
- S&P drop < -0.67% on threat day

If BOTH thresholds exceeded → Fast TACO likely (3-7 days)
If NEITHER exceeded → Slow TACO (14-30 days)

## Key Rules

1. **Military threats → oil spikes**
   - USO: +4.5% typical for military threat
   - This distinguishes from trade threats

2. **Trade threats → retail/importers hurt**
   - XRT: -3.8% typical
   - CNY, MXN weaken vs USD

3. **Fed/personnel threats → gold, bitcoin up**
   - GLD: +1.2%, BTC: +2.1%
   - Dollar typically weakens

4. **Desensitization is per (type, target) pair**
   - China tariffs #3 still hurts China assets
   - But market overall is less shocked

5. **Confidence decreases with:**
   - High desensitization (nth_similar > 3)
   - Ambiguous statement language
   - No clear deadline

## Asset Priority by Type

| Type | Primary Trade | Secondary Trades |
|------|---------------|-----------------|
| TRADE_TARIFF | Short SPY/QQQ | Long GLD/TLT, Short XRT |
| MILITARY | Long USO/XLE | Long GLD, Short SPY |
| PERSONNEL | Long GLD | Short USD |
| TERRITORIAL | Short EEM | Long GLD |
| POLICY | Varies by policy | Long TLT if rate cut |
