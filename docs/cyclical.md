# Cyclical Trough Buying Strategy Workflow

## Overview

The Cyclical strategy buys cyclical stocks near their trough using normalized (mid-cycle) valuations. It exists because Quality Yield penalizes cyclical stocks — QY uses TTM cash flows, which look terrible at cycle troughs. Cyclical normalizes across the full cycle to find stocks the QY framework incorrectly rejects.

**Core idea**: When a cyclical company's TTM GG says FAIL but its normalized (5-year median) GG says PASS, the trough is the buying opportunity.

## Operating Modes

| Mode | Trigger | Action |
|------|---------|--------|
| **Analyze** | `/us-cyclical PBR QCOM FRO` | Run 3-factor analysis on given tickers |
| **Update** | `/us-cyclical` (portfolio exists) | Re-analyze all current holdings |
| **Screen** | `/us-cyclical screen` | Cyclical screen → normalized GG → analyze candidates |

## US Market Parameters

| Parameter | Value |
|-----------|-------|
| Risk-free rate (Rf) | US 10Y Treasury (~4.3%) |
| Threshold II | max(5%, Rf + 3%) = 7.3% |
| Dividend tax rate | 15% (qualified) |
| Currency / Units | USD / Millions |
| Max position | 15% |
| Cash reserve | 20% minimum |
| Target holdings | 3-10 |

## Pipeline Architecture

```
Phase 1: Data Collection
  ├── Task 1:  yfinance/Bloomberg → data_pack.md
  │            (reuses QY data packs if < 7 days old)
  └── Task 2:  Cycle Indicator Collector → cycle_data_pack.md

Phase 2: Calculation
  ├── Task 3:  Normalized GG Calculator → normalized_gg.md
  │            + QY GG Calculator → {T}_GG.md (for comparison)
  └── Task 4:  Cycle Phase Scorer → cycle_score.md

Phase 3: Analysis
  └── Task 5:  C1 → C2 → C3 Analysis → cycle_analysis.md

Phase 4: Portfolio
  └── Task 6:  Portfolio Construction → CYCLE_PORTFOLIO.md
```

## 3-Factor Model

### Factor C1: Survival & Quality

**Purpose**: Ensure the company can survive the trough and emerge on the other side.

| Component | What It Evaluates | Gate |
|-----------|-------------------|------|
| C1-A: Quick Survival Screen | 5 items: liquidity, debt maturity, interest coverage, trough FCF, going-concern | Any VETO → stop |
| C1-B: Cyclicality Confirmation | CV(Revenue) >= 0.15, CV(EBITDA) >= 0.30 | Confirms stock is actually cyclical |
| C1-C: Balance Sheet Stress Test | Net Debt / Mid-Cycle EBITDA <= 3.0x, Cash runway >= 18 months | VETO if fails |
| C1-D: Basic Quality Filters | Fraud, business clarity, survival history, governance | Quick pass/fail |

**If C1 VETO → stop analysis entirely, write report with veto reason.**

### Factor C2: Cycle Phase Detection

**Purpose**: Determine where we are in the cycle — buy only at Phase 1 (trough) or Phase 2 (early recovery).

The cycle phase is a composite score from four components:

| Component | Weight | Signals |
|-----------|--------|---------|
| Company | 40% | Revenue/margin trends, capacity utilization, order backlog |
| Sector | 35% | Industry inventory, peer performance, supply/demand |
| Macro | 15% | PMI, yield curve, credit spreads, commodity prices |
| Price | 10% | Historical percentile, 52-week range, RSI |

**Phase classification**:

| Phase | Score Range | Name | Action |
|-------|------------|------|--------|
| 1 | 0.00-0.25 | Trough | **BUY** (maximum conviction) |
| 2 | 0.25-0.45 | Early Recovery | **BUY** (moderate conviction) |
| 3 | 0.45-0.65 | Mid-Cycle | **HOLD** (no new positions) |
| 4 | 0.65-0.85 | Late Cycle | **REDUCE** exposure |
| 5 | 0.85-1.00 | Peak | **AVOID** (sell into strength) |

Cross-validation: If automated phase disagrees with qualitative assessment by 2+ phases, note divergence and explain.

### Factor C3: Normalized Valuation & Entry

**Purpose**: Determine if the normalized (mid-cycle) valuation offers sufficient return.

```
Normalized GG = GG calculated using 5-year median cash flows
                instead of TTM (trailing twelve months)

Entry Signal Requirements (ALL must be met):
  1. C1 Survival: PASS
  2. C2 Phase: 1 or 2
  3. Normalized GG >= 7.30% (Threshold II)
  4. Discount to mid-cycle price >= 15%
```

**Key comparison — TTM vs Normalized**:

| Method | When It's Higher | Implication |
|--------|-----------------|-------------|
| TTM GG > Normalized GG | Company at cycle peak | QY overstates true value |
| Normalized GG > TTM GG | Company at cycle trough | **This is the opportunity** — QY rejects, Cyclical buys |
| Gap (Cyclical Premium) | Normalized - TTM | Bigger gap = deeper trough = better entry |

## Output Files per Ticker

```
output/cycle/{TICKER}/
├── cycle_data_pack.md         # Sector/macro cycle indicators
├── normalized_gg.md           # Normalized GG calculation
├── cycle_score.md             # Phase classification + composite score
└── cycle_analysis.md          # Full C1/C2/C3 report

output/{TICKER}/
├── data_pack.md               # Financial data (shared with QY)
└── {T}_GG.md                  # TTM GG (for comparison)
```

## Report Structure

| Section | Content |
|---------|---------|
| Summary | Normalized GG, TTM GG, cyclical premium, phase, entry signal |
| C1: Survival | Quick screen (5 items), cyclicality CV, stress test, quality filters |
| C2: Cycle Phase | Composite score breakdown (company/sector/macro/price), cross-validation |
| C3: Normalized Value | TTM vs normalized comparison, entry signal checklist, position sizing |
| Conclusion | Buy/hold/avoid rationale, QY vs Cyclical verdict comparison |
| Risks | Top 3 risks |
| Monitoring | Phase change triggers, GG threshold alerts, commodity level alerts |

## Scripts

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `yfinance_collector.py` | Fetch financial data | `--ticker T --output path` |
| `cycle_indicator_collector.py` | Collect sector/macro indicators | `--ticker T` |
| `calculate_normalized_gg.py` | Calculate normalized GG | `--input data_pack.md --code T` |
| `calculate_qy_gg.py` | Calculate TTM GG (comparison) | `--input data_pack.md --code T` |
| `calculate_cycle_score.py` | Compute cycle phase score | `--data-pack path --indicators path --code T` |
| `cycle_screener.py` | Cyclical stock screen | `--with-normalized-gg --top-n N` |
| `cycle_portfolio_manager.py` | Portfolio CRUD | `update / read-tickers` |
| `cycle_backtest.py` | Historical backtest | (standalone) |
| `cycle_alerts.py` | Price/phase alerts | (standalone) |

## Prompts

| File | Purpose |
|------|---------|
| `prompts/cyclical/coordinator.md` | Mode detection & task dispatch |
| `prompts/cyclical/phase3_analysis.md` | Execution engine |
| `prompts/cyclical/references/factor_c1_survival.md` | C1 survival rules |
| `prompts/cyclical/references/factor_c2_cycle_phase.md` | C2 phase detection rules |
| `prompts/cyclical/references/factor_c3_normalized_value.md` | C3 normalized valuation rules |

## Comparison with Other Strategies

| Aspect | QY | Cyclical | Cigar Butt |
|--------|-----|----------|------------|
| GG method | TTM | Normalized (5yr median) | N/A (uses NAV) |
| Core metric | GG (penetration return) | Normalized GG | NAV discount |
| Best for | Stable compounders | Cyclical trough buying | Below-NAV deep value |
| Analysis | 4-factor, parallel agents | 3-factor (C1/C2/C3) | 3-pillar + 21-item Fact Check |
| Entry signal | GG > 7.3% | Norm GG > 7.3% + Phase 1-2 | Price < tier NAV threshold |
| Max position | 25% | 15% | 10% (T0) / 8% (T1) / 5% (T2) |
| Cash reserve | None | 20% | 10% |
| Holdings | 5-15 | 3-10 | 12-20 |
| Portfolio file | `US_PORTFOLIO.md` | `CYCLE_PORTFOLIO.md` | `CIGAR_PORTFOLIO.md` |
| Output dir | `output/{T}/` | `output/cycle/{T}/` | `output/cigar/{T}/` |

## Error Handling

- yfinance failure → skip ticker, continue with remaining
- Cycle indicator failure → use defaults (mid-range scores)
- All tickers fail → report error, suggest checking network/API access
