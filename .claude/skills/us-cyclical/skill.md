---
description: "Cyclical Trough Buying Strategy — Analyze, screen, and manage cyclical stock portfolio"
argument-hint: "[TICKER...] [--source bloomberg|yfinance]"
---

# Cyclical Trough Buying Strategy

Buy cyclical stocks at troughs using normalized (mid-cycle) valuations.
Separate framework from Quality Yield — designed for stocks that Quality Yield penalizes
because it uses TTM cash flows (e.g., QCOM, PBR, FRO at cycle troughs).

## Mode Detection

1. **Mode 1 (Analyze)**: User provides tickers
   - e.g., `/us-cycle PBR QCOM FRO`
2. **Mode 2 (Update Portfolio)**: No tickers, `CYCLE_PORTFOLIO.md` exists
   - e.g., `/us-cycle` or `/us-cycle update`
3. **Mode 3 (Screen)**: No tickers, no portfolio
   - e.g., `/us-cycle screen`

**Data source**: Default `yfinance`. User can specify `--source bloomberg`.

## Execution Pipeline

### Mode 1: Analyze Specific Tickers

**Task 1: Data Collection** (Budget: 5 min, max 5 tickers/batch)

Reuses Quality Yield data packs if recent (< 7 days). Otherwise:

> ```bash
> # yfinance (handles SSL internally):
> python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md
> ```

**Task 2: Cycle Indicator Collection** (Budget: 3 min)
```bash
python3 scripts/cycle_indicator_collector.py --ticker {TICKER}
```
Output: `output/cycle/{TICKER}/cycle_data_pack.md`

**Task 3: Normalized GG Calculation** (Budget: 2 min)
```bash
python3 scripts/calculate_normalized_gg.py --input output/{TICKER}/data_pack.md --code {TICKER}
```
Output: `output/cycle/{TICKER}/normalized_gg.md`

Also run Quality Yield GG for comparison (if not already available):
```bash
python3 scripts/calculate_qy_gg.py --input output/{TICKER}/data_pack.md --code {TICKER}
```

**Task 4: Cycle Phase Scoring** (Budget: 2 min)
```bash
python3 scripts/calculate_cycle_score.py \
    --data-pack output/{TICKER}/data_pack.md \
    --indicators output/cycle/{TICKER}/cycle_data_pack.md \
    --code {TICKER}
```
Output: `output/cycle/{TICKER}/cycle_score.md`

**Task 5: C1/C2/C3 Analysis** (Budget: 8 min, 1 agent per ticker)

For each ticker, launch a parallel agent that:
1. Reads `prompts/cyclical/phase3_analysis.md` for execution instructions
2. Reads the three factor reference files:
   - `prompts/cyclical/references/factor_c1_survival.md`
   - `prompts/cyclical/references/factor_c2_cycle_phase.md`
   - `prompts/cyclical/references/factor_c3_normalized_value.md`
3. Reads all Task 1-4 outputs for the ticker
4. Executes C1 (Survival) → C2 (Phase) → C3 (Normalized Value) analysis
5. Writes: `output/cycle/{TICKER}/cycle_analysis.md`

**Task 6: Portfolio Construction** (Budget: 3 min)
```bash
python3 scripts/cycle_portfolio_manager.py update --source yfinance
```
Output: `output/cycle/CYCLE_PORTFOLIO.md`

### Mode 2: Update Portfolio

1. Read tickers: `python3 scripts/cycle_portfolio_manager.py read-tickers`
2. Execute Tasks 1-6 from Mode 1

### Mode 3: Screen → Analyze

**Task S1: Cyclical Screening** (Budget: 5 min)
```bash
python3 scripts/cycle_screener.py --with-normalized-gg --top-n 15
```
Output: `output/cycle/screen/cyclical_candidates.csv`

**Tasks S2-S6**: Mode 1 Tasks 1-6 using top tickers from candidates CSV.

## Key Constraints

- **10-minute task limit**: Split if needed
- **File-based handoffs**: Every task writes output files
- **Resumable**: Restart from any task using previous outputs
- **Parallel agents**: 1 ticker per analysis agent
- **All amounts in millions USD**, output in English
- **US thresholds**: Rf = 4.3%, Threshold II = 7.3%

## After Completion

1. **Summary Table** with QY vs Cyclical comparison:

```markdown
| Ticker | Phase | Norm GG | TTM GG | Gap | QY Says | Cyclical Says | Position |
|--------|-------|---------|--------|-----|---------|---------------|----------|
```

2. **Key Insight**: Highlight tickers where QY says AVOID but Cyclical
   says BUY (the core value proposition of this strategy)

3. **Portfolio update** if applicable

4. Ask if user wants to run backtest or set up monitoring alerts

## Key Differences from /us-qy

| Aspect | /us-qy | /us-cycle |
|--------|-----------|-----------|
| GG method | TTM | Normalized (5yr median) |
| Best for | Stable compounders | Cyclical trough buying |
| Max position | 25% | 15% |
| Cash reserve | None | 20% minimum |
| Analysis | 4-factor (Quality, Coarse, Refined, Valuation) | 3-factor (Survival, Phase, Normalized Value) |
| Portfolio file | US_PORTFOLIO.md | CYCLE_PORTFOLIO.md |
| Output dir | output/{TICKER}/ | output/cycle/{TICKER}/ |

## Error Handling

- If yfinance fails → skip ticker, continue
- If cycle indicators fail → use defaults (mid-range scores)
- If all tickers fail → report error, suggest network check

<HARD-GATE>
Do NOT modify any scripts or code files. Only execute existing scripts and write analysis output files.
If a script needs fixing, report the issue to the user.
</HARD-GATE>
