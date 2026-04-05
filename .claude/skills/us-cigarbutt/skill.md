---
description: "Cigar Butt Deep Value Strategy — Analyze, screen, and manage below-NAV stock portfolio"
argument-hint: "[TICKER...] [--source bloomberg|yfinance]"
---

# Cigar Butt Deep Value Strategy

Buy stocks trading below net asset value (NAV) using a 3-pillar framework
(Asset Cushion + Operating Maintenance + Realization Logic) with 21-item
Fact Check. Separate framework from Quality Yield and Cyclical.

## Mode Detection

Parse user input to determine mode:

1. **Mode 1 (Analyze)**: User provides one or more ticker symbols
   - e.g., `/us-cigar T VLO GM`
2. **Mode 2 (Update Portfolio)**: No tickers given, `output/cigar/CIGAR_PORTFOLIO.md` exists with holdings
   - e.g., `/us-cigar` or `/us-cigar update`
3. **Mode 3 (Screen)**: No tickers given, portfolio is empty or missing
   - e.g., `/us-cigar screen` or `/us-cigar` (when no portfolio exists)

**Data source**: Default to `yfinance`. User can specify `--source bloomberg`.

## Execution Pipeline

### Mode 1: Analyze Specific Tickers

**Task 1: Data Collection** (Budget: 5 min, max 5 tickers/batch)

Reuses Quality Yield data packs if recent (< 7 days). Otherwise:

> ```bash
> # yfinance (handles SSL internally):
> python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md
>
> # Bloomberg:
> python3 scripts/bloomberg_collector.py --security "{TICKER} US Equity" --output output/{TICKER}/data_pack.md
> ```

Output: `output/{TICKER}/data_pack.md` for each ticker

**Task 2: NAV Calculation** (Budget: 2 min)
```bash
# For each ticker:
python3 scripts/calculate_cigar_nav.py --input output/{TICKER}/data_pack.md --code {TICKER} --sector "{SECTOR}"
```
Output: `output/cigar/{TICKER}/cigar_nav.md` for each ticker

**Task 3: 3-Pillar Analysis + Fact Check** (Budget: 8 min, 1 ticker/agent)

For each ticker, launch a parallel agent that:
1. Reads `prompts/cigar/phase3_analysis.md` for execution instructions
2. Reads the four reference files:
   - `prompts/cigar/references/pillar1_net_asset_cushion.md`
   - `prompts/cigar/references/pillar2_operating_maintenance.md`
   - `prompts/cigar/references/pillar3_realization_logic.md`
   - `prompts/cigar/references/fact_check.md`
3. Reads `output/{TICKER}/data_pack.md` and `output/cigar/{TICKER}/cigar_nav.md`
4. Executes: Pillar 1 → Pillar 2 → Sub-type Classification → Pillar 3 → Fact Check
5. Writes: `output/cigar/{TICKER}/cigar_analysis.md`

Run all tickers in parallel (1 agent per ticker).

**Task 4: Portfolio Construction** (Budget: 3 min)
```bash
python3 scripts/cigar_portfolio_manager.py update --source yfinance
```
Output: `output/cigar/CIGAR_PORTFOLIO.md`

### Mode 2: Update Portfolio

1. Read tickers: `python3 scripts/cigar_portfolio_manager.py read-tickers`
2. Execute Tasks 1-4 from Mode 1 using those tickers

### Mode 3: Screen → Analyze

**Task S1: Deep Value Screening** (Budget: 5 min)
```bash
python3 scripts/cigar_screener.py --with-nav --top-n 15
```
Output: `output/cigar/screen/cigar_candidates.csv`

**Tasks S2-S4**: Mode 1 Tasks 1-4 using top tickers from candidates CSV.

## Key Constraints

- **10-minute task limit**: If a task might exceed 10 min, split it
- **File-based handoffs**: Every task writes output files before finishing
- **Resumable**: If a task fails, restart from that task using previous outputs
- **Max batch sizes**: 5 tickers per data collection, 1 ticker per analysis agent
- **Single-round analysis**: Unlike Quality Yield (3 rounds), cigar analysis runs all 3 pillars + Fact Check in 1 round per ticker
- **Parallel agents**: Run all tickers in parallel within analysis
- **All amounts in millions USD**, all output in English
- **US thresholds**: Rf = 4.3%, Dividend tax = 15% (qualified)

## After Completion

1. **Summary Table**:

```markdown
| Ticker | Tier | Sub-Type | NAV Disc | P/B | Div Yield | Fact Check | Recommendation | Position |
|--------|------|----------|----------|-----|-----------|------------|----------------|----------|
```

2. **Key Insight**: Highlight stocks with deepest NAV discounts and strongest realization catalysts

3. **Portfolio update** if applicable

4. Ask if user wants to:
   - Investigate specific Fact Check items manually
   - Run a ticker through Quality Yield or Cyclical for comparison
   - Set up monitoring alerts

## Key Differences from /us-qy and /us-cycle

| Aspect | /us-qy | /us-cycle | /us-cigar |
|--------|-----------|-----------|-----------|
| Core metric | GG (penetration return) | Normalized GG | NAV discount |
| Best for | Stable compounders | Cyclical trough buying | Below-NAV deep value |
| Analysis | 4-factor | 3-factor (Survival, Phase, Value) | 3-pillar + 21-item Fact Check |
| Entry signal | GG > 7.3% | Norm GG > 7.3% + Phase 1-2 | Price < T-level NAV threshold |
| Max position | 25% | 15% | 10% (T0), 8% (T1), 5% (T2) |
| Cash reserve | None | 20% | 10% |
| Holdings | 5-15 | 3-10 | 12-20 |
| Portfolio file | US_PORTFOLIO.md | CYCLE_PORTFOLIO.md | CIGAR_PORTFOLIO.md |
| Output dir | output/{TICKER}/ | output/cycle/{TICKER}/ | output/cigar/{TICKER}/ |

## Error Handling

- If yfinance fails for a ticker → skip with warning, continue with remaining
- If NAV calculation fails → report error, skip analysis for that ticker
- If all tickers fail → report error, suggest checking network/API access
- If Fact Check has VETO item → report D rating, do NOT recommend investment

<HARD-GATE>
Do NOT modify any scripts or code files. Only execute existing scripts and write analysis output files.
If a script needs fixing, report the issue to the user.
</HARD-GATE>
