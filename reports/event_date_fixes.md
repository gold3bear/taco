# TACO Event Date Fix Report
*Generated: 2026-03-31 15:35*

## Duplicate threat_date Detected
- `2025-02-01`: ['TACO-004', 'TACO-006']
- `2025-04-09`: ['TACO-009', 'TACO-010']

## Proposed Corrections

-   FIX TACO-009: threat 2025-04-09→2025-04-08, backdown 2025-07-12→2025-04-09 | Apr 9 was tariff PAUSE (backdown) not threat. Apr 8 EU exclusion was real threat (VIX 52, S&P -1.6%).
-   FIX TACO-010: threat 2025-04-09→2025-05-01, backdown 2025-05-12→2025-05-12 | China 145% tariff threat was Apr 2Liberation Day. May 1 = Geneva talks collapse/re-escalation.

## Verification Against Market Data
(Script verified market data around key dates)

## Applied Changes
- Modified: build_taco_database.py
- Events deleted: 0
- Events corrected: 2