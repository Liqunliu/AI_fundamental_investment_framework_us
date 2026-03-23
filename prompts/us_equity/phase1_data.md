# Phase 1: Data Collection — US Equity Turtle Strategy

> Instructions for collecting financial data for US equities.
> Phase 1 uses Python scripts for deterministic data collection.

---

## Data Sources

| Source | Usage | When |
|--------|-------|------|
| **yFinance** | Default data source | `--source yfinance` (default) |
| **Bloomberg** | Institutional-grade data | `--source bloomberg` (requires Terminal/HAPI) |

## Data Collection Commands

### yFinance (Default)

```bash
# Single stock
python3 scripts/yfinance_collector.py --ticker AAPL --output output/AAPL/data_pack.md

# Multiple stocks (run sequentially or parallel)
for TICKER in AAPL MSFT GOOGL; do
  python3 scripts/yfinance_collector.py --ticker $TICKER --output output/$TICKER/data_pack.md
done
```

### Bloomberg

```bash
# Bloomberg Terminal
python3 scripts/bloomberg_collector.py --security "AAPL US Equity" --output output/AAPL/data_pack.md

# Bloomberg HAPI
python3 scripts/bloomberg_collector.py --security "AAPL US Equity" --api hapi --output output/AAPL/data_pack.md
```

## Output Format

The data pack (`data_pack.md`) contains these sections:

| Section | Content | Source |
|---------|---------|--------|
| §1 | Company Overview | yFinance info / Bloomberg |
| §2 | Market Data (price, 52-week range, PE, PB) | yFinance / Bloomberg |
| §3 | Income Statement (5 years) | yFinance financials / Bloomberg |
| §4 | Balance Sheet (5 years) | yFinance balance_sheet / Bloomberg |
| §5 | Cash Flow Statement + FCF (5 years) | yFinance cashflow / Bloomberg |
| §6 | Dividend History | yFinance dividends / Bloomberg |
| §7-§9 | Placeholders (governance, industry, subsidiaries) | WebSearch (Phase 1B) |
| §10 | Historical Prices (10 years weekly) | yFinance history / Bloomberg |
| §11 | Financial Ratios (ROE, margins, etc.) | Computed from §3/§4 |
| §12 | Risk Warnings | Auto-detected |
| §13 | Risk-Free Rate (US 10Y Treasury) | Default 4.3% |
| §14 | Share Buybacks | yFinance cashflow / Bloomberg |
| §15 | Derived Metrics (precomputed) | Computed from §3/§4/§5 |

## Time Budget

| Stocks | Budget | Strategy |
|--------|--------|----------|
| 1-5 | 5 min | Sequential or parallel |
| 6-10 | 10 min | Batch of 5, then remaining |
| 11+ | Split into 5-ticker batches | Each batch < 5 min |

## Data Quality Checks

After collection, verify:
1. §3 Income Statement has ≥ 3 years of data
2. §5 Cash Flow has OCF and Capex values
3. §1 has market cap
4. §10 has ≥ 5 years of price history

If any critical field is missing, flag in §12 Risk Warnings.
