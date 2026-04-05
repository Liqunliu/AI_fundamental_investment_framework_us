---
description: "Standalone Qualitative Business Analysis — Assess business model, moat, management, and environment"
argument-hint: "TICKER [--source bloomberg|yfinance]"
---

# Standalone Qualitative Business Analysis

Analyze a company's business quality using the shared 6-dimension qualitative framework (D1-D6).
Produces a standalone qualitative report that can also serve as input to strategy-specific analyses
(Quality Yield, Cigar, Cyclical).

## Input Parsing

1. Extract single ticker symbol (1-5 uppercase letters)
2. Extract `--source` flag if present (default: `yfinance`)

## Execution Pipeline

**Task 1: Data Collection** (Budget: 5 min)

> ```bash
> # yfinance (default, handles SSL internally):
> python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md
>
> # Bloomberg:
> python3 scripts/bloomberg_collector.py --security "{TICKER} US Equity" --output output/{TICKER}/data_pack.md
> ```

Output: `output/{TICKER}/data_pack.md`

**Skip data collection if**: `output/{TICKER}/data_pack.md` already exists and was created
within the last 7 days. Inform the user that existing data is being reused.

**Task 2: Qualitative Assessment** (Budget: 8 min)

1. Load the qualitative framework:
   - `prompts/shared/qualitative/qualitative_assessment.md` (main framework)
   - `prompts/shared/qualitative/references/framework_guide.md` (moat definitions)
   - `prompts/shared/qualitative/references/market_rules_us.md` (US-specific rules)
   - `prompts/shared/qualitative/references/judgment_examples.md` (calibration examples)
   - `prompts/shared/qualitative/references/output_schema.md` (output format)

2. Read `output/{TICKER}/data_pack.md`

3. Execute the full qualitative assessment:
   - Pre-Analysis: Data Validation & Calibration
   - D1: Business Model & Capital Structure
   - D2: Competitive Advantage & Moat
   - D3: External Environment (Cyclicality + Regulatory)
   - D4: Management & Governance
   - D5: MD&A Interpretation
   - D6: Complex Structure (conditional)

4. Write output to `output/{TICKER}/qualitative_report.md`

**Task 3: Output Delivery**

Present summary table to user:

| Dimension | Rating | Key Finding |
|-----------|--------|-------------|
| D1: Business Model | [type] | [one sentence] |
| D2: Moat | [WIDE/NARROW/NONE] | [one sentence] |
| D3: Environment | [cyclicality] + [regulatory] | [one sentence] |
| D4: Management | [rating] | [one sentence] |
| D5: MD&A | [credibility] | [one sentence] |
| D6: Structure | [applicable/N/A] | [one sentence] |

**Overall Quality**: [A/B/C/D]
**Full report**: `output/{TICKER}/qualitative_report.md`

Suggest next steps based on results:
- Quality A/B → `/us-qy {TICKER}` for full Quality Yield analysis
- Capital-hungry + cyclical → `/us-cycle {TICKER}` for Cyclical analysis
- Low P/B + deep value → `/us-cigar {TICKER}` for Cigar Butt analysis

## Key Constraints

- **8-minute task limit** for the qualitative assessment
- **No external data calls** — use only data_pack.md
- **All output in English**
- **Single ticker per invocation** — for multiple tickers, run sequentially

<HARD-GATE>
Do NOT modify any scripts or code files. Only execute existing scripts and write analysis output files.
If a script needs fixing, report the issue to the user.
</HARD-GATE>
