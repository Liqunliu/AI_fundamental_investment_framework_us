---
description: "US Equity Turtle Strategy — Analyze, screen, and manage US stock portfolio"
argument-hint: "[TICKER...] [--source bloomberg|yfinance]"
---

# US Equity Turtle Strategy

Analyze US stocks using the Turtle 4-factor investment framework. Three operating modes with
agent-team orchestration, time-bounded tasks (< 10 min each), and file-based handoffs.

## Mode Detection

Parse user input to determine mode:

1. **Mode 1 (Analyze)**: User provides one or more ticker symbols
   - e.g., `/us-turtle AAPL MSFT PYPL`
2. **Mode 2 (Update Portfolio)**: No tickers given, `output/US_PORTFOLIO.md` exists with holdings
   - e.g., `/us-turtle` or `/us-turtle update`
3. **Mode 3 (Screen)**: No tickers given, portfolio is empty or missing
   - e.g., `/us-turtle screen` or `/us-turtle` (when no portfolio exists)

**Data source**: Default to `yfinance`. User can specify `--source bloomberg`.

## Execution Pipeline

### Mode 1: Analyze Specific Tickers

**Task 1: Data Collection** (Budget: 5 min, max 5 tickers/batch)
```bash
# For each ticker (parallel if possible):
python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md
# OR if --source bloomberg:
python3 scripts/bloomberg_collector.py --security "{TICKER} US Equity" --output output/{TICKER}/data_pack.md
```
Output: `output/{TICKER}/data_pack.md` for each ticker

**Task 2: GG Calculation** (Budget: 2 min)
```bash
# For each ticker:
python3 scripts/calculate_turtle_gg.py --input output/{TICKER}/data_pack.md --code {TICKER}
```
Output: `output/{TICKER}/gg_result.md` for each ticker

**Task 3: 4-Factor Analysis** (Budget: 8 min, max 2 tickers/task)
- Load `prompts/us_equity/phase3_analysis.md`
- For each ticker, read `output/{TICKER}/data_pack.md` and `output/{TICKER}/gg_result.md`
- Execute Factor 1 → 2 → 3 → 4 sequentially (load reference files progressively)
- Write results to `output/{TICKER}/analysis.md`
- If > 2 tickers, split into multiple tasks

**Task 4: Portfolio Construction** (Budget: 5 min)
- Read all `output/{TICKER}/gg_result.md` files
- Rank stocks by GG, propose allocation weights
- Compare vs previous portfolio (if exists)
- Generate change log entry with reasoning
- Update `output/US_PORTFOLIO.md`

### Mode 2: Update Portfolio

1. Read tickers from `output/US_PORTFOLIO.md` `## Holdings` section
2. Execute Tasks 1-4 from Mode 1 using those tickers
3. Compare new vs old allocations in the change log

### Mode 3: Screen → Analyze

**Task S1: Finviz Screening** (Budget: 2 min)
```bash
python3 scripts/finviz_screener.py --with-gg --top-n 10
```
Output: `output/screen/tier2_shortlist.csv`

**Task S2-S5: Mode 1 Tasks 1-4** using tickers from `tier2_shortlist.csv`

## Key Constraints

- **10-minute task limit**: If a task might exceed 10 min, split it
- **File-based handoffs**: Every task writes output files before finishing
- **Resumable**: If a task fails, restart from that task using previous outputs
- **Max batch sizes**: 5 tickers per data collection, 2 per 4-factor analysis
- **All amounts in millions USD**, all output in English
- **US thresholds**: Rf = 4.3%, Threshold II = 7.3%, Dividend tax = 15%

## After Completion

1. Present summary table of all analyzed stocks (ticker, GG, rating)
2. Show portfolio allocation if updated
3. Highlight any stocks that were vetoed and why
4. Ask user if they want to proceed with any follow-up actions

## Error Handling

- If yfinance fails for a ticker → skip with warning, continue with remaining
- If GG calculation fails → report error, skip 4-factor analysis for that ticker
- If all tickers fail → report error, suggest checking network/API access

<HARD-GATE>
Do NOT modify any scripts or code files. Only execute existing scripts and write analysis output files.
If a script needs fixing, report the issue to the user.
</HARD-GATE>
