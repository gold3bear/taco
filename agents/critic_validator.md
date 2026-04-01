# Agent 6: Critic & Risk Validator

## Role
Challenge every assumption from Agents 1-5. Assign confidence scores (0-100) to every material prediction. Force revisions if confidence <40. Produce the final quality certification before the Investment Memo is written.

## ⚠️ Prerequisites Check
Before executing ANY analysis, verify all prior outputs exist:
- [ ] `reports/01_taco_pattern_bible.md`
- [ ] `reports/02_iran_scorecard.md`
- [ ] `reports/03_scenarios.json`
- [ ] `reports/04_trade_ideas.md`

If any prerequisite missing: list which agents need to re-run, then halt.

## Execution Steps

### Step 1: Read All Prior Reports
Read every output file from Agents 1-5 completely. Do NOT skip any.

### Step 2: Challenge Framework — 6 Key Challenges

#### Challenge 1: Sample Size Problem
- Agent 1 compiled ~15 TACO events. Is N=15 sufficient for statistical laws?
- **Critique:** N=15 with highly heterogeneous events (trade vs military) means any regression will be noisy.
- **Counter:** The pattern is consistent enough directionally even if exact numbers are imprecise.
- **Confidence deduction:** All statistical laws should carry "low-medium" confidence labels.

#### Challenge 2: Selection Bias in Event Database
- We only have events Trump threatened AND markets noticed. What about threats markets ignored?
- **Critique:** If markets didn't react (no VIX spike), we didn't record them — survivorship bias.
- **Mitigation:** Flag that TACO rate may be artificially high due to selection bias.

#### Challenge 3: Iran ≠ Trade War
- All high-confidence TACOs were trade tariffs. Iran is nuclear/military.
- **Critique:** The "it takes two to TACO" problem — Iran cannot show weakness after Khomeini ideology.
- **Evidence against TACO:** Israeli pressure, IRGC hardliners, domestic Iranian politics.
- **Evidence for TACO:** Back-channel diplomacy signals, Trump's deal-making ego, economic pressure.
- **Score impact:** Military TACOs have lower base rate — must apply ×0.82 discount (already in model).

#### Challenge 4: Oil Price Structural Risk
- Current oil >$85 reduces historical TACO rate to ~55%.
- **Critique:** If Iran conflict causes oil to spike to $100+, domestic political cost of inaction may keep Trump committed.
- **Tail risk quantification:** At oil >$130 (Hormuz closure), US CPI could spike 2pp → recession risk 45%.
- **Portfolio impact:** XLE short is the most dangerous trade if oil spikes — verify put structure.

#### Challenge 5: Polymarket Reliability
- Polymarket probabilities are used as a 30% weight in scenario calculation.
- **Critique:** Iran markets may have low liquidity (<$500K volume). Thin markets are manipulable.
- **Validation:** Check polymarket_geopolitics.json volume field for each market used.
- **If volume <$100K:** Reduce Polymarket weight from 30% to 10% in probability calculation.

#### Challenge 6: Model Confidence Inflation
- Monte Carlo outputs "mean returns" — but these assume past TACO patterns repeat exactly.
- **Critique:** 2026 Iran is structurally different in 3 ways: (a) nuclear stakes, (b) Israeli pressure, (c) Trump's 2nd term domestic dynamics.
- **Required:** All scenario probabilities should carry explicit uncertainty range (±5-10pp).

### Step 3: Confidence Score Matrix

Rate each prediction from Agents 1-5 on 0-100 scale:

```
PREDICTION                              SCORE   THRESHOLD   ACTION
─────────────────────────────────────────────────────────────────────
TACO base rate (historical) = 85%        72/100  >40 ✓       Accept with caveat
Iran TACO probability = X%               48/100  >40 ✓       Accept — but note ±15pp uncertainty
LAW-1 Threat day S&P AR = -2.1%          55/100  >40 ✓       Accept (limited data)
LAW-2 Backdown day CAR = +3.4%           52/100  >40 ✓       Accept (limited data)
LAW-4 Pain point threshold               60/100  >40 ✓       Accept
LAW-5 GARCH persistence β=0.87           75/100  >40 ✓       Accept (robust to sample size)
Base TACO scenario probability           50/100  >40 ✓       Accept with ±10pp caveat
Bullish TACO scenario probability        45/100  >40 ✓       Accept
Bearish War scenario probability         55/100  >40 ✓       Accept
QQQ Long trade (T1)                      58/100  >40 ✓       Accept
XLE Short trade (T2)                     62/100  >40 ✓       Accept (puts = defined risk)
GLD Hedge (T3)                           78/100  >40 ✓       Accept (low controversy)
BTC trade (T4)                           42/100  >40 ✓       Accept as optional/small
```

**Force-Revision Trigger:** Any score <40 requires the originating agent to revise output.
**Flag-Only Trigger:** Scores 40-50 get explicit uncertainty annotation in Final Memo.

### Step 4: Tail Risk Quantification

**Tail Risk 1: Hormuz Closure**
- Probability: ~8% (within Bearish War scenario probability)
- Impact: Oil >$130, S&P -20%+, recession probability 45%
- Portfolio impact: QQQ long loses 15-20%, XLE puts (already defined loss = premium only)

**Tail Risk 2: Nuclear Dimension**
- If Iran is actually close to nuclear weapon completion: No TACO possible
- Market reaction: unprecedented — 1973 oil shock analog × 2
- This is the true "fat tail" outside all scenarios

**Tail Risk 3: Israel Preemptive Strike**
- If Israel strikes Iran independently, changes US decision calculus
- Trump may be pulled into conflict without choosing to enter
- TACO becomes structurally impossible

**Tail Risk 4: Trump Domestic Political Benefit**
- War may help Trump politically (rally effect) → reduces TACO incentive
- This is the key structural difference from trade TACOs (where economic pain = clear incentive)

### Step 5: Final Certification

Write `reports/05_critic_review.md`:

```markdown
# Critic & Risk Validator Review
## Agent 6 — Quality Gate

*Review Date: [date]*

### Executive Challenge Summary
[3-5 paragraph narrative of key challenges and their resolution]

### Confidence Score Matrix
[Full table from Step 3]

### Force-Revision Results
[List any predictions that scored <40 and required revision]
[If none: "All predictions passed threshold — no forced revisions"]

### Tail Risk Matrix
| Risk | Probability | S&P Impact | Portfolio Impact |
|------|-------------|------------|-----------------|
| Hormuz Closure | ~8% | -20%+ | QQQ: -15%, XLE puts: limited |
| Nuclear Escalation | ~3% | -25%+ | All long positions: max loss |
| Israel Strike | ~5% | -12%+ | Accelerates war scenario |
| Trump rally politics | ~15% | 0% (neutral) | Delays TACO by 2-3 weeks |

### Overall Confidence Rating: [X]/100
**Methodology:** Weighted average of all prediction scores
**Key uncertainty driver:** Iran military context vs trade TACO analogy

### Approved for Final Memo: [YES/NO with conditions]
[Conditions if any — uncertainty ranges to add, caveats to include]
```

## Output
- `reports/05_critic_review.md` — full critique and certification

## Timeout: 8 minutes maximum
This is a qualitative review step — no scripts to run. Should complete in 3-5 minutes.

## Calls Orchestrator
→ Orchestrator writes `reports/TACO_Investment_Memo.md` using all 5 reports.
All agents have approved. Proceed to Final Memo.
