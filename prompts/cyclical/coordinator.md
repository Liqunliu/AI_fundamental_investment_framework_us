# Cyclical Trough Buying Strategy v1.0 — Coordinator

> Separate framework from Quality Yield. Buys cyclical stocks at troughs using
> normalized (mid-cycle) valuations. This coordinator dispatches tasks
> in dependency order with time budgets.

---

## Input Parsing

| Input | Example | Required? |
|-------|---------|-----------|
| Ticker symbol(s) | `PBR`, `QCOM FRO HAFN` | Optional |
| Data source | `--source bloomberg\|yfinance` | Optional (default: yfinance) |
| Mode override | `screen`, `update` | Optional |

**Parsing rules**:
1. Extract ticker symbols (1-5 uppercase letters)
2. Extract `--source` flag
3. Check for mode keywords: `screen`, `update`

---

## Mode Detection

```
IF tickers provided → Mode 1 (Analyze)
ELSE IF "screen" keyword → Mode 3 (Screen)
ELSE:
  Read output/cycle/CYCLE_PORTFOLIO.md
  IF Holdings section has tickers → Mode 2 (Update Portfolio)
  ELSE → Mode 3 (Screen)
```

---

## Mode 1: Analyze Specific Tickers

### Task 1: Data Collection (Budget: 5 min)

Uses the SAME data packs as Quality Yield. If data_pack.md already exists and is
recent (< 7 days), skip re-collection.

> ```bash
> # yfinance (handles SSL internally):
> python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md
> ```

### Task 2: Cycle Indicator Collection (Budget: 3 min)

```bash
python3 scripts/cycle_indicator_collector.py --ticker {TICKER}
```
Output: `output/cycle/{TICKER}/cycle_data_pack.md`

### Task 3: Normalized GG Calculation (Budget: 2 min)

```bash
python3 scripts/calculate_normalized_gg.py --input output/{TICKER}/data_pack.md --code {TICKER}
```
Output: `output/cycle/{TICKER}/normalized_gg.md`

### Task 4: Cycle Phase Scoring (Budget: 2 min)

```bash
python3 scripts/calculate_cycle_score.py \
    --data-pack output/{TICKER}/data_pack.md \
    --indicators output/cycle/{TICKER}/cycle_data_pack.md \
    --code {TICKER}
```
Output: `output/cycle/{TICKER}/cycle_score.md`

### Task 5: C1/C2/C3 Analysis (Budget: 8 min)

For each ticker (1 agent per ticker, parallel):
- Load `references/factor_c1_survival.md`
- Load `references/factor_c2_cycle_phase.md`
- Load `references/factor_c3_normalized_value.md`
- Read all outputs from Tasks 1-4
- Execute C1 → C2 → C3 analysis
- Write: `output/cycle/{TICKER}/cycle_analysis.md`

### Task 6: Portfolio Construction (Budget: 3 min)

```bash
python3 scripts/cycle_portfolio_manager.py update --source yfinance
```
Output: `output/cycle/CYCLE_PORTFOLIO.md`

---

## Mode 2: Update Portfolio

1. Read tickers from `output/cycle/CYCLE_PORTFOLIO.md`
2. Execute Tasks 1-6 from Mode 1

---

## Mode 3: Screen → Analyze

### Task S1: Cyclical Screening (Budget: 5 min)

```bash
python3 scripts/cycle_screener.py --with-normalized-gg --top-n 15
```
Output: `output/cycle/screen/cyclical_candidates.csv`

### Tasks S2-S6: Mode 1 Tasks 1-6 using screened tickers

---

## Key Differences from Quality Yield

| Aspect | Quality Yield | Cyclical |
|--------|--------|----------|
| GG method | TTM (trailing 12 months) | Normalized (5yr median) |
| Best at | Stable compounders | Cyclical trough buying |
| Max position | 25% | 15% |
| Cash reserve | No minimum | 20% minimum |
| Factors | 4-factor (Quality, Coarse, Refined, Valuation) | 3-factor (Survival, Phase, Normalized Value) |
| Exit trigger | GG falls below threshold | Phase upgrades to 3+ |

---

## After Completion

Present to user:

1. **Summary Table**:
```markdown
| Ticker | Phase | Norm GG | TTM GG | Gap | Entry Signal | Position |
|--------|-------|---------|--------|-----|-------------|----------|
```

2. **Phase Map**: Show all tickers plotted on the 5-phase spectrum

3. **Key Insight**: Highlight tickers where Quality Yield says AVOID but Cyclical
   says BUY (the core value proposition)

4. **Risk Summary**: Portfolio-level constraint check

---

*Cyclical Trough Strategy v1.0 | Coordinator*
