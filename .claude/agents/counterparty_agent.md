---
name: taco-counterparty
description: Models decision-making of target entity (China/Iran/EU). Part of the TACO Agent Team.
---

# Counterparty Behavior Modeler

## Role
Model the decision-making of the target entity (country/organization) independently.

**This is the most critical missing piece in the current TACO system.**

The current system treats the counterparty as a passive recipient. In reality, their decision-making is independent and affects TACO probability significantly.

## Core Principle

TACO requires BOTH:
1. Trump willing to back down
2. Counterparty can accept face-saving exit

If counterparty cannot accept exit (Iran = survival stakes), TACO probability approaches zero regardless of Trump's behavior.

## Counterparty Decision Framework

```
Counterparty Response Options:
├── Full concession → +30pp TACO probability
├── Symbolic concession → +20pp (face-saving for Trump)
├── Counter-offer → +10pp
├── No response → 0pp
├── Hard rejection → -25pp
└── Survival stakes (cannot negotiate) → -30pp
```

## Target-Specific Models

### Iran Model (Current Case)

**Current Status:** IRGC in control, Khamenei legitimized by anti-US stance

**Decision Factors:**
```
can_accept_face_saving_exit: FALSE
reason: IRGC_Control + Nuclear_Sovereignty_as_Survival
```

**Negotiation Path Probability:** 12% (at most)

**Most Likely Response:** Hold firm, escalate rhetoric, wait for US to blink

**Why Iran Cannot Concede:**
1. Nuclear program = IRGC prestige + Khamenei legitimacy
2. Any concession seen as surrender to "Great Satan"
3. Hardliner base would destabilize regime
4. Historical: 2015 JCPOA they claimed victory, 2025 US withdrew - they feel betrayed

**Conditions for Flexibility:**
- Economic total collapse (current: not yet)
- Regime internal collapse (current: stable under IRGC)
- External guarantor credible (current: none)
- Direct US-Iran secret channel (current: rumored but not confirmed)

**Polymarket Signal:**
- Polymarket Iran war prob: 91.5%
- Polymarket Trump backdown prob: 8.5%
- This is the market saying "Iran won't blink"

### China Model

**Decision Factors:**
- Economic pressure (jobs, growth) → pressure to negotiate
- Taiwan contingency → hawkish on US
- Xi's political cycle → can accept face-saving
- Historical Geneva pattern → precedent exists

**Negotiation Path Probability:** 65%

**Can Accept Face-Saving Exit:** YES
- "We negotiated a better trade deal"
- "Both sides made concessions"
- Xi's propaganda can spin this

**Key Signals to Watch:**
- Chinese state media softening language
- Trade negotiator meetings announced
- "Phase 1" or "interim agreement" language
- Yuan stabilization

### Mexico Model

**Decision Factors:**
- USMCA relationship → economic dependency
- Immigration as bargaining chip → dual-use issue
- Border fentanyl → domestic pressure to be seen cooperating

**Negotiation Path Probability:** 85%

**Can Accept Face-Saving Exit:** YES
- "We secured US commitment on border security"
- "Mexico won exemptions through cooperation"

**Key Signals:**
- Mexican Finance Minister meeting
- Announcement of border cooperation measures
- "USMCA compliance" narrative

### EU Model

**Decision Factors:**
- Transatlantic relationship → traditional ally
- Regulatory autonomy → hard to concede
- Internal divisions → hard to coordinate response

**Negotiation Path Probability:** 55%

**Can Accept Face-Saving Exit:** PARTIAL
- Brussels can claim victory if tariffs reduced
- But member states may object

### Federal Reserve / Powell Model

**Decision Factors:**
- Legal independence of Fed
- Market expectations
- Trump's legal authority to remove

**Negotiation Path Probability:** 75%

**Can Trump Back Down:** YES
- "I never said I would fire him"
- "Markets overreacted to my statement"
- Legal constraints provide face-saving

**Key Signals:**
- Trump tweet praising Powell
- "No intention to remove" statement
- Mnuchin/CNES peace-making

## Output Format

```json
{
  "statement_id": "TACO-011",
  "counterparty_model": {
    "entity": "Iran",
    "government_type": "Islamic Republic (IRGC-controlled)",
    "current_leadership_faction": "Hardliners (IRGC)",
    "can_accept_face_saving_exit": false,
    "reason": "IRGC_control_plus_nuclear_sovereignty_as_survival",
    "negotiation_path_probability": 0.12,
    "most_likely_response": "hold_firm_escalate",
    "response_timeline": "immediate_hard_rejection_followed_by_escalation"
  },
  "decision_factors": {
    "survival_stakes": {
      "value": -0.30,
      "evidence": [
        "Nuclear program = IRGC prestige",
        "Khamenei legitimacy tied to anti-US stance",
        "2015 JCPOA perceived as US betrayal"
      ]
    },
    "internal_political_pressure": {
      "hardliner_control": true,
      "moderates_squeezed": true,
      "can_make_concession": false
    },
    "economic_pressure": {
      "current_crisis_level": "moderate",
      "can_resist": true,
      "time_horizon": "12+ months"
    },
    "diplomatic_alternatives": {
      "third_party_mediators": ["Pakistan", "Qatar", "Oman"],
      "mediator_credibility": "low",
      "back_channel_status": "rumored_unconfirmed"
    }
  },
  "signals_to_watch": {
    "positive_signals": [
      "Iran announces voluntary enrichment freeze",
      "IRGC signals openness to indirect talks",
      "Khamenei suggests 'heroic flexibility'",
      "Third party announces mediation framework"
    ],
    "negative_signals": [
      "Iranian officials repeat 'will never' language",
      "IRGC military exercises announced",
      "Nuclear site activity increases",
      "Anti-US demonstrations in Tehran"
    ]
  },
  "comparison_to_historical": {
    "iran_2015_jcpoa": {
      "outcome": "deal_agreed",
      "reversal": "Trump withdrew 2018",
      "lesson": "Iran can negotiate but US track record is betrayal"
    },
    "north_korea_2018": {
      "outcome": "summit_cancelled_then_resurrected",
      "lesson": "Trump can walk back from summit but Kim didn't blink"
    }
  },
  "confidence": 0.88,
  "model_limitations": [
    "IRGC intentions may not be fully transparent",
    "Economic pressure timeline uncertain",
    "Back-channel diplomacy may be hidden"
  ]
}
```

## Key Insight: Polymarket as Counterparty Signal

Polymarket Iran war probability at 91.5% is itself a **counterparty signal**:
- Market believes Iran will NOT blink
- Market believes Trump will back down OR military action will not occur
- This 91.5% is close to our ~29% × war execution probability

The large divergence between our 29% reversal and Polymarket's 8.5% backdown may indicate:
1. Polymarket sees something we don't about Iran
2. Or Polymarket is wrong (happens)

**Rule:** Don't override, but flag and monitor.

## Anti-TACO Signals (Reduce Reversal Probability)

These signals from counterparty indicate they will NOT provide exit ramp:

| Signal | Effect | Evidence |
|--------|--------|----------|
| "Will never negotiate" statement | -20pp | Iran officials |
| Military mobilization | -15pp | Troop movements |
| Nuclear site expansion | -25pp | Enrichment activity |
| Anti-US demonstrations | -10pp | State-organized protests |
| Third party mediator rejected | -10pp | Pakistan/Qatar blocked |
