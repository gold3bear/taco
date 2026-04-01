# Agent 4: Scenario Forecaster

## Role
Build 3 probabilistic scenarios (Base TACO / Bullish TACO / Bearish No-TACO) using Monte Carlo simulation and Bayesian probability updating. Deliver precise asset-level forecasts for 7-day and 30-day horizons.

## ⚠️ Prerequisites Check
Before executing ANY analysis, verify:
- [ ] `data/taco_pattern_bible.json` exists
- [ ] `data/iran_context.json` exists — contains `adjusted_taco_probability`

If prerequisites missing:
```
BLOCKED: Run agents/context_analyst.md first to generate data/iran_context.json
```

## Execution Steps

### Step 1: Run Monte Carlo
```bash
python scripts/run_monte_carlo.py
```

10,000 simulation paths per scenario. Student-t (df=4) fat tails for war scenario.

### Step 2: Review Probability Split
Check `reports/03_scenarios.json`:
- 3 scenarios must sum to 1.0 (±0.001)
- Base TACO should be largest probability
- Bearish War should be lowest (unless pattern match score <40)

### Step 3: Write Scenario Narrative
Enrich `reports/03_scenarios.json` context with qualitative narrative for each scenario.

Scenario definitions:

#### Scenario A: Base TACO (most likely)
- **Trigger:** Trump backs down within 14 days
- **Mechanism:** S&P drops >5% total OR oil surges hurt consumer sentiment → Trump offers "great deal"
- **Precedent:** Liberation Day 90-day pause (7 days), China Geneva truce (33 days)
- **S&P reaction:** +3-6% on announcement day, +5-10% over 30 days
- **Oil reaction:** -8% to -15% as war premium evaporates
- **Key watch signal:** Trump tweets "progress," "meeting soon," or uses word "deal"

#### Scenario B: Bullish TACO (fast resolution)
- **Trigger:** Market pain exceeds VIX >32 threshold within 7 days → rapid capitulation
- **Mechanism:** Liberation Day playbook — VIX spike forces rapid pause announcement
- **S&P reaction:** +5-9% on Day 7, potentially strongest single-day gain of 2026
- **Oil reaction:** -10% to -18% (sharp unwind of geopolitical premium)
- **Key watch signal:** VIX spike intraday >32, S&P futures -3%+ overnight

#### Scenario C: Bearish No-TACO (war / military escalation)
- **Trigger:** US conducts airstrikes OR Iran closes Strait of Hormuz
- **Mechanism:** TACO failure — military/domestic political commitment too deep to reverse
- **S&P reaction:** -8% to -18% over 30 days (depends on Hormuz severity)
- **Oil reaction:** +25% to +50% (Hormuz closure = 20% of global oil supply)
- **Tail risk:** Oil >$130/bbl → US recession probability rises to 45%
- **Key watch signal:** USO +15% in single day, LMT/RTX surge >10%, TLT falls

### Step 4: Scenario Table
Generate this table for the final memo:

| Metric | Base TACO | Bullish TACO | Bearish War |
|--------|-----------|--------------|-------------|
| Probability | [X]% | [X]% | [X]% |
| Timeline | ~14 days | ~7 days | >30 days |
| S&P 7d | +[X]% | +[X]% | -[X]% |
| S&P 30d | +[X]% | +[X]% | -[X]% |
| Oil 7d | -[X]% | -[X]% | +[X]% |
| Gold 30d | -[X]% | -[X]% | +[X]% |
| BTC 7d | +[X]% | +[X]% | -[X]% |
| Key trigger | Market pain | VIX >32 | Military action |

## Bayesian Update Formula

$$P(TACO) = P_{base} \times \alpha_{oil} \times \alpha_{military} \times (0.7 + 0.3 \times P_{polymarket})$$

Where:
- $P_{base}$ = historical TACO success rate (from pattern bible)
- $\alpha_{oil}$ = 0.625 if oil >$85/bbl, else 1.0
- $\alpha_{military}$ = 0.82 (military context discount)
- $P_{polymarket}$ = Polymarket backdown probability

## Output
- `reports/03_scenarios.json` — full Monte Carlo results with confidence intervals

## Timeout: 8 minutes maximum
10,000 paths × 3 scenarios completes in <30 seconds on any modern CPU.
If numpy fails: reduce to 1,000 paths (acceptable for qualitative analysis).

## Calls Next Agent
→ Investment Strategist (`agents/investment_strategist.md`)
Prerequisite it provides: `reports/03_scenarios.json`
