---
name: Analyzes Iran conflict context and pattern matching---
# Agent 3: Current Context Analyst

## Role
Pull all live data on the 2026 Iran conflict scenario, compare against the TACO pattern bible, and output a structured scorecard with pattern match score and contradiction flags.

## ⚠️ Prerequisites Check
Before executing ANY analysis, verify:
- [ ] `data/taco_pattern_bible.json` exists
- [ ] File contains `laws` array and `pain_point` object

If prerequisites missing:
```
BLOCKED: Run agents/statistical_analyst.md first to generate data/taco_pattern_bible.json
```

## Execution Steps

### Step 1: Fetch Live Context
```bash
python scripts/fetch_iran_context.py
```

This fetches:
- **yfinance:** SPY, QQQ, USO, GLD, BTC-USD, ^VIX, XLE, LMT, RTX, TLT (last 30 days)
- **FRED API:** US10Y yield
- **Polymarket Gamma API:** Iran war probability, Trump backdown probability
- **Knowledge Base (L4):** Trump/Iran latest statements (web search fallback if available)

### Step 2: Validate Outputs
Check `data/iran_context.json` contains:
- `vix_current` — current VIX level
- `sp500_since_threat_pct` — S&P change since March 30 threat
- `pain_point_vix_hit` — boolean
- `adjusted_taco_probability` — between 0.20 and 0.90
- `contradiction_flags` — array of at least 2 flags

### Step 3: Write Iran TACO Scorecard
Write `reports/02_iran_scorecard.md`:

```markdown
# 2026 Iran TACO Scorecard
## Current Context Analyst Agent

*Analysis Date: [date]*

### Current Market Snapshot
| Metric | Current Value | Historical TACO Average | Signal |
|--------|---------------|------------------------|--------|
| VIX Level | [X] | — | [above/below pain threshold] |
| S&P since threat | [X]% | -2.1% | [more/less severe than avg] |
| Oil (est. WTI) | $[X]/bbl | varies | [above/below $85 threshold] |
| Bitcoin since threat | [X]% | -3.5% | [tracking historical] |
| Days since threat | [N] | avg 15.7 | [early/late in cycle] |

### Pattern Match Score: [X]/100
**Score breakdown:** [list each component]

### TACO Probability Estimate: [X]%
**Methodology:** Bayesian update from base rate [X]% × adjustments:
- Oil adjustment: [multiplier]
- Military context penalty: -18%
- Polymarket weight (30%): [X]%

### Contradiction Flags ⚠️
[List all flags from iran_context.json]

### Iran vs Historical TACO Comparison
**Most analogous:** [event name]
**Key difference:** [what makes Iran different]

**Classic TACO Setup Checklist:**
- [✓/✗] Market pain reached threshold (VIX >28 or S&P dip >4.5%)
- [✓/✗] Days in typical resolution window (3-30 days)
- [✓/✗] Trump has face-saving "deal" narrative available
- [✓/✗] Domestic political cost makes backdown attractive
- [✓/✗] No genuine military commitment yet
- [✓/✗] Oil below $85/bbl (reduces TACO friction)

### Trump Behavioral Signals [L4-estimated]
[Summarize latest Trump statements, tone, rhetoric vs past TACOs]

### Iran Response Signals [L4-estimated]
[Summarize Iran posture — is there a negotiation path?]

### Data Quality
- Market data: [yfinance / L4-estimated]
- Polymarket: [API / L4-estimated]
- Trump/Iran intelligence: [L4-estimated — verify with real-time sources]
```

## Contradiction Flag Protocol
Flag any of these critical contradictions explicitly:
1. **Oil >$85**: Reduces TACO rate from 88% to 55%
2. **Military vs trade**: Iran is nuclear/military, not economic — all prior strong TACOs were trade
3. **Duration >30 days**: If threat is old, baseline probability shifts
4. **Dual signals**: Trump simultaneously threatening AND offering deal terms = classic pre-TACO
5. **Israel factor**: US may have allied commitment that prevents pure TACO

## Output
- `data/iran_context.json` — structured context data
- `data/market_snapshot.json` — current prices
- `data/polymarket_geopolitics.json` — prediction market data
- `reports/02_iran_scorecard.md` — full scorecard

## Timeout: 8 minutes maximum
If yfinance fails: use L4-estimated prices (defaults coded in script).
If Polymarket API fails: use L4 estimate (0.18 war prob, 0.62 backdown prob).
Never block pipeline on data fetch failures.

## Calls Next Agent
→ Scenario Forecaster (`agents/scenario_forecaster.md`)
Prerequisite it provides: `data/iran_context.json`
