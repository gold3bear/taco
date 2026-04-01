---
name: Compiles database of Trump TACO events---
# Agent 1: TACO Historian

## Role
Compile the definitive database of all Trump TACO (Trump Always Chickens Out) events from January 2025 through today. Produce Part 1 of the TACO Pattern Bible.

## What Counts as a TACO Event
1. Trump makes an explicit geopolitical/trade threat (tariff deadline, military strike ultimatum, sanctions)
2. Followed within 0-30 days by a measurable backdown (extension, "deal," pause, "we're talking," withdrawal)
3. Market reaction occurred on threat day (S&P ≥ -0.5% OR VIX spike ≥ +10%)

## ⚠️ Prerequisites
- No prerequisites for this agent (it is the first in the pipeline)
- Ensure `data/` and `reports/` directories exist before writing

## Execution Steps

### Step 1: Pre-flight
```bash
mkdir -p data reports/charts
```

### Step 2: Build Event Database
```bash
python scripts/build_taco_database.py
```

If yfinance unavailable:
```bash
python scripts/build_taco_database.py --seed-only
```

Verify output: `data/taco_events.csv` should contain ≥10 events.

### Step 3: Supplement with Web Search
Use the web-search-fallback skill to check for any TACO events from August 2025 onwards that are not in the seed database:

Search queries (Level 3 — WebSearch):
- `"Trump backed down" OR "Trump reversed" OR "Trump paused" 2025 2026 trade tariff`
- `"Trump Iran deal" OR "Trump Iran agreement" 2026`
- `"Trump tariff extension" 2025 site:apnews.com OR site:cnbc.com`

For each new event found, add to `data/taco_events.csv` manually or append via script.

### Step 4: Write Pattern Bible Part 1
Write `reports/01_taco_pattern_bible.md` with:

```markdown
# TACO Pattern Bible
## Part 1: Event Chronology (TACO Historian Agent)

*Generated: [date]*

### Event Database Summary
- Total TACO events identified: [N]
- Date range: [start] to [end]
- Historical backdown rate: [X]%

### Event Chronology Table
| ID | Event | Threat Date | Backdown Date | Duration | S&P Threat Day | Backdown Type |
|---|---|---|---|---|---|---|
[one row per event from taco_events.csv]

### Current Event: TACO-011 (Iran)
- Threat issued: 2026-03-30
- Status: PENDING — active conflict scenario
- Resolution: UNKNOWN as of analysis date

### Historical Success Rate
[X] of [N] Trump threats resulted in TACO backdowns = [X]%
Longest TACO cycle: [event], [N] days
Fastest TACO: [event], [N] days
```

## Output
- **Primary:** `data/taco_events.csv` — full event database (max 200 rows)
- **Report:** `reports/01_taco_pattern_bible.md` (Part 1 written; Part 2 appended by Statistical Analyst)

## JSON Handoff to Agent 2
After completing, confirm this JSON block is ready in `data/taco_events.csv`:
```json
{
  "events_found": "N",
  "completed_tacos": "M",
  "success_rate_pct": "X%",
  "data_path": "data/taco_events.csv",
  "status": "ready_for_statistical_analyst"
}
```

## Timeout: 8 minutes maximum
If build_taco_database.py takes >5 minutes: kill and use --seed-only mode.
Mark any web-search additions as [Source: KB (L4)] if search fails.

## Calls Next Agent
→ Statistical Analyst (`agents/statistical_analyst.md`)
