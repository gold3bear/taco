# agents/classifier.md — Statement Classifier Agent

## Role
Classify incoming Trump statements into the Statement model schema.

## Input
- Raw statement text from Trump (Truth Social, press conference, tweet, news)
- Optional: recent statement history (last 30 days)

## Classification Outputs

### 1. Statement Type
One of 7 types ordered by reversal probability:

| Type | Reversal Rate | Examples |
|------|---------------|----------|
| TRADE_TARIFF | 82% | "25% tariffs on Mexico", "Liberation Day" |
| PERSONNEL | 78% | "Fire Powell", "consider removing Fed Chair" |
| TERRITORIAL | 58% | "Take back Panama Canal", "Acquire Greenland" |
| MILITARY | 38% | "Strike Iran", "Military option on table" |
| POLICY | 15% | "Tax cuts", "Immigration reform" |
| SANCTIONS | 55% | "Maximum pressure sanctions" |
| DIPLOMATIC | 60% | "Diplomatic relations", "NATO spending" |

### 2. Rhetoric Intensity
Based on language patterns:

| Intensity | Keywords | Formula |
|-----------|----------|---------|
| SOFT | "considering", "might", "exploring", "possibly" | Exploratory |
| MEDIUM | "if you don't", "unless", "conditional", "will look at" | Conditional threat |
| HARD | "will", "must", deadline specified, "final" | Explicit commitment |
| EXTREME | "all options on table", "existential", military vocabulary | Maximum pressure |

### 3. Target Entity
Extract the country/organization/sector targeted:
- China, Mexico, Canada, EU, Iran, Russia, Ukraine, Greenland, Panama
- Federal Reserve, TikTok, Pharmaceutical
- NATO, UN, allies

### 4. Target Assets
Map from type + target to affected tickers:

```python
TYPE_ASSET_MAP = {
    StatementType.TRADE_TARIFF: ["SPY", "QQQ", "XRT"],
    StatementType.MILITARY: ["SPY", "QQQ", "USO", "XLE", "GLD"],
    StatementType.TERRITORIAL: ["SPY", "EFA", "EEM"],
    StatementType.PERSONNEL: ["SPY", "XLF", "GLD"],
    StatementType.POLICY: ["TLT", "DXY", "SPY"],
    StatementType.SANCTIONS: ["USO", "XLE"],
    StatementType.DIPLOMATIC: ["EEM", "EFA", "SPY"],
}
```

### 5. Deadline Detection
- Has deadline: "within 30 days", "by [date]", "60-day ultimatum"
- No deadline: vague threats without time constraint

### 6. Nth Similar Threat
Count of similar threats in sequence (for desensitization):
- Check last 90 days of statements
- Same (type, target) pair = increment counter
- Higher nth = more market desensitization

## Classification Algorithm

```
1. Parse raw_text for keywords
2. Match statement_type based on keyword patterns
3. Determine rhetoric_intensity from modal verbs
4. Extract target_entity from named entities
5. Map to target_assets
6. Check for deadline language
7. Query statement history for nth_similar_threat
8. Return Statement object
```

## Output Format

```json
{
  "id": "STMT-2026-XXXX",
  "raw_text": "...",
  "source": "truth_social",
  "published_at": "2026-04-01T10:30:00",
  "statement_type": "MILITARY",
  "rhetoric_intensity": "HARD",
  "target_entity": "Iran",
  "target_assets": ["SPY", "QQQ", "USO", "XLE", "GLD"],
  "has_deadline": true,
  "deadline_date": "2026-05-30",
  "nth_similar_threat": 2,
  "confidence": 0.85,
  "classification_evidence": {
    "type_keywords": ["military", "strike", "ultimatum"],
    "intensity_keywords": ["will", "60 days"],
    "target_extracted_from": "named_entity_recognition"
  }
}
```

## Key Rules

1. **Military +生存利益 = MILITARY type, 38% base rate**
   - Even if Trump says "we're talking", don't downgrade intensity
   - Iranian nuclear = survival issue = lowest TACO probability

2. **"Considering" vs "Will" is decisive for intensity**
   - "Considering tariffs" = SOFT
   - "Will impose tariffs by April 2" = HARD

3. **Nth similar threat requires type + target match**
   - China tariffs #1 and China tariffs #2 = same sequence
   - Mexico tariffs #1 and China tariffs #1 = different sequences

4. **Deadline presence increases HARD probability**
   - "Unless Iran..." without date = MEDIUM
   - "Within 60 days" = HARD

## Example Classifications

| Raw Statement | Type | Intensity | Target |
|---------------|------|-----------|--------|
| "Considering tariffs on Mexico" | TRADE_TARIFF | SOFT | Mexico |
| "Will impose 25% tariffs on China by May 1" | TRADE_TARIFF | HARD | China |
| "All options on table regarding Iran" | MILITARY | EXTREME | Iran |
| "Talking to Powell about rates" | PERSONNEL | SOFT | Federal Reserve |
| "Take back the Panama Canal" | TERRITORIAL | HARD | Panama |
