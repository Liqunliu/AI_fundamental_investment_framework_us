# Portfolio Manager — US Equity Turtle Strategy

> Instructions for reading, updating, and managing the portfolio file.

---

## Portfolio File Location

`output/US_PORTFOLIO.md`

## Reading the Portfolio

```bash
# Read ticker list
python3 scripts/portfolio_manager.py read-tickers
# Output: AAPL,MSFT,GOOGL,PYPL (comma-separated)
```

The `## Holdings` section contains a comma-separated list of tickers.
If the file doesn't exist or Holdings is empty → Mode 3 (Screen).

## Updating the Portfolio

After GG calculation is complete for all tickers:

```bash
python3 scripts/portfolio_manager.py update --gg-dir output/ --source yfinance
```

This:
1. Scans `output/{TICKER}/gg_result.md` for all tickers
2. Ranks by GG descending
3. Assigns equal-weight allocation to passing stocks
4. Generates a change log entry
5. Updates `output/US_PORTFOLIO.md`

## Portfolio File Format

The portfolio file has these required sections:

1. **Holdings**: Comma-separated ticker list (machine-readable)
2. **Current Allocation**: Markdown table with per-stock metrics
3. **Portfolio Metrics**: Weighted GG, threshold multiple, etc.
4. **Allocation Change History**: Timestamped entries with reasoning
5. **Individual Analysis**: Links to per-stock analysis files

## Change Log Guidelines

Every portfolio update MUST include a change log entry explaining:
- What changed (new stocks, removed stocks, allocation shifts)
- Why it changed (GG moved, new data, market conditions)
- Data source used
- Date of change

## Allocation Rules

- **Max single position**: 25% (from config)
- **Min positions**: 5 stocks
- **Max positions**: 15 stocks
- **Allocation method**: GG-weighted (higher GG → larger allocation)
- **Cash reserve**: 2-5% for rebalancing flexibility
