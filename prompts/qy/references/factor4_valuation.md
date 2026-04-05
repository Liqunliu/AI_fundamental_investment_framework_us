# Factor 4: Valuation & Safety Margin — Detailed Steps

> Reference file for Phase 3 executor. Load when executing Factor 4. All amounts in millions USD.

**Instruction**: Anchor on Factor 3's refined penetration return rate (GG), assess safety margin and screen for value traps.
Only execute for stocks that passed Factors 1-3.

## Parameter Input Validation

> Before executing Factor 4, verify that all required inbound parameters from Agent A and Agent B
> are present. See `references/factor_interface.md` for type definitions.

**Required from Agent A (Qualitative)**:
- `cyclicality` + `cycle_position` — needed for Step 3 cyclicality adjustment
- `moat_rating` — needed for Step 2 value trap #2
- `management_rating` — needed for Step 2 value trap #5
- `distribution_willingness` — needed for Step 2 value trap #4
- `asset_quality_score` — needed for report summary

**Required from Agent B (Quantitative)**:
- `GG_primary` — primary input for Steps 1-4
- `AA_baseline` or `AA_exSBC` — needed for Step 4 sensitivity analysis
- `payout_ratio_anchor` + `avg_buybacks` — needed for Step 4 sensitivity formulas
- `extrapolation_credibility` — needed for Step 3 position matrix
- `cash_surplus_series` — needed for Step 2 value trap #1
- `lambda_sensitivity` — needed for reference in sensitivity assessment

**Validation rule**: If any required parameter is missing from the upstream output files,
flag `[MISSING PARAMETER: name]` and use the degraded approach specified in phase3_analysis.md.

---

## Step 1: Threshold Calculation

```
Rf and Threshold II: → See shared_tables.md §T3

Rf = [value]% (source: data_pack §13, US 10-Year Treasury)
Threshold II = max(5%, Rf + 3%) = [value]%

Refined Penetration Return Rate [GG]% vs Threshold [II]%
  GG ≥ II → Pass, proceed to Step 2
  GG < II → Below threshold
    If growth capex as % of total deductions > 30% → Flag "recommend refining assumptions for retest"
    Otherwise → Exclude
```

---

## Step 2: Value Trap Screening

Check each item by referencing prior factor conclusions only (no new analysis):

| # | Trap Characteristic | Data Source | Criterion | Result |
|---|-------------------|------------|-----------|--------|
| 1 | Cash flow trending deterioration | Factor 3 cash surplus series | Declining ≥ 2 consecutive years AND decline > 15% | [Present / Absent] |
| 2 | Moat narrowing | Factor 1B Module 3 | Business barrier layer assessed as "Negative", or technical layer being disrupted (competitor algorithm/data advantage reversal); if compound moat flywheel exists, single-layer narrowing with other layer stable → downgrade to "Medium" rather than triggering directly | [Present / Absent] |
| 3 | Structural industry decline | Factor 1B Module 5 | Terminal demand irreversibly shrinking (not cyclical fluctuation) | [Present / Absent] |
| 4 | Weak distribution willingness | Factor 3 distribution willingness | Assessed as "Weak" | [Present / Absent] |
| 5 | Management destroying value | Factor 1B Module 7 | Assessed as "Destroying value" or "Observation period" | [Present / Absent] |

```
Count of present items = [N]
  N = 0 → Value trap risk: LOW
  N = 1 → Value trap risk: MEDIUM — flag the risk point
  N ≥ 2 → Value trap risk: HIGH
    If GG > II × 1.5 → Retain (return rate sufficiently covers risk)
    Otherwise → Exclude
```

---

## Step 3: Safety Margin & Position Sizing

```
Safety margin = Refined penetration return rate − Threshold = [value] pct (JJ = GG − II)

Cyclicality adjustment (strong-cycle companies only):
  Cycle bottom → Threshold -1 pct → Adjusted margin = GG - (II - 1%)
  Cycle top    → Threshold +2 pct → Adjusted margin = GG - (II + 2%)
  Mid-cycle or non-cycle → No adjustment

Adjusted safety margin = [value] pct (KK)
```

### Position Matrix

Full 8×3 matrix incorporating safety margin × extrapolation credibility × trap risk:

| Condition | Position |
|-----------|----------|
| Margin ≥ 1.5 pct + Credibility HIGH + Trap risk LOW | Standard position (100%) |
| Margin ≥ 1.5 pct + Credibility HIGH + Trap risk MEDIUM | 70% |
| Margin ≥ 1.5 pct + Credibility MEDIUM + Trap risk LOW | 70% |
| Margin ≥ 1.5 pct + Credibility MEDIUM + Trap risk MEDIUM | 50% |
| Margin 0.5–1.5 pct + Credibility HIGH + Trap risk LOW | 50% |
| Margin 0.5–1.5 pct + Credibility MEDIUM + Trap risk LOW | Observation (30%) |
| Margin 0–0.5 pct | Observation or wait |
| Margin < 0 pct | Do not build position |
| Credibility LOW | Observation or do not build position |
| Trap risk HIGH and GG < II × 1.5 | Exclude |

---

## Step 4: Stock Price Position & Target Buy Price Assessment

**Purpose**: Evaluate where the current price sits within the long-term historical range, reverse-calculate the target buy price from the threshold, and assess buy trigger probability.

### Step 4-1: Target Buy Price Reverse Calculation

```
Target Buy Price = Current Market Cap × (GG / II) / Total Shares Outstanding

  Where:
  - GG = Refined penetration return rate
  - II = Threshold value
  - Logic: At the target buy price, the penetration return rate equals exactly II%

  If GG ≥ II → Target buy price ≥ current price (already qualifies; target is upper reference)
  If GG < II → Target buy price < current price (must wait for pullback)
```

### Step 4-2: Historical Price Data

```
Data requirement:
  - Obtain past 10 years (or since listing, whichever is shorter) of weekly close prices
  - Source: data_pack §10 (from yfinance weekly prices)
  - If less than 10 years available, use all available data and note actual coverage period

Output variables:
  [NN] = Number of data points
  [OO] = 10-year low price (and date)
  [PP] = 10-year high price (and date)
```

### Step 4-3: Percentile Calculation & Buy Trigger Assessment

```
Current price historical percentile = (count of data points where current price < historical price) / NN × 100%

Target buy price historical percentile = (count of data points where target buy price < historical price) / NN × 100%

Buy trigger assessment:
  Target buy price percentile ≤ 10%  → Trigger probability VERY LOW (only extreme historical bottoms)
  Target buy price percentile 10-25% → Trigger probability LOW (requires significant pullback)
  Target buy price percentile 25-50% → Trigger probability MODERATE (below historical median)
  Target buy price percentile 50-75% → Trigger probability FAIRLY HIGH (price often in this range)
  Target buy price percentile > 75%  → Currently at or below target price

Comprehensive assessment:
  If GG ≥ II AND current percentile < 75% → "Qualifies; current price level reasonable"
  If GG ≥ II AND current percentile ≥ 75% → "Qualifies, but price on high side; consider waiting for pullback for higher margin"
  If GG < II AND target percentile ≤ 10% → "Needs major pullback to extreme historical low; actual trigger probability very low"
  If GG < II AND target percentile 10-50% → "Needs pullback; historically some probability of reaching target"
  If GG < II AND target percentile > 50% → "Target price within historically common range; wait for opportunity"
```

### Step 4-4: Performance Decline Sensitivity Analysis

**Core variable**: Real disposable cash surplus AA (from Factor 3 Step 7), NOT net income.
For US stocks with significant SBC (SBC > 10% of NI), use AA_exSBC from Factor 3 as the base.

```
Formulas (→ See shared_tables.md §T5 for base formula):
  Return_scenario = (AA_new × M% × (1 − Q) + O) / Current Market Cap
  Threshold_price_scenario = (AA_new × M% × (1 − Q) + O) / (II% × Total Shares)

  Where:
  - AA_new = AA × decline factor (use AA_exSBC for high-SBC stocks)
  - M = Payout ratio anchor (from Factor 2, → §T1)
  - Q = Dividend tax rate (→ §T2, US: 15%)
  - O = Average annual buybacks (from Factor 2, default 0)
  - II = Threshold value (→ §T3)
```

**Table 1: Cumulative annual decline (each year -10%, 1-3 years)**

| Scenario | Real Disposable Cash Surplus | Return Rate | vs Threshold | Threshold Price | vs Current Price |
|----------|----------------------------|-------------|-------------|----------------|-----------------|
| Base | AA | GG% | ±X pct | [value] | ±X% |
| Decline 1yr (×0.9) | AA×0.9 | ... | ... | ... | ... |
| Decline 2yr (×0.9²) | AA×0.81 | ... | ... | ... | ... |
| Decline 3yr (×0.9³) | AA×0.729 | ... | ... | ... | ... |

**Table 2: Single-year at different decline magnitudes**

| Decline | Real Disposable Cash Surplus | Return Rate | Threshold Price | vs Current Price |
|---------|----------------------------|-------------|----------------|-----------------|
| -10% | AA×0.9 | ... | ... | ... |
| -20% | AA×0.8 | ... | ... | ... |
| -30% | AA×0.7 | ... | ... | ... |

```
Interpretation:
  If return rate after 3-year decline still ≥ II → Thick safety margin, strong resilience
  If return rate drops below II after just 1-year decline → Thin margin, closely monitor performance trends
  Threshold price = price at which return rate exactly equals II% under each scenario
  vs Current Price = (Threshold Price - Current Price) / Current Price
    Positive → Current price below threshold price, safety cushion exists
    Negative → Price must fall by this % to reach threshold
```

---

## Step 5: Relative & Absolute Valuation

### Step 5-1: PE Historical Percentile

```
From §10 (historical prices) and §11 (financial ratios):
  Current PE (TTM) = [value]
  5-year PE range: [min] – [max]
  Current PE percentile = [value]% (where 0% = cheapest, 100% = most expensive)

  PE < 10th percentile → "Extreme discount"
  PE 10-25th percentile → "Attractive"
  PE 25-50th percentile → "Fair value"
  PE 50-75th percentile → "Full valuation"
  PE > 75th percentile → "Expensive"
```

### Step 5-2: PB Historical Percentile

```
From §1 and §11:
  Current PB = [value]
  5-year PB range: [min] – [max]
  Current PB percentile = [value]%
```

### Step 5-3: Sector Comparison

```
Compare current PE/PB with sector median:
  Sector median PE = [value] (from §1 or industry data)
  Premium/discount to sector = [value]%

  Trading at [premium/discount] to sector → [justified/unjustified] because [reason]
```

### Step 5-4: Relative Valuation Summary

```
PE percentile: [value]% — [assessment]
PB percentile: [value]% — [assessment]
Sector comparison: [premium/discount]%
Relative Valuation: [CHEAP / FAIR / EXPENSIVE]
```

### Step 5-5: Absolute Valuation Indicators (11 items)

Calculate all available indicators:

| # | Indicator | Formula | Value | Assessment |
|---|-----------|---------|-------|------------|
| 1 | EV/EBITDA | (Market Cap + Net Debt) / EBITDA | [value] | < 10 good, < 8 attractive |
| 2 | Cash-adjusted PE | (Market Cap − Net Cash) / Net Income | [value] | Lower = better |
| 3 | FCF Yield | FCF / Market Cap × 100 | [value]% | > 5% good, > 8% attractive |
| 4 | Earnings Yield | Net Income / Market Cap × 100 | [value]% | Compare vs Rf |
| 5 | Buyback Yield | Annual Buybacks / Market Cap × 100 | [value]% | > 3% = significant |
| 6 | Shareholder Yield | (Div + Buyback) / Market Cap × 100 | [value]% | > 5% attractive |
| 7 | EV/Revenue | Enterprise Value / Revenue | [value] | Industry-dependent |
| 8 | EV/FCF | Enterprise Value / FCF | [value] | < 15 good |
| 9 | Goodwill/Equity | Goodwill / Total Equity × 100 | [value]% | > 50% = risk |
| 10 | Net Debt/EBITDA | Net Debt / EBITDA | [value] | < 2 good, > 4 concern |
| 11 | Capex/OCF | Capital Expenditure / OCF × 100 | [value]% | < 30% = capital-light |

---

## Step 6: Floor Price (5-Method Composite)

Calculate floor price using 5 methods, then take arithmetic average:

### Method 1: Net Liquid Assets per Share

```
Net Liquid Assets = Cash + Short-term Investments + Trading Assets − Total Interest-bearing Debt
                  = [value] $M
Shares Outstanding = [value]M
Net Liquid Assets / Share = $[value]
```

### Method 2: Book Value per Share (BVPS)

```
Total Shareholders' Equity (excl. minority) = [value] $M
Shares Outstanding = [value]M
BVPS = $[value]
```

### Method 3: 10-Year Historical Low Price

```
From §10 (weekly close prices, 10 years):
  10-year minimum close = $[value]
  Date of low = [YYYY-MM-DD]
```

### Method 4: Dividend Discount Price

```
Average annual dividend per share (3-year) = $[value]
Discount rate = max(Rf, 3%) = [value]%
Dividend Discount Price = Avg DPS / Discount Rate = $[value]

Note: If company pays no dividends, this method is N/A.
Use buyback yield as alternative:
  Buyback-implied price = Annual Buyback per Share / Discount Rate = $[value]
```

### Method 5: Pessimistic FCF Capitalization Price

```
Past 5 years FCF: [FCF1, FCF2, FCF3, FCF4, FCF5] $M
Minimum FCF = [value] $M

Condition: Valid only if ALL 5 years FCF > 0
If valid:
  Pessimistic FCF Cap Price = Min_FCF / Rf / Shares = $[value]
If invalid (any year FCF ≤ 0):
  Method 5 = N/A
```

### Composite Floor Price

```
Valid methods: [list which methods produced valid results]
Floor Price = Arithmetic average of valid method values = $[value]

Current Price: $[value]
Premium over Floor: (Current / Floor − 1) × 100 = [value]%
```

### Premium Assessment

| Premium Range | Interpretation |
|--------------|----------------|
| ≤ 0% | "Buying is winning" — price below floor |
| 0 – 30% | Adequate safety margin |
| 30 – 80% | Reasonable premium, needs growth validation |
| > 80% | High premium, requires strong growth thesis |

---

## Factor 4 Output

```
Rf: [X]%
Threshold: II = [X]% (calculation shown)
Refined Penetration Return Rate: GG = [X]%
Safety Margin: JJ = [X] pct

Value Trap Screening:
  Cash flow trending deterioration: [Present / Absent]
  Moat narrowing: [Present / Absent]
  Structural industry decline: [Present / Absent]
  Weak distribution willingness: [Present / Absent]
  Management destroying value: [Present / Absent]
  Risk level: [LOW / MEDIUM / HIGH]

Cyclicality adjustment: [N/A / Bottom -1 pct / Top +2 pct]
Adjusted Safety Margin: KK = [X] pct

Stock Price Position Assessment:
  10-year price range: $[OO] — $[PP]
  Current price: $[value] (historical percentile [X]%)
  Target buy price: $[value] (historical percentile [X]%)
  Buy trigger probability: [Very Low / Low / Moderate / Fairly High / Already qualifies]
  Comprehensive assessment: [conclusion]

Performance Decline Sensitivity:
  Table 1 (cumulative -10%/yr):
    | Scenario | Return Rate | vs Threshold | Threshold Price | vs Current |
    | Base     | GG%         | ±X pct       | $[value]        | ±X%        |
    | -1yr     | ...         | ...          | ...             | ...        |
    | -2yr     | ...         | ...          | ...             | ...        |
    | -3yr     | ...         | ...          | ...             | ...        |
  Table 2 (single-year):
    | Decline  | Return Rate | Threshold Price | vs Current |
    | -10%     | ...         | ...             | ...        |
    | -20%     | ...         | ...             | ...        |
    | -30%     | ...         | ...             | ...        |

Relative Valuation:
  PE percentile: [value]% — [assessment]
  PB percentile: [value]% — [assessment]
  Sector premium/discount: [value]%

Absolute Valuation:
  EV/EBITDA: [value]x
  Cash-adj PE: [value]x
  FCF Yield: [value]%
  Shareholder Yield: [value]%
  Net Debt/EBITDA: [value]x
  Goodwill/Total Assets: [value]%

Floor Price: $[value] (methods used: [list])
Current Price: $[value]
Premium: [value]%
Floor Price Assessment: [Buying is winning / Adequate margin / Reasonable premium / High premium]

Position Recommendation: [Standard / 70% / 50% / Observation / Exclude]
Factor 4 Conclusion: [PASS / Exclude (reason)]
```

---

*US Equity Quality Yield Strategy v2.0 | Factor 4 Reference File*
