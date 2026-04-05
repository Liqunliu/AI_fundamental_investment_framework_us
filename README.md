# AI Fundamental Investment Framework (US)

AI-assisted fundamental analysis system for US equities. Three investment strategies plus standalone business analysis, powered by Claude Code skills with yFinance or other data sources.

The Quality Yield strategy is adapted from [Turtle Investment Framework](https://github.com/terancejiang/Turtle_investment_framework) for the US market, with additions including SBC adjustment, SEC EDGAR integration, and parallel agent architecture.

### Key Terms

- **GG (Penetration Return Rate / 穿透回报率)** — The core metric of the Quality Yield framework. Measures the actual cash returned to shareholders (dividends + buybacks) as a percentage of market cap, after deducting all capital maintenance costs. A stock passes when GG exceeds Threshold II (Rf + 3%).
- **SBC (Stock-Based Compensation)** — Equity granted to employees as pay. SBC inflates operating cash flow since it's added back as a non-cash expense. The QY strategy deducts SBC to reflect the real dilution cost to shareholders.

## Strategies

| Skill | Strategy | Focus | Docs |
|-------|----------|-------|------|
| `/us-qy` | Quality Yield | 4-factor framework: asset quality, coarse return, refined return (GG), valuation | [docs/qy.md](docs/qy.md) |
| `/us-cigarbutt` | Cigar Butt Deep Value | Below-NAV stocks trading below liquidation value | [docs/cigarbutt.md](docs/cigarbutt.md) |
| `/us-cyclical` | Cyclical Trough Buying | Cyclical stocks near trough with recovery catalysts | [docs/cyclical.md](docs/cyclical.md) |
| `/business-analysis` | Qualitative Analysis | Standalone business model, moat, management assessment | — |

Each strategy supports: `[TICKER...]` to analyze, no args to update portfolio, `screen` to discover.

## Quick Start

```bash
pip install -r requirements.txt

# Quality Yield: analyze a stock
python3 scripts/yfinance_collector.py --ticker AAPL --output output/AAPL/data_pack.md
python3 scripts/calculate_qy_gg.py --input output/AAPL/data_pack.md --code AAPL

# Screen for QY opportunities
python3 scripts/screen_pipeline.py --top-n 10 --with-edgar

# Cigar Butt: screen for deep value
python3 scripts/cigar_screener.py

# Cyclical: screen for trough opportunities
python3 scripts/cycle_screener.py
```

## Quality Yield 4-Factor Model

| Factor | What It Measures | Key US Adaptation |
|--------|-----------------|-------------------|
| F1: Asset Quality | Business model, moat, balance sheet | SBC assessment |
| F2: Coarse Return Rate | Top-down Owner Earnings estimate | SBC-adjusted earnings |
| F3: Refined Return Rate (GG) | Bottom-up cash flow analysis | SBC subtracted from AA |
| F4: Valuation & Safety Margin | Floor price, relative/absolute value | US benchmarks, S&P 500 comparison |

### US Market Parameters

| Parameter | Value |
|-----------|-------|
| Risk-free rate (Rf) | US 10Y Treasury (~4.3%) |
| Threshold II | Rf + 3% = 7.3% |
| Dividend tax rate | 15% (qualified) |
| Currency | USD (millions) |
| Benchmark | S&P 500 (SPY) |

## Project Structure

```
AI_fundamental_investment_framework_us/
├── .claude/skills/
│   ├── us-qy/                     # Quality Yield skill
│   ├── us-cigarbutt/              # Cigar Butt skill
│   ├── us-cyclical/               # Cyclical Trough skill
│   └── business-analysis/         # Qualitative analysis skill
├── prompts/
│   ├── qy/                        # QY strategy prompts & factor references
│   ├── cigar/                     # Cigar Butt strategy prompts
│   ├── cyclical/                  # Cyclical strategy prompts
│   └── shared/                    # Shared qualitative assessment
├── scripts/
│   ├── config.py                  # US market configuration
│   ├── format_utils.py            # USD formatting utilities
│   ├── yfinance_collector.py      # yFinance data collector
│   ├── bloomberg_collector.py     # Bloomberg data collector
│   ├── edgar_downloader.py        # SEC EDGAR filing downloader
│   ├── edgar_parser.py            # SEC filing parser
│   ├── finviz_screener.py         # Finviz screener
│   ├── screen_pipeline.py         # Tier 1 → Tier 2 screening pipeline
│   ├── calculate_qy_gg.py        # QY penetration return calculator
│   ├── calculate_factor_inputs.py # Factor input calculator
│   ├── calculate_cigar_nav.py     # Cigar Butt NAV calculator
│   ├── calculate_cycle_score.py   # Cyclical score calculator
│   ├── portfolio_manager.py       # QY portfolio manager
│   ├── cigar_portfolio_manager.py # Cigar Butt portfolio manager
│   ├── cycle_portfolio_manager.py # Cyclical portfolio manager
│   ├── cigar_screener.py          # Cigar Butt screener
│   ├── cycle_screener.py          # Cyclical screener
│   ├── qy_backtest.py            # QY strategy backtester
│   ├── cycle_backtest.py          # Cyclical strategy backtester
│   ├── qy_alerts.py              # QY daily alerts
│   ├── cycle_alerts.py            # Cyclical alerts
│   └── qy_scheduler.py           # Scheduled execution
├── output/                        # All output files
│   ├── US_PORTFOLIO.md            # QY master portfolio
│   ├── {TICKER}/                  # Per-stock analysis
│   └── screen/                    # Screening results
├── templates/                     # Report templates
├── tests/                         # Test suite
├── docs/                          # Documentation
└── requirements.txt
```

## Pipeline Design

Every task completes in < 10 minutes with file-based handoffs:

```
Screener → tier1.csv → GG Scan → tier2.csv
  ↓
Data Collection → data_pack.md → GG Calc → GG.md
  ↓
Preflight → Qualitative ‖ Quantitative → Valuation → Report
  ↓
Portfolio Manager → US_PORTFOLIO.md
```

## Scheduling

| Tier | Frequency | What | Budget |
|------|-----------|------|--------|
| Daily | Every trading day | Price alerts, threshold proximity | ~30 sec |
| Weekly | Monday | GG refresh for all holdings | ~5 min |
| Monthly | 1st of month | Full Finviz screen + discovery | ~30 min |

## License

MIT
