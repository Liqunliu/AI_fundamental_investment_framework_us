# US Equity Turtle Strategy — Design Specification

**Date**: 2026-03-23
**Status**: Approved
**Author**: Brainstorm session with Claude

---

## Overview

English-language Turtle investment strategy dedicated to US equities. Uses yFinance or Bloomberg as data sources. Three operating modes with agent-team orchestration, strategy backtesting, and scheduled execution.

## Core Requirements

1. **English-only** — All prompts, reports, and output in English
2. **US equity focus** — Adapted thresholds, US GAAP, USD units
3. **Three operating modes** — Analyze, Update Portfolio, Screen
4. **Data source selection** — `--source bloomberg` or `--source yfinance` (user chooses at runtime)
5. **Time-bounded tasks** — Every task completes in < 10 minutes
6. **File-based handoffs** — Each task writes output file, next task reads it
7. **Resumable pipeline** — If task N fails, restart from task N using task N-1's output

---

## Architecture

### Agent Team

```
/us-turtle [TICKERS] [--source bloomberg|yfinance]
      │
      ├─ 1. Mode Detection
      │   ├── TICKERS given? → Mode 1 (analyze these)
      │   ├── US_PORTFOLIO.md has Holdings? → Mode 2 (update)
      │   └── Empty/missing? → Mode 3 (screen first)
      │
      ├─ 2. [Mode 3 only] Screener Agent
      │   ├── Finviz bulk screen → 50 candidates
      │   ├── Quick GG scan on top 50
      │   └── Select top 10 for deep analysis
      │
      ├─ 3. Data Collection (parallel per ticker)
      │   ├── --source bloomberg → bloomberg_collector.py
      │   └── --source yfinance → yfinance_collector.py
      │
      ├─ 4. GG Calculation (per ticker)
      │   └── calculate_turtle_gg.py (English output)
      │
      ├─ 5. 4-Factor Analysis (per ticker, agent-driven)
      │   ├── F1: Asset Quality & Business Model
      │   ├── F2: Coarse Penetration Return Rate
      │   ├── F3: Refined Penetration Return Rate
      │   └── F4: Valuation & Safety Margin
      │
      ├─ 6. Portfolio Construction Agent
      │   ├── Rank by GG + safety margin
      │   ├── Propose allocation weights
      │   ├── Compare vs previous allocation (if Mode 2)
      │   └── Generate change log entry with reasoning
      │
      └─ 7. Output
          ├── Update US_PORTFOLIO.md
          └── Per-stock reports: output/{TICKER}/analysis.md
```

### Module Inventory

| Module | Purpose | Implementation |
|--------|---------|---------------|
| 1. Screener | Finviz Tier 1 + GG quick scan | Python script |
| 2. Data Collector | yFinance / Bloomberg data fetch | Python script (reuse from CN version) |
| 3. GG Calculator | Automated GG from data pack | Python script (adapt from CN version) |
| 4. 4-Factor Analyst | US-adapted qualitative analysis | Agent prompts |
| 5. Portfolio Manager | Read/write portfolio, changelog | Agent prompts + Python |
| 6. Backtester | Historical strategy replay | Python script |
| 7. Scheduler | Daily/weekly/monthly execution | Python script |

---

## Operating Modes

### Mode 1: Analyze Specific Tickers

```
Input:  /us-turtle AAPL MSFT PYPL --source yfinance
Output: Per-ticker analysis + portfolio update
```

**Task Chain:**

| Task | Input | Output | Budget |
|------|-------|--------|--------|
| T1: Data Collection | ticker list | output/{TICKER}/data_pack.md | 3-5 min (parallel), max 5 tickers/batch |
| T2: GG Calculation | data_pack.md (per ticker) | output/{TICKER}/gg_result.md | < 2 min total |
| T3: 4-Factor Analysis | data_pack.md + gg_result.md | output/{TICKER}/analysis.md | 5-8 min, max 2 tickers/task |
| T4: Portfolio Construction | all gg_result.md + analysis.md + US_PORTFOLIO.md | US_PORTFOLIO.md (updated) | 3-5 min |

### Mode 2: Update Portfolio

```
Input:  /us-turtle (no tickers, portfolio exists)
Output: Refreshed GG + updated portfolio
```

Same as Mode 1 but reads ticker list from `## Holdings` section of `US_PORTFOLIO.md`.

### Mode 3: Screen → Analyze

```
Input:  /us-turtle screen --source yfinance
Output: Screened candidates + analysis + new portfolio
```

**Task Chain:**

| Task | Input | Output | Budget |
|------|-------|--------|--------|
| T1: Finviz Screen (Tier 1) | screening config | output/screen/tier1_candidates.csv | ~2 min |
| T2: Quick GG Scan (Tier 1.5) | tier1_candidates.csv | output/screen/tier1_with_gg.csv | 5-8 min (batch 25+25 if needed) |
| T3: Select Top 10 | tier1_with_gg.csv | output/screen/tier2_shortlist.csv | ~1 min |
| T4-T7: Mode 1 Tasks 1-4 | tier2_shortlist.csv | per-ticker analysis + portfolio | 8 min each, batch 5 tickers |

---

## US Market Adaptations

| Parameter | Chinese Version | US Version |
|-----------|----------------|------------|
| Risk-free rate | China 10Y bond (~2.5%) | US 10Y Treasury (~4.3%) |
| Threshold II | Rf + 3% = ~5.5% | Rf + 3% = ~7.3% |
| Dividend tax | 20% (港股通) / 10% (A股) | 15% qualified / 37% ordinary |
| Accounting | Chinese GAAP | US GAAP |
| ROE benchmark | ≥ 8% | ≥ 10% |
| PDF parsing | Phase 2 (年报) | Skip (10-K not needed for GG) |
| Language | Chinese | English |
| Data units | 百万元 RMB | Millions USD |
| Annual report source | Snowball/Tonghuashun | EDGAR / not needed |

### 4-Factor Model (US-Adapted)

**Factor 1: Asset Quality & Business Model**
- Same framework: light-asset vs heavy-asset vs leverage vs platform
- US GAAP adjustments: operating lease capitalization (ASC 842), SBC treatment
- Goodwill impairment (more common in US via acquisitions)

**Factor 2: Coarse Penetration Return Rate**
- Same formula: R% = M × (1 − dividend_tax_rate) × OE
- US dividend tax: 15% qualified, use 15% as default
- ROE gate: ≥ 10% (vs 8% for China)
- Veto if R% < Rf (US 10Y ~4.3%)

**Factor 3: Refined Penetration Return Rate**
- Same steps: real cash income → operating outflows → base earnings → AA
- SBC adjustment: subtract stock-based compensation from AA (US-specific)
- Capex vs R&D: treat R&D as operating expense (US GAAP already does this)

**Factor 4: Valuation & Safety Margin**
- Same 5 floor price methods adapted:
  1. Net liquid assets / share
  2. BVPS
  3. 10-year historical low price
  4. Dividend discount price (div / max(Rf, 3%))
  5. Pessimistic FCF capitalization (min 5Y FCF / Rf / shares)
- Benchmark: S&P 500 multiples (vs CSI 300 for China)

---

## Portfolio File Format

**File**: `output/US_PORTFOLIO.md`

```markdown
# US Equity Portfolio — Turtle Strategy

**Last Updated**: 2026-03-23
**Data Source**: yfinance
**Threshold II**: 7.30% (Rf 4.30% + 3%)

## Holdings
AAPL, MSFT, GOOGL, NVDA, PYPL, QCOM, ADBE

## Current Allocation

| Rank | Ticker | Allocation | Amount | GG | Safety Margin | Rating | Last Updated |
|------|--------|-----------|--------|-----|---------------|--------|-------------|
| 1 | PYPL | 25% | $250,000 | 11.55% | +4.25 pct | BUY | 2026-03-21 |
| ... | ... | ... | ... | ... | ... | ... | ... |

## Portfolio Metrics

| Metric | Value |
|--------|-------|
| Weighted GG | 10.5% |
| Weighted Safety Margin | 3.2 pct |
| Threshold Multiple | 1.44x |
| Number of Holdings | 7 |

## Allocation Change History

### 2026-03-23 — Initial Portfolio (Source: Screener)
- Screener identified 50 candidates from Finviz
- Quick GG scan narrowed to top 10
- Deep 4-factor analysis selected 7 holdings
- Allocation rationale: ...

### 2026-04-15 — Quarterly Rebalance
- PYPL: 25% → 20% (GG declined: 11.55% → 9.2%, reason: ...)
- NVDA: NEW 10% (GG 14.2%, entered at $xxx, reason: ...)

## Individual Analysis
[Links to per-stock analysis files]
```

---

## Backtest Module

### Strategy Backtest Design

Replay the full Turtle screening + GG selection process historically. Run screener at past dates, select stocks, track forward returns. Compare vs S&P 500.

**Task Chain:**

| Task | Input | Output | Budget |
|------|-------|--------|--------|
| B1: Historical Universe | date range, rebalance freq | backtest/historical_universe.parquet | ~8 min |
| B2: Historical Financials | universe + rebalance_date | backtest/financials_{date}.parquet | ~8 min per period |
| B3: Historical GG Calc | financials_{date}.parquet | backtest/selections_{date}.csv | ~3 min per period |
| B4: Portfolio Simulation | all selections + price history | backtest/equity_curve.csv + report.md | ~5 min |
| B5: Visualization | equity_curve.csv | backtest/*.png charts | ~2 min |

**Key Constraints:**
- No look-ahead bias: only use data available at each date
- One rebalance period per task (10-year quarterly = 40 tasks)
- Handle survivorship bias: include delisted stocks

**CLI:**
```bash
python3 scripts/turtle_backtest.py \
  --start 2016-01-01 --end 2025-12-31 \
  --rebalance quarterly \
  --source yfinance \
  --top-n 10 \
  --benchmark SPY
```

**Output Metrics:**
- Total return, CAGR
- Sharpe ratio, Sortino ratio
- Max drawdown, recovery time
- Alpha & Beta vs S&P 500
- Win rate (% of picks that beat threshold)
- Turnover rate
- Yearly breakdown table

---

## Scheduler Module

### Tiered Execution

| Tier | Frequency | What | Budget | Output |
|------|-----------|------|--------|--------|
| Daily | Every trading day | Alert monitor: price swings, earnings, threshold proximity | ~30 sec | alerts/YYYY-MM-DD.md |
| Weekly | Every Monday | GG refresh: recalc GG for all holdings, compare vs prior week | ~5 min | weekly/YYYY-MM-DD_refresh.md + update US_PORTFOLIO.md |
| Monthly | 1st of month | Full screen: Finviz → GG scan → compare vs holdings → recommend changes | ~30 min (split into 4 tasks) | monthly_screen/YYYY-MM/ |

### Alert Triggers (Daily)

| Condition | Action |
|-----------|--------|
| Price change > 5% in one day | Flag for review |
| Earnings release detected | Flag for GG recalculation |
| GG within 1 pct of threshold | Warn — close to veto zone |
| Stock halted or delisted | Emergency alert |
| 52-week low breached | Potential buying opportunity |

### Monthly Screen Sub-Tasks

| Task | Budget | Output |
|------|--------|--------|
| M1: Finviz screen | ~2 min | tier1.csv |
| M2: Quick GG scan (50 stocks) | ~8 min | tier1_gg.csv |
| M3: Compare vs current holdings | ~3 min | recommendations.md |
| M4: Deep analysis on new finds | ~8 min | new_candidates/ |

### Execution Options

```bash
# Standalone Python daemon
python3 scripts/turtle_scheduler.py --config schedule_config.json

# Claude Code session cron
/us-turtle schedule start
```

---

## Intermediate File Map

```
output/
├── US_PORTFOLIO.md              ← Master portfolio (read/write by all modes)
├── {TICKER}/
│   ├── data_pack.md             ← Task 1: data collection output
│   ├── gg_result.md             ← Task 2: GG calculation output
│   └── analysis.md              ← Task 3: 4-factor analysis output
├── screen/
│   ├── tier1_candidates.csv     ← Finviz raw results
│   ├── tier1_with_gg.csv        ← Quick GG scan results
│   └── tier2_shortlist.csv      ← Final selection for deep analysis
├── backtest/
│   ├── historical_universe.parquet
│   ├── financials_{date}.parquet (one per rebalance period)
│   ├── selections_{date}.csv    (one per rebalance period)
│   ├── equity_curve.csv
│   ├── backtest_report.md
│   ├── equity_curve.png
│   └── yearly_returns.png
├── alerts/
│   └── YYYY-MM-DD.md            (only created when alerts triggered)
├── weekly/
│   └── YYYY-MM-DD_refresh.md
└── monthly_screen/
    └── YYYY-MM/
        ├── tier1.csv
        ├── tier1_gg.csv
        ├── recommendations.md
        └── new_candidates/
```

---

## Design Rules

| Rule | Rationale |
|------|-----------|
| Every task writes a file before finishing | Resumable — never lose work |
| Max 5 tickers per data collection batch | Stay under 10 min |
| 4-factor analysis: max 2 tickers per task | LLM analysis takes 3-5 min each |
| Backtest: one rebalance period per task | 10Y quarterly = 40 tasks, each < 8 min |
| All intermediate files are human-readable | Debug easily, review manually |
| Portfolio changes always logged with reasoning | Audit trail for investment decisions |

---

## Implementation Order

| Phase | What | Priority | Effort | Dependencies |
|-------|------|----------|--------|-------------|
| 1 | Project scaffolding + config | High | Small | None |
| 2 | Data collectors (adapt yfinance + bloomberg) | High | Medium | Phase 1 |
| 3 | GG calculator (English, US thresholds) | High | Small | Phase 2 |
| 4 | US-adapted 4-factor prompts | High | Medium | Phase 3 |
| 5 | Portfolio manager + file format | High | Medium | Phase 3 |
| 6 | /us-turtle skill (coordinator) | High | Medium | Phase 4, 5 |
| 7 | Strategy backtester | Medium | Large | Phase 3 |
| 8 | Alert monitor (daily) | Medium | Medium | Phase 5 |
| 9 | Weekly/monthly scheduler | Low | Medium | Phase 8 |
| 10 | Tests | Ongoing | Medium | All phases |

---

## Dependencies on CN Version

Scripts to copy and adapt from `Turtle_investment_framework/scripts/`:

| Script | Action | Changes |
|--------|--------|---------|
| `yfinance_collector.py` | Copy + adapt | English output headers, USD units |
| `bloomberg_collector.py` | Copy + adapt | English output only |
| `bloomberg_modules/` | Copy | Minimal changes |
| `finviz_screener.py` | Copy + adapt | Integrate with GG quick scan |
| `calculate_turtle_gg.py` | Copy + adapt | English output, US thresholds, SBC adjustment |
| `format_utils.py` | Copy | USD formatting |
| `config.py` | Copy + adapt | US market config |

New scripts to create:
- `turtle_backtest.py`
- `turtle_alerts.py`
- `turtle_scheduler.py`
- `schedule_config.json`
