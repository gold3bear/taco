---
name: web-search-fallback
description: TACO system unified web search protocol. 5-level fallback: MCP Playwright (Google/X) → WebSearch → Brave/DuckDuckGo → Knowledge Base → Annotate Insufficient. All agents requiring web search MUST follow this protocol.
---

# Web Search 5-Level Fallback Protocol

All TACO agents must follow this protocol for web searches. No agent may define its own fallback logic.

---

## Fallback Order

```
Level 1: MCP Playwright (Google Search, X.com) — HIGHEST PRIORITY
Level 2: WebSearch tool (primary)
Level 3 (if L2 fails): Alternative query reformulation + retry
Level 4 (if L3 fails): Knowledge base fallback
Level 5: Annotate as "DATA INSUFFICIENT" and continue
```

**Timeout**: L1 + L2 combined must complete within 3 minutes. Escalate immediately on timeout.

---

## Level 1: MCP Playwright Browser Search (HIGHEST PRIORITY)

Use MCP Playwright to search Google and X.com directly. This bypasses API rate limits and captures real-time results.

### Google Search
```javascript
// Navigate to Google
await page.goto('https://www.google.com/search?q=Trump+Iran+threat+2026')

// Take snapshot
await page.snapshot()

// Or search for specific news
await page.goto('https://www.google.com/search?q=site:x.com+Trump+Iran&tbm=nws')
```

### X.com (Twitter) Search
```javascript
// Search X.com for Trump Iran tweets
await page.goto('https://x.com/search?q=Trump+Iran+from:realDonaldTrump&src=typed_query')

// Or general Iran news
await page.goto('https://x.com/search?q=Iran+nuclear+deal+trump&f=live')
```

### MCP Playwright Commands
```javascript
// Basic navigation
browser_navigate(url: string)

// Take screenshot
browser_take_screenshot()

// Take accessibility snapshot (for extracting text)
browser_snapshot(depth?: number)

// Extract console messages
browser_console_messages(level: 'error' | 'warning' | 'info' | 'debug')

// Wait for content
browser_wait_for(text: string, time?: number)

// Evaluate JS
browser_evaluate(function: string)
```

### When to Use Level 1
- **Google News**: For breaking news and current events
- **X.com**: For Trump statements, official reactions
- **Polymarket**: For prediction market data
- **FRED/BLS**: For official economic data

Failure conditions (switch to Level 2):
- Page returns 403/blocked
- No relevant content found
- Login wall encountered
- Already attempted once

---

## Level 2: WebSearch Tool

```
WebSearch("query terms site:apnews.com OR site:cnbc.com OR site:politico.com")
```

**Blocked sites (frequent 403)**: reuters.com · bloomberg.com · ft.com · wsj.com

Failure conditions (switch to Level 3):
- Returns 0 results
- HTTP 400 / 403 / 429 / 500
- Timeout >60 seconds
- Already retried once

---

## Level 3: Reformulated Query

Try alternative query terms and different sources:
```
WebSearch("Trump Iran [alternative terms] -site:reuters.com")
WebSearch("[event] date:[YYYY] market reaction")
```

Failure condition: still 0 results after 2 attempts → Level 4

---

## Level 4: Knowledge Base Fallback

Use training knowledge to fill the gap. Annotate every L4-sourced fact:

```
[Source: KB (L4), verify with real-time data]
```

For events after knowledge cutoff, annotate:
```
[Source: KB (L4-estimated), verify with live sources]
```

---

## Level 5: Annotate Insufficient

If no data available from any source:
```
[DATA INSUFFICIENT: [field_name] — skipped, marked for manual review]
```

Do NOT block the pipeline. Continue with available data.

---

## Source Tier Labels

| Source | Tier |
|--------|------|
| MCP Playwright (real-time) | L1 |
| Official press releases / SEC filings | L1 |
| WebSearch confirmed news | L2 |
| WebSearch unverified / paywalled | L3 |
| Training knowledge base | L4 |
| Post-cutoff estimated | L4-estimated |

---

## Quick Reference

| Task | Recommended Source |
|------|-------------------|
| Trump latest statements | X.com search via MCP Playwright |
| Breaking news | Google News via MCP Playwright |
| Iran conflict status | Polymarket via MCP Playwright |
| Economic data | FRED via direct API |
| Market prices | yfinance (L1) |
| Prediction markets | Polymarket API |
| Historical context | WebSearch |

---

## Example Flow: Trump Iran Statement

```javascript
// Level 1: MCP Playwright
await page.goto('https://x.com/search?q=Trump+Iran+from:realDonaldTrump&f=live')
const snapshot = await page.snapshot()
// If blocked or empty:

// Level 2: WebSearch
WebSearch("Trump Iran statement April 2026 site:x.com OR site:truthsocial.com")
// If 0 results:

// Level 3: Alternative query
WebSearch("Trump Iran ultimatum 2026 reaction")
// If still 0:

// Level 4: KB fallback + annotation
[Source: KB (L4-estimated), verify with live data]
```
