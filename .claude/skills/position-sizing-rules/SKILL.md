---
name: position-sizing-rules
description: TACO system position sizing rules. Investment Strategist must reference this skill. All allocation strategies must pass this checklist before output.
---

# Position Sizing Rules (Unified)

This skill is the single authoritative source for position sizing. All trade recommendations must comply.

---

## Hard Rules (Never Violate)

| Rule | Constraint | Notes |
|------|-----------|-------|
| **Rule 1: Single Position Cap** | Any single asset total ≤ **10%** | Includes all add-on buys |
| **Rule 2: Cash Reserve** | Cash balance after entry ≥ **20%** | Reserve for error correction |
| **Rule 3: Single Trade Cap** | Any single entry ≤ **5%** (pilot position) | First entry never exceeds 5% |

---

## Compliant Position Format

```
Initial entry: 3-5% ($XXX-XXX range, pilot position)
First add-on: +2-3% when [trigger condition met]
Second add-on: +2-3% if conditions continue (total ≤ 10%)
Total cap: 10% (never exceed under any scenario)
Cash constraint: ≥20% cash remaining after all entries

Stop-loss: Fundamental (exit if [core assumption] invalidated), NOT price-based
```

---

## Pre-Output Checklist

```
□ Any single entry ≤ 5%?
□ All tranches combined ≤ 10%?
□ Cash balance ≥ 20% after entries?
□ Stop-loss is fundamental trigger, not price level?
□ Risk/reward ratio ≥ 2:1?
```

All boxes checked before outputting trade strategy. Rewrite if any fail.

---

## Risk/Reward Requirement

```
Current price: $[price]
Upside target: $[target] → +X%
Downside (bear case): $[bear_price] → -X%
Risk/Reward ratio: upside / |downside| = X:1

Decision:
  > 2:1 → acceptable entry
  1-2:1 → cautious, wait for better entry
  < 1:1 → do NOT enter regardless of conviction
```

---

## Fundamental Stop-Loss Format

```
Exit signals (any one triggers consideration of reduce/exit):
1. [Core assumption] fails for 2 consecutive data points
2. Structural risk flagged by Critic Agent actually materializes
3. Scenario probability shifts >20pp toward No-TACO (war escalation)
```
