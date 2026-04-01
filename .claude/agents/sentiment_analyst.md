---
name: Analyzes rhetorical tone, escalation/de-escalation signals---
# agents/sentiment_analyst.md — Sentiment & Context Analyst Agent

## Role
Analyze rhetorical tone, escalation/de-escalation signals, media framing, and narrative context.

This agent fills the gap in the current TACO system which treats statements as isolated events rather than part of an ongoing narrative.

## Four Analysis Dimensions

### Dimension 1: Escalation Vocabulary

Track word families to measure aggression level:

| Word Family | Examples | Score Impact |
|-------------|----------|-------------|
| Military action | "surgical strike", "decimate", "obliterate", "wipe out" | +0.3 escalation |
| Economic destruction | "total destruction", "maximum pressure", "crush" | +0.2 escalation |
| Deadline language | "within days", "by [date]", "final" | +0.2 escalation |
| Existential framing | "existential threat", "survival", "catastrophic" | +0.3 escalation |
| Annexation | "take back", "reclaim", "belong to us" | +0.2 escalation |

### Dimension 2: De-escalation Vocabulary

Track retreat language:

| Word Family | Examples | Score Impact |
|-------------|----------|-------------|
| Negotiation | "talking", "negotiating", "deal", "progress" | +0.3 de-escalation |
| Face-saving | "both sides", "win-win", "mutual respect" | +0.2 de-escalation |
| Delay/Extension | "pause", "extend", "more time", "reprieve" | +0.2 de-escalation |
| Victory claim | "great progress", "they called me", "won" | +0.4 de-escalation |
| Third party | "many countries asking", "others agree" | +0.1 de-escalation |

### Dimension 3: Narrative Frame

Media/narrative context affects TACO execution:

| Frame | Description | TACO Ease Impact |
|-------|-------------|------------------|
| War hawk dominant | Media emphasizes military options | HARDER to TACO |
| Diplomatic solution | Media shows negotiation path | EASIER to TACO |
| Economic pain | Media focuses on market/economic damage | EASIER to TACO |
| Election year | Framing in electoral context | EASIER to TACO |
| Strongman | Framing as strength vs weakness | HARDER to TACO |

### Dimension 4: Face-Saving Exit Availability

Trump needs a "victory narrative" to exit. Analyze if one exists:

```
Can Trump claim victory if he backs down?
├── Yes: Clear path to TACO
│   ├── "They agreed to negotiate" → TACO likely
│   ├── "We got a better deal" → TACO likely
│   └── "Other countries will compensate" → TACO likely
│
└── No: TACO very difficult
    ├── Counterparty survival stakes (Iran nuclear)
    ├── Hardline media (Fox News calls it weakness)
    ├── Election far enough away (no urgency)
    └── Precipitating event (attack already happened)
```

## Signal Outputs

```json
{
  "statement_id": "TACO-011",
  "sentiment_analysis": {
    "escalation_score": 0.75,
    "de_escalation_score": 0.10,
    "net_sentiment": "strongly_escalating",
    "narrative_frame": "military_conflict",
    "face_save_available": false,
    "face_save_path": null,
    "media_ecosystem": {
      "fox_news_tone": "war_hawk",
      "msnbc_tone": "critical",
      "social_media_momentum": "pro_escalation"
    }
  },
  "key_phrases_detected": [
    "military option on the table",
    "existential threat",
    "60 days ultimatum"
  ],
  "escalation_signals": [
    "military_vocabulary_detected",
    "deadline_ultimatum_detected",
    "existential_framing_detected"
  ],
  "de_escalation_signals": [],
  "face_save_analysis": {
    "available": false,
    "reason": "Iran nuclear program is Khamenei/IRGC survival issue - cannot accept face-saving exit",
    "required_elements": [
      "Iran publicly freezes enrichment (they won't)",
      "US saves face by calling it 'pause' (but 60-day deadline hard to walk back)"
    ]
  },
  "confidence": 0.82
}
```

## Key Metrics

### Escalation/De-escalation Scores
- 0.0 to 1.0 scale
- 0.5 = neutral
- Combined produce net_sentiment

### Narrative Reversal Ease
```
narrative_reversal_ease = de_escalation_score × face_save_available × media_coverage_factor
```

| Ease Score | Interpretation |
|-------------|----------------|
| > 0.6 | Easy reversal - narrative supports it |
| 0.3 - 0.6 | Moderate - requires face-saving element |
| < 0.3 | Difficult - no clear narrative path to reversal |

## Iran Case Analysis (Current Event)

### Escalation Signals Present
- "Military option on table"
- "Existential threat" (to Israel/US)
- "60 days ultimatum" (hard deadline)
- IRGC/ Khamenei framed as irrevocably hostile

### De-escalation Signals Absent
- No "great progress" language
- No "they called me" signals
- No negotiation mention
- No third-party mediator announced

### Face-Save Analysis
**Available: NO**

Why:
1. Iran nuclear program = IRGC + Supreme Leader legitimacy issue
2. Cannot freeze enrichment without appearing to surrender
3. Even "pause" language would be seen as US capitulation
4. Khamenei's base (hardliners) would erupt if negotiate

**Required but unavailable elements:**
- Iranian public concession (won't happen)
- US claims victory while giving nothing (hard with 60-day deadline)
- Third party credible enough (Pakistan/Qatar don't have leverage)

### Conclusion
```
face_save_available: false
narrative_reversal_ease: 0.05 (essentially zero)
```

This confirms Five-Factor Model's Factor 3 adjustment of -0.30 for survival stakes.

## Historical Pattern Recognition

Track Trump's escalation/de-escalation patterns:

| Pattern | Description | Predictor |
|---------|-------------|-----------|
| N-th threat desensitization | Markets ignore repeated threats | Use nth_similar |
| Deadline proximity | Escalation near deadline | Day 50-60 of 60-day = peak |
| Media cycle | News cycle affects attention | Weekend发布 = more volatility |
| Rally effect | Pro-Trump rallies increase hawkishness | Sentiment spikes after rallies |
