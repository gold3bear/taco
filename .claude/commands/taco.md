# /taco — Full TACO Analysis Pipeline

Run the complete 6-agent TACO (Trump Always Chickens Out) investment analysis pipeline.

Analyzes historical Trump threat→backdown patterns and applies them to the current 2026 Iran conflict context to generate a final investment memo with actionable trade recommendations.

---

## Pre-flight

```bash
mkdir -p reports/charts data
```

Verify Python dependencies installed:
```bash
pip install yfinance pandas numpy scipy arch matplotlib --quiet
```

---

## Step 1: TACO Historian + Statistical Analyst
**Agent:** `agents/taco_historian.md` → `agents/statistical_analyst.md`

**Run:**
```bash
python scripts/build_taco_database.py
```
If yfinance unavailable: `python scripts/build_taco_database.py --seed-only`

```bash
python scripts/run_event_study.py
```

**Verify:**
- `data/taco_events.csv` contains ≥10 events
- `data/taco_pattern_bible.json` contains `laws` array with ≥3 laws

**Output:** `reports/01_taco_pattern_bible.md`

---

## Step 2: Current Context Analyst
**[REQUIRES: `data/taco_pattern_bible.json`]**
**Agent:** `agents/context_analyst.md`

**Run:**
```bash
python scripts/fetch_iran_context.py
```

**Verify:**
- `data/iran_context.json` has `adjusted_taco_probability` field
- `data/market_snapshot.json` has `assets` dict

**Output:** `reports/02_iran_scorecard.md`

---

## Step 3: Scenario Forecaster
**[REQUIRES: `data/iran_context.json`]**
**Agent:** `agents/scenario_forecaster.md`

**Run:**
```bash
python scripts/run_monte_carlo.py
```

**Verify:**
- `reports/03_scenarios.json` has 3 scenarios
- Probability sum ≈ 1.0

**Output:** `reports/03_scenarios.json`

---

## Step 4: Investment Strategist
**[REQUIRES: `reports/03_scenarios.json`]**
**Agent:** `agents/investment_strategist.md`

**Run:**
```bash
python scripts/calc_portfolio_strategy.py
```

**Verify:**
- `reports/04_trade_ideas.md` has ≥3 trade recommendations
- Compliance checklist passes (cash ≥20%)

**Output:** `reports/04_trade_ideas.md`

---

## Step 5: Critic & Risk Validator
**[REQUIRES: all prior reports]**
**Agent:** `agents/critic_validator.md`

No script to run. Agent reads all prior reports and outputs critique.

**Required outputs:**
- `reports/05_critic_review.md` with confidence score matrix
- "Approved for Final Memo: YES" statement

---

## Step 6: Generate Charts + Final Memo

**Generate charts:**
```bash
python scripts/generate_taco_charts.py
```

**Write Final Investment Memo:**
The orchestrator synthesizes all 5 reports into `reports/TACO_Investment_Memo.md`.

### Final Memo Template (≤800 words)

```markdown
# TACO Investment Intelligence Memo
**Date:** [today] | **Confidence:** [critic_overall_score]/100 | **Analyst Team:** 6 agents

---

## Executive Summary (50 words)
[Current situation: Trump threatened Iran on [date]. TACO probability: [X]%.
Top trade: [T1 description]. Key risk: [primary contradiction flag].]

---

## TACO Pattern Bible (80 words)
**Analyzed:** [N] historical TACO events (Jan 2025–Mar 2026)
**Historical backdown rate:** [X]%
**Key statistical laws:**
- LAW-1: [threat day AR]
- LAW-2: [backdown day CAR]
- LAW-3: [TACO rate]
- LAW-4: [pain point threshold]
- LAW-5: [GARCH persistence]

---

## 2026 Iran TACO Scorecard (80 words)
**Pattern match: [X]/100** | **Adjusted TACO probability: [X]%**

Current vs historical:
| Metric | Current | Historical Avg | Signal |
[4-5 row table]

**Key contradictions:** [list top 2 flags]

---

## Three Scenarios (200 words)

| Scenario | Probability | S&P 7d | S&P 30d | Oil 30d | BTC 7d | Timeline |
|----------|-------------|--------|---------|---------|--------|---------|
| Base TACO | [X]% | +[X]% | +[X]% | -[X]% | +[X]% | ~14 days |
| Bullish TACO | [X]% | +[X]% | +[X]% | -[X]% | +[X]% | ~7 days |
| Bearish War | [X]% | -[X]% | -[X]% | +[X]% | -[X]% | >30 days |

**Key triggers:**
- Fast TACO signal: VIX >32 OR S&P 5-day drawdown >5%
- War signal: Military assets deployed OR Hormuz closure
- Deal signal: Trump tweets "great deal" or "meeting scheduled"

---

## Top 3 Trade Ideas (200 words)

**T1: LONG QQQ** | Entry: $[X] | Target: $[X] (+[X]%) | Size: 3-5%
Stop: Military strike confirmed | Wtd. Sharpe: [X] | R/R: [X]:1

**T2: SHORT XLE (puts)** | Entry: Buy [X]% OTM puts | Premium: 2-3%
Stop: Defined (premium paid) | Best case: -[X]% oil → +[X]% put profit

**T3: LONG GLD (hedge)** | Entry: $[X] | Size: 2% (insurance)
Rationale: +[X]% in war case offsets equity losses

**Portfolio compliance:** ✓ All positions ≤10% | ✓ Cash ≥20% | ✓ Fundamental stops only

---

## Critical Risks (100 words)

1. **Iran ≠ Trade War:** Military TACO has lower base rate. All prior strong TACOs were economic.
2. **Oil >$85:** Reduces TACO probability from ~85% to ~55%. Energy inflation = domestic political cost.
3. **Hormuz Tail:** 8% probability of Hormuz closure → oil >$130, S&P -20%, XLE +30% (covers put losses).
4. **Israel Factor:** US-Israel alliance could lock Trump into military response regardless of market pain.

**Confidence: [overall_score]/100** | *Verify all L4-estimated data with real-time sources before trading.*

---

## Data Quality
| Source | Coverage | Tier |
|--------|---------|------|
| TACO event database | Jan 2025–Mar 2026 | L1-L3 (seed) + L4 (web) |
| Market prices | Last 30 days | L1 (yfinance) |
| Polymarket | Current | L1-L4 (API or estimated) |
| Trump/Iran intelligence | Current | L4-estimated |

*All L4-estimated data should be verified with real-time sources before executing trades.*
```

---

## Pipeline Status Checks

After each step, verify the required output exists before proceeding:
```python
import os
checks = [
    "data/taco_events.csv",
    "data/taco_pattern_bible.json",
    "data/iran_context.json",
    "reports/03_scenarios.json",
    "reports/04_trade_ideas.md",
    "reports/05_critic_review.md",
]
for f in checks:
    status = "✓" if os.path.exists(f) else "✗ MISSING"
    print(f"  {status} {f}")
```

---

## Timeout Rules
- Each agent: 8 minutes max
- Each script: 5 minutes max (kill and use fallback if exceeded)
- Total pipeline: ~30-40 minutes end-to-end

## On Failure
If any step fails: mark as `PARTIAL_DATA`, write what's available, continue to next step.
Never block the full pipeline on a single agent failure.
