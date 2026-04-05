# Standalone Valuation — LLM Analysis Instructions

> Execute a multi-method valuation of the target company using available data.
> Adapt methods based on company classification. All amounts in millions USD.

---

<system_instructions>

## Role & Constraints

**Role**: You are a valuation analyst. Execute multiple valuation methods, cross-validate,
apply qualitative adjustments (if available), and produce a valuation report.

**Constraints**:
1. **No fabricated data** — Use only provided data_pack.md and qualitative_report.md
2. **Show all work** — Every calculation must show formula, inputs, and result
3. **All amounts in millions USD** — Convert if reporting currency differs
4. **Conservative bias** — When uncertain, use the more conservative assumption
5. **Currency check** — If financial data is not in USD, convert first using FX rate from §1

</system_instructions>

---

## Part 1: Company Classification

Based on data_pack.md financial characteristics, classify the company:

| Type | Criteria | Primary Methods |
|------|----------|----------------|
| **Growth** | Revenue CAGR > 15%, P/E > 25x, reinvestment rate > 50% | DCF (growth-stage), Revenue multiples |
| **Value / Mature** | Stable earnings, dividend yield > 2%, P/E < 20x | DDM, Earnings multiples, Graham |
| **Hybrid** | Mix of growth and value characteristics | DCF + Multiples + DDM |
| **Distressed** | Negative earnings, declining revenue, high leverage | Asset-based, Liquidation value |

Output: `Classification: [Growth / Value / Hybrid / Distressed]`

---

## Part 2: WACC Estimation

```
Risk-free rate (Rf): From §13 Market Parameters (10yr Treasury yield)
Equity risk premium (ERP): 5.0% (US long-term average)
Beta: From §2 Company Profile
Cost of equity (Ke): Rf + Beta × ERP
Cost of debt (Kd): Interest Expense / Total Debt (from §3/§4)
Tax rate: Effective tax rate from §3 (Tax Provision / Pre-tax Income)
Debt weight: Total Debt / (Total Debt + Market Cap)
Equity weight: Market Cap / (Total Debt + Market Cap)
WACC = Ke × Equity_weight + Kd × (1 - Tax_rate) × Debt_weight
```

---

## Part 3: Valuation Methods

### Method 1: DCF (Discounted Cash Flow)

**Execute for**: All classifications except Distressed

```
Step 1: Normalize FCF
  Base FCF = OCF - Maintenance Capex
  If growth capex is material (Capex/D&A > 2.0x):
    Maintenance Capex ≈ D&A × 0.5 (capital-hungry) or D&A × 0.3 (capital-light)
  Else: Maintenance Capex = Capex

Step 2: Growth assumptions
  Stage 1 (years 1-5): Use revenue CAGR from §16.1, capped at 20%
  Stage 2 (years 6-10): Fade to terminal growth rate
  Terminal growth rate: 2.5% (US nominal GDP proxy)

Step 3: Project FCF for 10 years
  Year N FCF = Base FCF × (1 + growth_rate_N)

Step 4: Terminal value
  TV = Year 10 FCF × (1 + terminal_growth) / (WACC - terminal_growth)

Step 5: Discount and sum
  Enterprise Value = Σ(FCF_t / (1+WACC)^t) + TV / (1+WACC)^10
  Equity Value = EV - Net Debt + Cash
  Per share = Equity Value / Shares Outstanding
```

**Sensitivity table** (5×5): Vary WACC (±1%) and terminal growth (±0.5%)

### Method 2: DDM (Dividend Discount Model)

**Execute for**: Companies with dividend yield > 1%

```
Current DPS: From §14 or calculate from Total Dividends / Shares
Dividend growth rate (g): Use 3-year dividend CAGR, capped at earnings growth
  If payout ratio is rising, use min(dividend CAGR, earnings CAGR)

Gordon Growth Model:
  Fair value = DPS × (1 + g) / (Ke - g)

Two-stage DDM (if high near-term growth):
  Stage 1: 5 years at current dividend growth
  Stage 2: Terminal at sustainable growth (2-3%)
```

**Sensitivity table** (5×5): Vary Ke (±1%) and g (±0.5%)

### Method 3: Comparable Multiples

**Execute for**: All classifications

Using data from §11 Financial Ratios and §16.7 Valuation Dashboard:

```
Metrics to evaluate:
  P/E Ratio: Current vs 5-year historical range (from §16.6 percentiles)
  EV/EBITDA: Current vs typical sector range
  P/B Ratio: Current vs historical
  FCF Yield: Current (higher = cheaper)
  Earnings Yield (E/P): Compare to Rf

For each metric:
  Current value = [X]
  Historical median (if available) = [Y]
  Sector typical range = [Z1 - Z2]
  Implied fair value at median = Current Price × (Median / Current)
```

### Method 4: Graham Number

**Execute for**: Value and Hybrid classifications

```
Graham Number = √(22.5 × EPS × BVPS)

Where:
  EPS = Net Income / Shares Outstanding
  BVPS = Book Value / Shares Outstanding
  22.5 = Graham's constant (P/E of 15 × P/B of 1.5)

Margin of Safety = (Graham Number - Current Price) / Graham Number × 100%
```

---

## Part 4: Cross-Validation

```
Compare all method results:

| Method | Fair Value (per share) | vs Current Price | Implied Upside |
|--------|----------------------:|:----------------:|:--------------:|
| DCF (base case) | $[X] | [premium/discount] | [Y]% |
| DDM | $[X] | | [Y]% |
| Multiples (median) | $[X] | | [Y]% |
| Graham Number | $[X] | | [Y]% |

Convergence check:
  If all methods agree within ±20% → HIGH confidence
  If 3/4 agree → MODERATE confidence
  If wide dispersion → LOW confidence, explain why

Central estimate: [Weighted average or median, state which and why]
Valuation range: [Low end] — [High end]
```

---

## Part 5: Qualitative Adjustments (if qualitative_report.md available)

```
For each qualitative dimension, adjust valuation:

D1 (Revenue quality):
  If profit_quality = LOW → apply 10-15% haircut to DCF growth rate
  If non_operational_pct > 15% → reduce base earnings by non-operational share

D2 (Moat):
  WIDE moat → terminal growth +0.5%, no discount
  NARROW moat → no adjustment
  NONE → terminal growth -0.5%, apply 10% discount to terminal value

D3 (Cyclicality):
  If strong-cycle at top → weight bear case higher (40% bear / 30% base / 30% bull)
  If strong-cycle at bottom → weight bull case higher (30% bear / 30% base / 40% bull)

D4 (Management):
  Destroying value → apply 15-20% governance discount
  Observation period → apply 5-10% discount
  Excellent → no discount

Cross-validation result:
  Material contradictions → apply additional 5% uncertainty discount
```

---

## Part 6: Report Assembly

Write to `output/{TICKER}/{TICKER}_valuation_report.md`:

```markdown
# {TICKER} — Standalone Valuation Report

**Date**: {YYYY-MM-DD}
**Classification**: {type}
**Data Source**: {yfinance / Bloomberg}
**Qualitative Input**: {Available / Not available}

---

## Summary

| Metric | Value |
|--------|-------|
| Current Price | ${X} |
| Valuation Range | ${low} — ${high} |
| Central Estimate | ${X} |
| Implied Upside/Downside | {X}% |
| Confidence | [HIGH / MODERATE / LOW] |
| WACC | {X}% |

---

## WACC Calculation
{Full WACC derivation}

## DCF Valuation
{Projections + sensitivity table}

## DDM Valuation (if applicable)
{DPS projection + sensitivity table}

## Comparable Multiples
{Multi-metric comparison table}

## Graham Number (if applicable)
{Calculation + margin of safety}

## Cross-Validation
{Method comparison table + convergence assessment}

## Qualitative Adjustments (if available)
{Before/after for each adjustment}

## Valuation Conclusion
{Final verdict with reasoning}

## Key Assumptions & Risks
| # | Assumption | Value | Sensitivity |
|---|-----------|-------|-------------|
| 1 | WACC | {X}% | ±{Y}% per 0.5% change |
| 2 | Terminal growth | {X}% | ±{Y}% per 0.5% change |
| 3 | Base FCF | ${X}M | {note on normalization} |

---

*Standalone Valuation Module v1.0 | {TICKER}*
```

---

*Standalone Valuation Module v1.0 | Phase 2 — LLM Valuation Analysis*
