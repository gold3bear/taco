---
name: web-search-fallback
description: TACO system unified web search protocol. 4-level fallback: WebSearch → Brave/DuckDuckGo → Knowledge Base → Annotate Insufficient. All agents requiring web search MUST follow this protocol.
---

# Web Search 4-Level Fallback Protocol

All TACO agents must follow this protocol for web searches. No agent may define its own fallback logic.

---

## Fallback Order

```
Level 1: WebSearch tool (primary)
Level 2 (if L1 fails): Alternative query reformulation + retry
Level 3 (if L2 fails): Knowledge base fallback
Level 4: Annotate as "DATA INSUFFICIENT" and continue
```

**Timeout**: L1 + L2 combined must complete within 3 minutes. Escalate immediately on timeout.

---

## Level 1: WebSearch Tool

```
WebSearch("query terms site:apnews.com OR site:cnbc.com OR site:politico.com")
```

**Blocked sites (frequent 403)**: reuters.com · bloomberg.com · ft.com · wsj.com

Failure conditions (switch to Level 2):
- Returns 0 results
- HTTP 400 / 403 / 429 / 500
- Timeout >60 seconds
- Already retried once

---

## Level 2: Reformulated Query

Try alternative query terms and different sources:
```
WebSearch("Trump Iran [alternative terms] -site:reuters.com")
WebSearch("[event] date:[YYYY] market reaction")
```

Failure condition: still 0 results after 2 attempts → Level 3

---

## Level 3: Knowledge Base Fallback

Use training knowledge to fill the gap. Annotate every L3-sourced fact:

```
[Source: KB (L3), as of Aug 2025 cutoff — verify with real-time data]
```

For events after Aug 2025 cutoff, annotate:
```
[Source: KB (L4-estimated), post-cutoff event — HIGH UNCERTAINTY]
```

---

## Level 4: Annotate Insufficient

If no data available from any source:
```
[DATA INSUFFICIENT: [field_name] — skipped, marked for manual review]
```

Do NOT block the pipeline. Continue with available data.

---

## Source Tier Labels

| Source | Tier |
|--------|------|
| Official press releases / SEC filings | L1 |
| WebSearch confirmed news | L2 |
| WebSearch unverified / paywalled | L3 |
| Training knowledge base | L4 |
| Post-cutoff estimated | L4-estimated |
