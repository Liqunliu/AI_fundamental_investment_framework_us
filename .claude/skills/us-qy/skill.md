---
description: "US Equity Quality Yield Strategy — Analyze, screen, and manage US stock portfolio"
argument-hint: "[TICKER...] [--source bloomberg|yfinance]"
---

# US Equity Quality Yield Strategy

Analyze US stocks using the Quality Yield 4-factor investment framework. Parallel agent architecture
with preflight validation, concurrent qualitative + quantitative analysis, and synthesis.

## Mode Detection

Parse user input to determine mode:

1. **Mode 1 (Analyze)**: User provides one or more ticker symbols
   - e.g., `/us-qy AAPL MSFT PYPL`
2. **Mode 2 (Update Portfolio)**: No tickers given, `output/US_PORTFOLIO.md` exists with holdings
   - e.g., `/us-qy` or `/us-qy update`
3. **Mode 3 (Screen)**: No tickers given, portfolio is empty or missing
   - e.g., `/us-qy screen` or `/us-qy` (when no portfolio exists)

**Data source**: Default to `yfinance`. User can specify `--source bloomberg`.

## Execution Pipeline

### Mode 1: Analyze Specific Tickers

**Task 1: Data Collection** (Budget: 5 min, max 5 tickers/batch)

> ```bash
> # yfinance (handles SSL internally):
> python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md
>
> # Bloomberg:
> python3 scripts/bloomberg_collector.py --security "{TICKER} US Equity" --output output/{TICKER}/data_pack.md
> ```

Output: `output/{TICKER}/data_pack.md` for each ticker

**Task 1E: EDGAR Download** (Budget: 2 min, parallel with Task 1)
```bash
# Requires: export SEC_EDGAR_USER_AGENT="Name email@example.com"
python3 scripts/edgar_downloader.py --ticker {TICKER}

# With interim filing (optional):
python3 scripts/edgar_downloader.py --ticker {TICKER} --include-interim
```
Output: `output/{TICKER}/{TICKER}_filing_meta.json` + filing HTML (filename varies by form type)
Note: Non-blocking — warn if fails, but proceed with analysis.
Note: Filing HTML filename varies — 10-K produces `{TICKER}_10K.html`, 20-F produces `{TICKER}_20F.htm`, etc.
      Always read `{TICKER}_filing_meta.json` to find the actual filename.

**Task 2: GG Calculation** (Budget: 2 min)
```bash
python3 scripts/calculate_qy_gg.py --input output/{TICKER}/data_pack.md --code {TICKER}
```
Output: `output/{TICKER}/{TICKER}_GG.md` for each ticker

**Task 2A: EDGAR Parse** (Budget: 1 min, if filing HTML exists)
```bash
# Read filing_meta.json to find the actual HTML filename
python3 scripts/edgar_parser.py --input output/{TICKER}/{FILING_HTML} --ticker {TICKER}
```
Output: `output/{TICKER}/filing_sections.json`

**Task 2B: Footnote Extraction** (Budget: 3 min, if filing_sections.json exists)
- Load `prompts/qy/phase2_footnotes.md`
- Read `output/{TICKER}/filing_sections.json`
- Write `output/{TICKER}/data_pack_footnotes.md`

**Task 2C: Factor Inputs Calculation** (Budget: 1 min)
```bash
python3 scripts/calculate_factor_inputs.py --input output/{TICKER}/data_pack.md --code {TICKER}
```
Output: `output/{TICKER}/{TICKER}_factor_inputs.md`

**Task 3-Preflight: Data Validation** (Budget: 2 min, 1 ticker/agent)
- Load `prompts/qy/phase3_preflight.md`
- Read `output/{TICKER}/data_pack.md` and `output/{TICKER}/{TICKER}_GG.md`
- Execute: data completeness check, profit anchor, cash scope, anomaly scan
- Write `output/{TICKER}/phase3_preflight.md`
- Run all tickers in parallel

**Task 3-A‖B: Qualitative + Quantitative** (Budget: 8 min, 2 agents per ticker, PARALLEL)

For each ticker, launch **two agents simultaneously**:

- **Agent A (Qualitative)**:
  - Load `prompts/shared/qualitative/qualitative_assessment.md`
    + `prompts/qy/references/factor1_asset_quality.md`
    + `prompts/qy/references/factor_interface.md`
  - Read `output/{TICKER}/data_pack.md` + `phase3_preflight.md`
  - Execute: F1A quick screen + shared qualitative (D1-D6) + QY M6/M11-M15
  - Write `output/{TICKER}/phase3_qualitative.md`

- **Agent B (Quantitative)**:
  - Load `prompts/qy/phase3_quantitative.md`
    + `prompts/qy/references/factor2_coarse_return.md`
    + `prompts/qy/references/factor3_refined_return.md`
    + `prompts/qy/references/factor_interface.md`
  - Read `output/{TICKER}/data_pack.md` + `{TICKER}_GG.md` + `phase3_preflight.md`
    + `data_pack_footnotes.md` (if available — for F3 Steps 6, 10)
    + `{TICKER}_factor_inputs.md` (if available — cross-validate)
  - Execute: Factor 2 (Steps 1-4) + Factor 3 (Steps 5-13)
  - Write `output/{TICKER}/phase3_quantitative.md`

Wait for both agents to complete. Only tickers where F1 + F2 + F3 all PASS proceed.

**Task 3-C: Valuation & Synthesis** (Budget: 8 min, 1 ticker/agent)
- Only for tickers that PASSED all factors
- Load `prompts/qy/phase3_valuation.md`
  + `prompts/qy/references/factor4_valuation.md`
  + `prompts/qy/references/factor_interface.md`
- Read `output/{TICKER}/data_pack.md`, `{TICKER}_GG.md`, `phase3_preflight.md`,
  `phase3_qualitative.md`, `phase3_quantitative.md`
  + `data_pack_footnotes.md` (if available — for contingent liabilities in value trap screening)
  + `{TICKER}_factor_inputs.md` (if available — §16.7 valuation dashboard)
- Execute: Factor 4 (Steps 1-6) + cross-validation + report assembly
- Write `output/{TICKER}/{TICKER}_analysis_report.md`
- Run all passing tickers in parallel

**Task 4: Portfolio Construction** (Budget: 5 min)
- Read all `output/{TICKER}/{TICKER}_GG.md` and `{TICKER}_analysis_report.md` files
- Rank stocks by GG, propose allocation weights
- Compare vs previous portfolio (if exists)
- Generate change log entry with reasoning
- Update `output/US_PORTFOLIO.md`

### Mode 2: Update Portfolio

1. Read tickers from `output/US_PORTFOLIO.md` `## Holdings` section
2. Execute Tasks 1-4 from Mode 1 using those tickers
3. Compare new vs old allocations in the change log

### Mode 3: Screen → Analyze

**Task S1: Full Pipeline** (Budget: 15 min)
```bash
# Recommended: automated Tier 1 → Tier 2 pipeline
python3 scripts/screen_pipeline.py --top-n 10 --with-edgar

# Or without EDGAR:
python3 scripts/screen_pipeline.py --top-n 10 --no-edgar

# Resume from existing shortlist (skip Finviz):
python3 scripts/screen_pipeline.py --skip-tier1

# Force fresh data (bypass cache):
python3 scripts/screen_pipeline.py --top-n 5 --no-cache
```
Output: `output/screen/final_candidates.csv` + `output/screen/summary.md`
        Per-ticker: `output/{T}/data_pack.md`, `{T}_GG.md`, `{T}_factor_inputs.md`

**Task S2-S5: Mode 1 Tasks 3-4** using tickers from `final_candidates.csv`
(Data collection + GG + factor inputs already done by pipeline)

## Checkpoint & Resume

Each task writes output before completing. Resume logic:

| If this file exists... | Skip to... |
|----------------------|-----------|
| `data_pack.md` | Task 1E/Task 2 |
| `{TICKER}_filing_meta.json` + filing HTML | Task 2A (skip EDGAR download) |
| `filing_sections.json` | Task 2B (skip EDGAR parse) |
| `data_pack_footnotes.md` | Task 2C (skip footnote extraction) |
| `{TICKER}_factor_inputs.md` | Task 3-Preflight (skip factor calc) |
| `{TICKER}_GG.md` | Task 3-Preflight |
| `phase3_preflight.md` | Task 3-A‖B |
| `phase3_qualitative.md` + `phase3_quantitative.md` | Task 3-C |
| `{TICKER}_analysis_report.md` | Task 4 |

When resuming, check file timestamps — only skip if file is < 24 hours old.

## Key Constraints

- **10-minute task limit**: If a task might exceed 10 min, split it
- **File-based handoffs**: Every task writes output files before finishing
- **Resumable**: If a task fails, restart from that task using previous outputs
- **Max batch sizes**: 5 tickers per data collection, 1 ticker per analysis agent
- **Parallel agents**: Agent A and Agent B run simultaneously for each ticker
- **All amounts in millions USD**, all output in English
- **US thresholds**: Rf = 4.3%, Threshold II = 7.3%, Dividend tax = 15%

## After Completion

1. Present summary table of all analyzed stocks (ticker, GG, rating)
2. Show portfolio allocation if updated
3. Highlight any stocks that were vetoed and why
4. Ask user if they want to proceed with any follow-up actions

## Error Handling

- If yfinance fails for a ticker → skip with warning, continue with remaining
- If GG calculation fails → report error, skip analysis for that ticker
- If Agent A fails but Agent B succeeds → run Agent C with degraded qualitative data
- If Agent B fails → cannot run Agent C (quantitative data required), skip ticker
- If all tickers fail → report error, suggest checking network/API access

<HARD-GATE>
Do NOT modify any scripts or code files. Only execute existing scripts and write analysis output files.
If a script needs fixing, report the issue to the user.
</HARD-GATE>
