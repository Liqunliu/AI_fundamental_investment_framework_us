# US Equity Turtle Strategy

AI-assisted fundamental analysis system for US equities. Uses the Turtle 4-factor investment framework with yFinance or Bloomberg data sources.

## Core Features

| Module | Purpose | Implementation |
|--------|---------|---------------|
| Screener | Finviz Tier 1 + GG quick scan | `finviz_screener.py` |
| Data Collector | yFinance / Bloomberg data fetch | `yfinance_collector.py`, `bloomberg_collector.py` |
| GG Calculator | Automated penetration return rate | `calculate_turtle_gg.py` |
| 4-Factor Analyst | US-adapted qualitative analysis | Agent prompts |
| Portfolio Manager | Read/write portfolio with changelog | `portfolio_manager.py` |
| Backtester | Historical strategy replay vs S&P 500 | `turtle_backtest.py` |
| Scheduler | Daily alerts, weekly refresh, monthly screen | `turtle_scheduler.py` |

## Three Operating Modes

```
/us-turtle AAPL MSFT          → Mode 1: Analyze specific tickers
/us-turtle                     → Mode 2: Update existing portfolio
/us-turtle screen              → Mode 3: Run screener, build new portfolio
```

## Quick Start

```bash
cd Turtle_investment_framework_us
pip install -r requirements.txt

# Mode 1: Analyze specific stocks
python3 scripts/yfinance_collector.py --ticker AAPL --output output/AAPL/data_pack.md
python3 scripts/calculate_turtle_gg.py --input output/AAPL/data_pack.md --code AAPL

# Mode 3: Screen for opportunities
python3 scripts/finviz_screener.py --with-gg --top-n 10

# Run daily alerts
python3 scripts/turtle_alerts.py

# Run backtest
python3 scripts/turtle_backtest.py --start 2018-01-01 --end 2025-12-31 --top-n 10
```

## 4-Factor Model (US-Adapted)

| Factor | What It Measures | Key US Adaptation |
|--------|-----------------|-------------------|
| F1: Asset Quality | Business model, moat, balance sheet | SBC assessment (Module 9) |
| F2: Coarse Return Rate | Top-down Owner Earnings estimate | SBC-adjusted earnings |
| F3: Refined Return Rate (GG) | Bottom-up cash flow analysis | SBC subtracted from AA |
| F4: Valuation & Safety Margin | Floor price, relative/absolute value | US benchmarks, S&P 500 comparison |

### US Market Parameters

| Parameter | Value |
|-----------|-------|
| Risk-free rate (Rf) | US 10Y Treasury (~4.3%) |
| Threshold II | Rf + 3% = 7.3% |
| Dividend tax rate | 15% (qualified) |
| ROE gate | ≥ 10% |
| Currency | USD (millions) |
| Benchmark | S&P 500 (SPY) |

## Project Structure

```
Turtle_investment_framework_us/
├── .claude/skills/us-turtle/      # Claude Code skill
├── prompts/us_equity/             # Analysis prompts (English)
│   ├── coordinator.md
│   ├── phase1_data.md
│   ├── phase3_analysis.md
│   ├── portfolio_manager.md
│   └── references/               # 4-factor detailed rules
├── scripts/
│   ├── config.py                  # US market configuration
│   ├── format_utils.py            # USD formatting utilities
│   ├── yfinance_collector.py      # yFinance data collector
│   ├── bloomberg_collector.py     # Bloomberg data collector
│   ├── finviz_screener.py         # Finviz screener + GG scan
│   ├── calculate_turtle_gg.py     # GG calculator
│   ├── portfolio_manager.py       # Portfolio read/write/changelog
│   ├── turtle_backtest.py         # Strategy backtester
│   ├── turtle_alerts.py           # Daily alert monitor
│   └── turtle_scheduler.py        # Scheduled execution
├── output/                        # All output files
│   ├── US_PORTFOLIO.md            # Master portfolio
│   ├── {TICKER}/                  # Per-stock analysis
│   ├── screen/                    # Screening results
│   ├── backtest/                  # Backtest results
│   ├── alerts/                    # Daily alerts
│   └── weekly/                    # Weekly refresh reports
├── tests/                         # Test suite
├── docs/specs/                    # Design specifications
└── requirements.txt
```

## Pipeline Design

Every task completes in < 10 minutes with file-based handoffs:

```
Screener → tier1.csv → GG Scan → tier2.csv
  ↓
Data Collection → data_pack.md → GG Calc → gg_result.md
  ↓
4-Factor Analysis → analysis.md → Portfolio Manager → US_PORTFOLIO.md
```

## Scheduling

| Tier | Frequency | What | Budget |
|------|-----------|------|--------|
| Daily | Every trading day | Price alerts, threshold proximity | ~30 sec |
| Weekly | Monday | GG refresh for all holdings | ~5 min |
| Monthly | 1st of month | Full Finviz screen + discovery | ~30 min |

## License

MIT
