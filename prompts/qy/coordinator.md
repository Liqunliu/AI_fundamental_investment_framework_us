# US Equity Quality Yield Strategy v2.0 — Coordinator

> This file is the multi-phase dispatch hub. The coordinator does NOT execute
> data fetching or analysis calculations itself. It only:
> (1) Parses user input; (2) Detects operating mode; (3) Dispatches tasks in dependency order;
> (4) Enforces time budgets; (5) Delivers the final report.
>
> **Architecture**: Preflight → Agent A (qualitative) ‖ Agent B (quantitative) → Agent C (valuation + synthesis)

---

## Input Parsing

User input may contain:

| Input | Example | Required? |
|-------|---------|-----------|
| Ticker symbol(s) | `AAPL`, `MSFT GOOGL PYPL` | Optional |
| Data source flag | `--source bloomberg` or `--source yfinance` | Optional (default: yfinance) |
| Mode override | `screen`, `update` | Optional |

**Parsing rules**:
1. Extract ticker symbols (1-5 uppercase letters)
2. Extract `--source` flag if present
3. Check for mode keywords: `screen`, `update`
4. Default source: `yfinance`

---

## Mode Detection

```
IF tickers provided → Mode 1 (Analyze)
ELSE IF "screen" keyword → Mode 3 (Screen)
ELSE:
  Read output/US_PORTFOLIO.md
  IF Holdings section has tickers → Mode 2 (Update Portfolio)
  ELSE → Mode 3 (Screen)
```

---

## Task Orchestration

### Time Budget Enforcement

Every task MUST complete within 10 minutes. If a task might exceed this:
- Split data collection into batches of 5 tickers
- Run independent agents in parallel where possible
- Agent A and Agent B run in parallel for each ticker

### File-Based Handoffs

Every task reads input from files and writes output to files:

```
Task N output file  →  Task N+1 input file
```

This ensures:
- Tasks are resumable (restart from any point)
- Progress is never lost (checkpointed to disk)
- Each task is independently verifiable

### Parallel Agent Architecture

```
PIPELINE (per ticker):

  Preflight (2 min)
    ↓
  ┌─────────────────────┬─────────────────────────┐
  │ Agent A (8 min)     │ Agent B (8 min)          │
  │ Qualitative         │ Quantitative             │
  │ (F1A + shared qual  │ (F2 coarse + F3 refined) │
  │  + M6/M11-M15)      │                          │
  └─────────┬───────────┴──────────┬──────────────┘
            ↓                      ↓
          Agent C (8 min)
          Valuation + Synthesis
          (F4 + cross-validation + report)
```

**Output files per ticker**:
- `output/{T}/phase3_preflight.md` — Preflight data validation
- `output/{T}/phase3_qualitative.md` — Agent A output
- `output/{T}/phase3_quantitative.md` — Agent B output
- `output/{T}/{T}_analysis_report.md` — Agent C final report

---

## Mode 1: Analyze Tickers

```
Task 1: Data Collection (parallel with Task 1E)
  FOR each ticker (batch of 5):
    RUN: yfinance_collector.py --ticker {T} --output output/{T}/data_pack.md
    OR:  bloomberg_collector.py --security "{T} US Equity" --output output/{T}/data_pack.md
  WAIT for batch to complete
  VERIFY: output/{T}/data_pack.md exists for each ticker

Task 1E: EDGAR Download (parallel with Task 1)
  FOR each ticker (parallel, background agents):
    RUN: edgar_downloader.py --ticker {T}
    Optional: Add --include-interim to also download the latest 10-Q/6-K
  Note: Runs in parallel with Task 1. Non-blocking — continues even if EDGAR fails.
  VERIFY: output/{T}/{T}_filing_meta.json exists (warn if missing, do not abort)
  Note: Filing HTML filename varies by form type (10-K → {T}_10K.html, 20-F → {T}_20F.htm, etc.).
        Always read {T}_filing_meta.json to find the actual filename.

Task 2: GG Calculation
  FOR each ticker:
    RUN: calculate_qy_gg.py --input output/{T}/data_pack.md --code {T}
  VERIFY: output/{T}/{T}_GG.md exists for each ticker

Task 2A: EDGAR Parse (runs if Task 1E produced filing HTML)
  FOR each ticker with output/{T}/{T}_filing_meta.json:
    READ: {T}_filing_meta.json → derive HTML filename from form_type + primary_document
    RUN: edgar_parser.py --input output/{T}/{DERIVED_FILENAME} --ticker {T}
  VERIFY: output/{T}/filing_sections.json exists

Task 2B: Footnote Extraction (LLM, runs if Task 2A produced JSON)
  FOR each ticker with output/{T}/filing_sections.json:
    LOAD: prompts/qy/phase2_footnotes.md
    READ: output/{T}/filing_sections.json
    EXECUTE: Extract 7 footnote sections into structured markdown
    WRITE: output/{T}/data_pack_footnotes.md

Task 2C: Factor Inputs Calculation
  FOR each ticker:
    RUN: calculate_factor_inputs.py --input output/{T}/data_pack.md --code {T}
  VERIFY: output/{T}/{T}_factor_inputs.md exists for each ticker

Task 3-Preflight: Data Validation & Calibration (1 agent per ticker, all tickers in parallel)
  FOR each ticker (parallel agents):
    LOAD: phase3_preflight.md
    READ: output/{T}/data_pack.md + output/{T}/{T}_GG.md
    CHECK (non-blocking): output/{T}/data_pack_footnotes.md, output/{T}/{T}_factor_inputs.md
    EXECUTE: Data completeness check, profit anchor, cash scope, anomaly scan
    WRITE: output/{T}/phase3_preflight.md
  WAIT for all agents to complete
  FILTER: Only tickers where both Agent A and Agent B are READY proceed

Task 3-A‖B: Qualitative + Quantitative Analysis (PARALLEL, 2 agents per ticker)
  FOR each ticker (parallel — launch Agent A and Agent B simultaneously):
    AGENT A (Qualitative):
      LOAD: prompts/shared/qualitative/qualitative_assessment.md
            + prompts/qy/references/factor1_asset_quality.md
            + prompts/qy/references/factor_interface.md
      READ: output/{T}/data_pack.md + output/{T}/phase3_preflight.md
      EXECUTE: F1A quick screen + shared qualitative (D1-D6) + QY M6/M11-M15
      WRITE: output/{T}/phase3_qualitative.md

    AGENT B (Quantitative):
      LOAD: prompts/qy/phase3_quantitative.md
            + prompts/qy/references/factor2_coarse_return.md
            + prompts/qy/references/factor3_refined_return.md
            + prompts/qy/references/factor_interface.md
      READ: output/{T}/data_pack.md + output/{T}/{T}_GG.md + output/{T}/phase3_preflight.md
            + output/{T}/data_pack_footnotes.md (if available)
            + output/{T}/{T}_factor_inputs.md (if available)
      EXECUTE: Factor 2 (Steps 1-4) + Factor 3 (Steps 5-13)
      WRITE: output/{T}/phase3_quantitative.md

  WAIT for all agents to complete
  FILTER: Only tickers where factor1 AND factor2 AND factor3 all PASS proceed

Task 3-C: Valuation & Synthesis (1 agent per ticker, all passing tickers in parallel)
  FOR each passing ticker (parallel agents):
    LOAD: prompts/qy/phase3_valuation.md
          + prompts/qy/references/factor4_valuation.md
          + prompts/qy/references/factor_interface.md
    READ: output/{T}/data_pack.md + output/{T}/{T}_GG.md
          + output/{T}/phase3_preflight.md
          + output/{T}/phase3_qualitative.md
          + output/{T}/phase3_quantitative.md
          + output/{T}/data_pack_footnotes.md (if available)
          + output/{T}/{T}_factor_inputs.md (if available)
    EXECUTE: Factor 4 (Steps 1-6) + cross-validation + report assembly
    WRITE: output/{T}/{T}_analysis_report.md
  WAIT for all agents to complete

Task 4: Portfolio Construction
  READ: All output/{T}/{T}_GG.md + output/{T}/{T}_analysis_report.md
  READ: output/US_PORTFOLIO.md (if exists, for comparison)
  EXECUTE:
    - Rank stocks by GG x safety margin
    - Propose allocation weights (GG-weighted, max 25% per stock)
    - Compare vs previous allocation
    - Generate change log entry
  WRITE: output/US_PORTFOLIO.md
```

## Mode 2: Update Portfolio

```
Task 0: Read Portfolio
  READ: output/US_PORTFOLIO.md → extract ticker list from ## Holdings
  IF empty → switch to Mode 3

Tasks 1-4: Same as Mode 1 using extracted tickers
```

## Mode 3: Screen → Analyze

```
Option A: Full automated pipeline (recommended)
  RUN: python3 scripts/screen_pipeline.py --top-n 10 --with-edgar
  This runs the full Tier 1 → Tier 2 pipeline automatically:
    - Tier 1: Finviz screening + quick GG
    - Tier 2: For each shortlisted ticker:
      yfinance_collector.py → calculate_qy_gg.py → calculate_factor_inputs.py → EDGAR
  VERIFY: output/screen/final_candidates.csv exists
  OUTPUT: output/screen/summary.md + per-ticker files in output/{T}/
  READ: final_candidates.csv → proceed to Phase 3 analysis (Tasks 3-4) for top candidates

Option B: Manual step-by-step
  Task S1: Finviz Screening (Tier 1 + Quick GG)
    RUN: finviz_screener.py --with-gg --top-n 10
    VERIFY: output/screen/tier2_shortlist.csv exists
    READ: tier2_shortlist.csv → extract tickers
  Tasks 1-4: Same as Mode 1 using screened tickers
```

---

## Checkpoint & Resume Logic

Each task writes its output before completing. Resume logic:

| If this file exists... | Skip to... |
|----------------------|-----------|
| `output/{T}/data_pack.md` | Task 1E/Task 2 |
| `output/{T}/{T}_filing_meta.json` + filing HTML | Task 2A (skip EDGAR download) |
| `output/{T}/filing_sections.json` | Task 2B (skip EDGAR parse) |
| `output/{T}/data_pack_footnotes.md` | Task 2C (skip footnote extraction) |
| `output/{T}/{T}_factor_inputs.md` | Task 3-Preflight (skip factor calc) |
| `output/{T}/{T}_GG.md` | Task 3-Preflight |
| `output/{T}/phase3_preflight.md` | Task 3-A‖B |
| `output/{T}/phase3_qualitative.md` AND `phase3_quantitative.md` | Task 3-C |
| `output/{T}/{T}_analysis_report.md` | Task 4 |

When resuming, check file timestamps — only skip if file is < 24 hours old.

---

## Output Delivery

After all tasks complete, present to user:

1. **Summary Table**:
```markdown
| Ticker | GG | Safety Margin | Rating | Position Size |
|--------|-----|---------------|--------|--------------|
```

2. **Portfolio Update** (if applicable):
   - Show old vs new allocations
   - Highlight changes with reasoning

3. **Vetoed Stocks** (if any):
   - List stocks that failed at each factor with reason

4. **Next Steps**:
   - Suggest monitoring schedule
   - Offer to run backtest on the portfolio

---

*US Equity Quality Yield Strategy v2.0 | Coordinator*
