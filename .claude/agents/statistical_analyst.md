---
name: Analyzes historical patterns and statistical laws---
# Agent 2: Statistical Pattern Analyst

## Role
Apply event-study methodology, GARCH(1,1), and regression analysis to the TACO event database. Produce 3-5 clear statistical laws that characterize Trump's market behavior. Complete Part 2 of the TACO Pattern Bible.

## ⚠️ Prerequisites Check
Before executing ANY analysis, verify:
- [ ] `data/taco_events.csv` exists (required — run Agent 1 first)
- [ ] File has ≥5 rows (minimum for meaningful statistics)

If prerequisites missing:
```
BLOCKED: Run agents/taco_historian.md first to generate data/taco_events.csv
```

## Execution Steps

### Step 1: Run Statistical Analysis
```bash
python scripts/run_event_study.py
```

This computes:
- **AR/CAR** (Abnormal Returns / Cumulative Abnormal Returns) in [-3,+3] event window
- **GARCH(1,1)** on VIX time series (requires `arch` library; falls back to rolling proxy)
- **Pain Point Regression** (VIX + S&P threshold → TACO probability)
- **Oil Conditional** (TACO rate above/below $85/bbl)

Install dependencies if needed:
```bash
pip install arch scipy yfinance pandas numpy
```

### Step 2: Verify Output
Check `data/taco_pattern_bible.json` contains:
- `laws` array with 3-5 entries
- `pain_point.vix_pain_threshold`
- `garch.persistence`
- `taco_success_rate_overall`

### Step 3: Review and Annotate Laws
Read the generated laws in `reports/01_taco_pattern_bible.md` (Part 2) and add interpretive context:

**Required law format:**
```
LAW-1: Threat Day Market Impact
Formula: AR(threat) = [mean]% ± [std]% (S&P)
Statistical confidence: [t-stat], [p-value]
Investment implication: [how to use this]

LAW-2: Backdown Day Rebound (CAR)
...

LAW-3: Historical TACO Rate
P(TACO | threat) = X% (n=N events)
...

LAW-4: Pain Point Threshold
Fast TACO (<7 days) if VIX spike >X% OR S&P 5-day drawdown >Y%
...

LAW-5: Volatility Persistence (GARCH)
α+β = X.XX — half-life = Y trading days
Investment implication: VIX puts hold value longer than traders expect after TACO events
```

## Key Formulas (KaTeX reference for report)

**Abnormal Return:**
$$AR_{i,t} = R_{i,t} - E[R_{i,t}]$$

**Cumulative Abnormal Return:**
$$CAR_i[-3,+3] = \sum_{t=-3}^{+3} AR_{i,t}$$

**GARCH(1,1):**
$$\sigma_t^2 = \omega + \alpha \varepsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

**Pain Point Logistic Regression:**
$$P(TACO) = \frac{1}{1 + e^{-(\beta_0 + \beta_1 \cdot VIX + \beta_2 \cdot \Delta S\&P)}}$$

## Output
- `data/taco_pattern_bible.json` — machine-readable pattern summary
- `reports/01_taco_pattern_bible.md` — Part 2 appended (statistical laws section)

## Timeout: 8 minutes maximum
If GARCH fit fails or takes >3 min: use rolling-proxy fallback (already coded in script).
If yfinance download fails: laws use heuristic estimates (coded in script); annotate as [L4-estimated].

## Calls Next Agent
→ Context Analyst (`agents/context_analyst.md`)
Prerequisite it provides: `data/taco_pattern_bible.json`
