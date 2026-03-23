# US Equity Turtle Strategy v1.0 — Coordinator

> This file is the multi-phase dispatch hub. The coordinator does NOT execute
> data fetching or analysis calculations itself. It only:
> (1) Parses user input; (2) Detects operating mode; (3) Dispatches tasks in dependency order;
> (4) Enforces time budgets; (5) Delivers the final report.

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
- Split 4-factor analysis into batches of 2 tickers
- Run independent tasks in parallel where possible

### File-Based Handoffs

Every task reads input from files and writes output to files:

```
Task N output file  →  Task N+1 input file
```

This ensures:
- Tasks are resumable (restart from any point)
- Progress is never lost (checkpointed to disk)
- Each task is independently verifiable

---

## Mode 1: Analyze Tickers

```
Task 1: Data Collection
  FOR each ticker (batch of 5):
    RUN: yfinance_collector.py --ticker {T} --output output/{T}/data_pack.md
    OR:  bloomberg_collector.py --security "{T} US Equity" --output output/{T}/data_pack.md
  WAIT for batch to complete
  VERIFY: output/{T}/data_pack.md exists for each ticker

Task 2: GG Calculation
  FOR each ticker:
    RUN: calculate_turtle_gg.py --input output/{T}/data_pack.md --code {T}
  VERIFY: output/{T}/gg_result.md exists for each ticker

Task 3: 4-Factor Analysis (Agent task, max 2 tickers at a time)
  LOAD: prompts/us_equity/phase3_analysis.md
  FOR each ticker:
    READ: output/{T}/data_pack.md + output/{T}/gg_result.md
    EXECUTE: Factor 1 → 2 → 3 → 4 (load reference files progressively)
    WRITE: output/{T}/analysis.md (checkpoint after each factor)
  VERIFY: output/{T}/analysis.md exists with all 4 factors

Task 4: Portfolio Construction
  READ: All output/{T}/gg_result.md + output/{T}/analysis.md
  READ: output/US_PORTFOLIO.md (if exists, for comparison)
  EXECUTE:
    - Rank stocks by GG × safety margin
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
Task S1: Finviz Screening (Tier 1 + Quick GG)
  RUN: finviz_screener.py --with-gg --top-n 10
  VERIFY: output/screen/tier2_shortlist.csv exists
  READ: tier2_shortlist.csv → extract tickers

Tasks 1-4: Same as Mode 1 using screened tickers
```

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

*US Equity Turtle Strategy v1.0 | Coordinator*
