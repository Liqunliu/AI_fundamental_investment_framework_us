---
description: "Standalone Valuation Analysis — DCF, DDM, multiples, and Graham valuation"
argument-hint: "TICKER [--source bloomberg|yfinance]"
---

# Standalone Valuation Analysis

Run a multi-method valuation (DCF, DDM, comparable multiples, Graham Number) on a US stock.
Uses data_pack.md as primary input. If a qualitative_report.md exists (from `/business-analysis`),
applies qualitative adjustments to refine estimates.

## Input Parsing

1. Extract single ticker symbol (1-5 uppercase letters)
2. Extract `--source` flag if present (default: `yfinance`)

## Execution Pipeline

**Task 1: Data Collection** (Budget: 3 min, skip if recent files exist)

```bash
# Collect data (skip if output/{TICKER}/data_pack.md exists and < 7 days old):
python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md

# Factor inputs (skip if output/{TICKER}/{TICKER}_factor_inputs.md exists and < 7 days old):
python3 scripts/calculate_factor_inputs.py --input output/{TICKER}/data_pack.md --code {TICKER}
```

**Task 2: Valuation Analysis** (Budget: 8 min)

1. Load the valuation framework:
   - `prompts/valuation/phase2_valuation.md` (execution instructions)

2. Read data files:
   - `output/{TICKER}/data_pack.md` (required)
   - `output/{TICKER}/{TICKER}_factor_inputs.md` (if exists)
   - `output/{TICKER}/qualitative_report.md` (if exists — for qualitative adjustments)
   - `output/{TICKER}/data_pack_footnotes.md` (if exists)

3. Execute valuation:
   - Company classification (Growth / Value / Hybrid / Distressed)
   - WACC estimation
   - DCF with sensitivity table
   - DDM with sensitivity table (if dividend-paying)
   - Comparable multiples analysis
   - Graham Number (if applicable)
   - Cross-validation of all methods
   - Qualitative adjustments (if qualitative_report.md available)

4. Write output to `output/{TICKER}/{TICKER}_valuation_report.md`

**Task 3: Output Delivery**

Present summary:

| Metric | Value |
|--------|-------|
| Classification | {type} |
| Valuation Range | ${low} — ${high} |
| Central Estimate | ${value} |
| Current Price | ${price} |
| Implied Upside/Downside | {X}% |
| Confidence | [HIGH/MODERATE/LOW] |

Suggest next steps:
- If attractive → `/us-qy {TICKER}` for full Quality Yield analysis
- If deep value → `/us-cigar {TICKER}` for Cigar Butt analysis

## Key Constraints

- **8-minute task limit** for valuation analysis
- **All amounts in millions USD** — convert if reporting currency differs
- **Currency validation** — check §1 for reporting currency, apply FX conversion if needed
- **Conservative bias** — use lower-bound assumptions when uncertain
- **Single ticker per invocation**

## Checkpoint & Resume

| If this file exists... | Skip to... |
|----------------------|-----------|
| `data_pack.md` (< 7 days) | Task 2 (skip data collection) |
| `{TICKER}_factor_inputs.md` (< 7 days) | Task 2 (skip factor calc) |
| `{TICKER}_valuation_report.md` (< 24h) | Task 3 (skip analysis, present results) |

<HARD-GATE>
Do NOT modify any scripts or code files. Only execute existing scripts and write analysis output files.
If a script needs fixing, report the issue to the user.
</HARD-GATE>
