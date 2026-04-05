# Cigar Butt Deep Value Strategy Workflow

## Overview

The Cigar Butt strategy buys stocks trading below net asset value (NAV) — companies the market has left for dead that still have one last "puff" of value. It uses a 3-pillar framework (Asset Cushion + Operating Maintenance + Realization Logic) plus a 21-item Fact Check. Separate from Quality Yield and Cyclical.

**Core idea**: Buy at a deep discount to liquidation value, capture the gap as the market reprices or catalysts unlock value.

## Operating Modes

| Mode | Trigger | Action |
|------|---------|--------|
| **Analyze** | `/us-cigarbutt T VLO GM` | Run 3-pillar + Fact Check on given tickers |
| **Update** | `/us-cigarbutt` (portfolio exists) | Re-analyze all current holdings |
| **Screen** | `/us-cigarbutt screen` | Deep value screen → NAV calc → analyze candidates |

## US Market Parameters

| Parameter | Value |
|-----------|-------|
| Risk-free rate (Rf) | US 10Y Treasury (~4.3%) |
| Dividend tax rate | 15% (qualified) |
| Currency / Units | USD / Millions |
| Max position (T0) | 10% |
| Max position (T1) | 8% |
| Max position (T2) | 5% |
| Cash reserve | 10% |
| Target holdings | 12-20 |

## Pipeline Architecture

```
Phase 1: Data Collection
  └── Task 1:  yfinance/Bloomberg → data_pack.md
                (reuses QY data packs if < 7 days old)

Phase 2: NAV Calculation
  └── Task 2:  NAV Calculator → cigar_nav.md
                (T0/T1/T2 tiers, ABR, P/B zone)

Phase 3: Analysis (single-round, sequential pillars)
  └── Task 3:  Pillar 1 → Pillar 2 → Sub-Type → Pillar 3 → Fact Check
                → cigar_analysis.md

Phase 4: Portfolio
  └── Task 4:  Portfolio Construction → CIGAR_PORTFOLIO.md
```

## 3-Pillar Model

### Pillar 1: Net Asset Cushion

**Purpose**: Determine if the stock trades below liquidation value.

| Component | What It Evaluates |
|-----------|-------------------|
| T0 NAV | Most conservative: Cash + (Current Assets - All Liabilities) |
| T1 NAV | Moderate: adds discounted PP&E and investments |
| T2 NAV | Least conservative: adds discounted intangibles |
| Tier classification | Which NAV level the price falls below |
| P/B zone | Deep value (< 0.5x), Value (0.5-0.8x), Marginal (0.8-1.0x) |
| NAV discount | How far below NAV the stock trades |

**Special adjustments**: Restricted cash, pledged assets, operating leases (ASC 842).

### Pillar 2: Operating Maintenance

**Purpose**: Verify the company isn't actively burning through its asset cushion.

| Condition | Metric | Threshold |
|-----------|--------|-----------|
| 1. FCF positive | FCF = OCF - Capex | FCF > 0 |
| 2. Asset Burn Rate (ABR) | (Cash_t - Cash_t-1) / Cash_t-1 | T0: >= 0%, T1: >= 5%, T2: >= 10% |
| 3. Consecutive OCF | Years of positive OCF | Count from most recent |

**Gate**: Pass if 2 of 3 conditions met. Failure (0/3 or 1/3) is a WARNING but analysis continues.

### Pillar 3: Realization Logic

**Purpose**: Identify how value gets unlocked — the catalyst for closing the NAV gap.

| Sub-Type | Entry Criteria | Catalyst |
|----------|---------------|----------|
| **Type A** (Dividend Harvester) | Div yield >= 5%, P/B <= 0.50, >= 5 consecutive div years | Collect dividends while waiting for revaluation |
| **Type B** (Hidden Assets) | Listed/unlisted subsidiaries, SOTP discount >= 30% | Spin-off, IPO of subsidiary, strategic sale |
| **Type C1** (Event Catalyst) | Asset disposition, active buyback, going-private signal | Corporate action unlocks trapped value |
| **Type C2** (Regulatory Resolution) | Pending regulatory outcome with quantifiable impact | Resolution removes overhang |

Stocks may qualify for multiple sub-types (dual-tag).

## 21-Item Fact Check

The Fact Check is a comprehensive verification layer run after the 3 pillars:

| Category | Items | Examples |
|----------|-------|---------|
| **Automated** | #3, #6, #13 | Goodwill/assets ratio, IBD/assets, insider ownership |
| **Semi-automated** | #21 | Institutional ownership from yfinance |
| **Manual** | Remaining items | Audit opinion, related party, litigation, ESG flags |

**Rating system**:

| Rating | Criteria |
|--------|----------|
| A | All items pass |
| B | 1-2 warnings |
| B+ | B with >= 2 bonus points |
| C | 3+ warnings |
| D (VETO) | Any veto item triggered |

## Output Files per Ticker

```
output/cigar/{TICKER}/
├── cigar_nav.md               # NAV calculation (T0/T1/T2)
└── cigar_analysis.md          # Full 3-pillar + Fact Check report

output/{TICKER}/
└── data_pack.md               # Financial data (shared with QY)
```

## Report Structure

The analysis report follows this structure:

| Section | Content |
|---------|---------|
| I. Executive Summary | Tier, sub-type, NAV discount, Fact Check rating, recommendation |
| II. Company Profile | Business description, sector, geography |
| III. Financial Overview | 3-5 year trend table |
| IV. Pillar 1 | NAV calculations, tier classification, P/B zone |
| V. Pillar 2 | FCF check, ABR, OCF streak |
| VI. Pillar 3 | Sub-type classification with catalyst analysis |
| VII. Fact Check | All 21 items with pass/warning/veto |
| VIII. Risk Assessment | Top 5 risks with mitigations |
| IX. Investment Conclusion | Rating, recommendation, entry/exit plan |
| X. Monitoring Checklist | Monthly/quarterly/annual review items |

## Entry & Exit Plan

**Entry (tranched)**:

| Tranche | Weight | Trigger |
|---------|--------|---------|
| 1st | 40% | Price below tier threshold |
| 2nd | 30% | Further NAV discount or catalyst confirmation |
| 3rd | 30% | Additional downside or Fact Check upgrade |

**Exit triggers**:
- Profit-taking at defined price levels (50% then remaining)
- Hard stop-loss at 25% decline
- Fundamental deterioration (specific triggers)
- Time-based: 5-year mandatory review

## Scripts

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `yfinance_collector.py` | Fetch financial data | `--ticker T --output path` |
| `calculate_cigar_nav.py` | Calculate T0/T1/T2 NAV | `--input data_pack.md --code T --sector S` |
| `cigar_screener.py` | Deep value screen | `--with-nav --top-n N` |
| `cigar_portfolio_manager.py` | Portfolio CRUD | `update / read-tickers` |

## Prompts

| File | Purpose |
|------|---------|
| `prompts/cigar/phase3_analysis.md` | Execution engine (single-round) |
| `prompts/cigar/references/pillar1_net_asset_cushion.md` | Pillar 1 rules |
| `prompts/cigar/references/pillar2_operating_maintenance.md` | Pillar 2 rules |
| `prompts/cigar/references/pillar3_realization_logic.md` | Pillar 3 rules + sub-type decision tree |
| `prompts/cigar/references/fact_check.md` | 21-item Fact Check rules |

## Monitoring Schedule

| Frequency | Items |
|-----------|-------|
| Monthly | Price check, 8-K filings, insider activity (Form 4) |
| Quarterly | NAV update (re-run calculator), ABR recalculation, earnings review |
| Semi-annual | Full Fact Check refresh, sub-type thesis review |
| Annual | Audit opinion, management changes, full 10-K review |

**Alert triggers**: >10% price drop, dividend change, auditor change, litigation filing, management departure.

## Comparison with Other Strategies

| Aspect | QY | Cyclical | Cigar Butt |
|--------|-----|----------|------------|
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
- NAV calculation failure → report error, skip ticker
- All tickers fail → report error, suggest checking network/API access
- Fact Check VETO item → D rating, do NOT recommend investment
