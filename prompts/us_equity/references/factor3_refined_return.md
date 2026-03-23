# Factor 3: Refined Penetration Return Rate (Bottom-Up) — Detailed Steps

> Reference file for Phase 3 executor. Load when executing Factor 3. All amounts in millions USD.

## Purpose

Bottom-up cash flow analysis to calculate the refined GG (penetration return rate).
Unlike Factor 2's profit-based approximation, Factor 3 traces actual cash flows.

**Instruction**: Read data_pack.md §3-§5, §15. Execute step by step. Use Module 0's anchored metrics.

---

## Steps 1-3: Real Cash Revenue

### Step 1: Revenue Cash Collection

```
From §3 (Income Statement):
  Revenue = [value] $M (S_reported)

From §4 (Balance Sheet):
  Accounts Receivable (current year) = [value] $M
  Accounts Receivable (prior year) = [value] $M
  AR change = [value] $M

Cash collected from customers:
  S = Revenue − AR_increase = [value] $M
  (If AR decreased, S > Revenue → positive signal)
```

### Step 2: Conservative Base

```
Conservative adjustment:
  T = S × 0.95 (5% haircut for potential bad debt / returns)
  T = [value] $M

Or if data_pack §15 has precomputed collection ratio:
  Collection ratio = OCF / Revenue = [value]%
  T = S × collection_ratio
```

### Step 3: Collection Ratio Assessment

```
Collection Ratio = OCF / Revenue (from §15 derived metrics)
  = [value]%

Assessment:
  > 100%: Excellent (cash exceeds reported revenue)
  80-100%: Good
  60-80%: Moderate (potential quality issues)
  < 60%: Poor (significant accrual vs cash gap)
```

---

## Steps 4-6: Operating Cash Outflows

### Step 4: Supplier Payments (W1)

```
From §5 or §4:
  COGS = [value] $M
  Inventory change = [value] $M
  Accounts Payable change = [value] $M

  W1 = COGS + Inventory_increase − AP_increase = [value] $M

  If AP increasing (company paying slower) → W1 < COGS → positive for cash
```

### Step 5: Employee Costs (W2)

```
From §3 or §5:
  SG&A or total operating expenses = [value] $M
  Estimate employee portion = [value] $M (W2)

  US-specific: SBC component
  Cash employee costs = W2 − SBC = [value] $M (W2_cash)
  SBC is non-cash → separate from W2 for cash flow analysis
```

### Step 6: Taxes & Interest (W3, W4)

```
From §5 (Cash Flow):
  Income taxes paid = [value] $M (W3)
  Interest paid = [value] $M (W4)

  Effective cash tax rate = W3 / Pre-tax income = [value]%
  Interest coverage = Operating Income / W4 = [value]x
```

**Total Operating Outflows:**
```
W = W1 + W2_cash + W3 + W4 = [value] $M
```

---

## Steps 7-9: Base Earnings & AA Calculation

### Step 7: Base Earnings

```
Base Earnings = T − W = [value] $M
  = Conservative Cash Revenue − Operating Outflows

Cross-check vs OCF:
  OCF from §5 = [value] $M
  Difference = Base Earnings − OCF = [value] $M
  If difference > 20% of OCF → investigate discrepancy
```

### Step 8: AA Calculation (Adjusted Available Cash)

```
From §5 (Cash Flow):
  Capital Expenditure = [value] $M (Capex)
  Maintenance Capex = D&A × G = [value] $M (from Factor 2)
  Growth Capex = Total Capex − Maintenance Capex = [value] $M

AA components:
  (+) Operating Cash Flow = [value] $M
  (−) Maintenance Capex = [value] $M
  (+) Buybacks (cancellation-type) = [value] $M
  (−) Net debt increase = [value] $M
  (−) Dividends paid = [value] $M

  AA (including capitalized growth) = [value] $M

US-specific SBC adjustment:
  (−) Stock-Based Compensation = [value] $M
  AA (excluding SBC) = AA − SBC = [value] $M

  Rationale: SBC creates real dilution for shareholders.
  Even though non-cash, it transfers value from existing to new shareholders.
  Must subtract to get true owner economics.
```

### Step 9: GG Calculation

```
Market Cap = [value] $M (from §1)

GG (standard) = AA / Market_Cap × 100 = [value]%
GG (ex-SBC) = AA_exSBC / Market_Cap × 100 = [value]%

Primary GG = GG (ex-SBC) for US stocks with significant SBC
  (Significant = SBC > 10% of Net Income)

CV (Cash Variance coefficient):
  Calculate GG for each of the past 5 years
  CV = StdDev(GG_series) / Mean(GG_series)

λ (reliability) coefficient:
  If CV < 0.3 → λ = 1.0 (highly predictable)
  If 0.3 ≤ CV < 0.6 → λ = 0.85 (moderately predictable)
  If CV ≥ 0.6 → λ = 0.7 (low predictability)

Adjusted GG = GG × λ = [value]%
```

---

## Steps 10-11: Distribution Willingness & Predictability

### Step 10: Distribution Willingness (M)

```
Payout history (3-5 years):
  Dividend payout ratio: [X1%, X2%, X3%, X4%, X5%]
  Buyback yield: [Y1%, Y2%, Y3%, Y4%, Y5%]
  Total shareholder return ratio: [Z1%, Z2%, Z3%, Z4%, Z5%]

Distribution willingness M:
  If total shareholder return > 80% consistently → M = HIGH
  If 50-80% → M = MODERATE
  If < 50% → M = LOW

US-specific: Many US tech companies return cash primarily through buybacks, not dividends.
  Include both dividends and buybacks in M assessment.
```

### Step 11: Predictability Rating

```
Based on:
  - Revenue growth stability (CV of 5-year revenue growth)
  - Margin stability (CV of 5-year operating margin)
  - Cash flow predictability (λ from Step 9)
  - Business model recurring revenue % (SaaS subscription, licensing, etc.)

Rating:
  HIGH: Subscription/recurring business, stable margins, λ ≥ 0.85
  MEDIUM: Moderate cyclicality, some recurring revenue, 0.7 ≤ λ < 0.85
  LOW: Highly cyclical, project-based revenue, λ < 0.7
```

---

## Factor 3 Output

```
Real Cash Revenue: S = $[value]M
Collection Ratio: [value]%
Operating Outflows: W = $[value]M
Base Earnings: $[value]M
AA (standard): $[value]M
AA (ex-SBC): $[value]M
SBC Adjustment: $[value]M ([value]% of Net Income)
GG (standard): [value]%
GG (ex-SBC): [value]%
GG (adjusted, ×λ): [value]%
Reliability (λ): [value] — [HIGH/MEDIUM/LOW]
Distribution Willingness (M): [HIGH/MODERATE/LOW]
Predictability: [HIGH/MEDIUM/LOW]
Factor 3 Conclusion: [PASS / VETO (reason)]
```

---

*US Equity Turtle Strategy v1.0 | Factor 3 Reference File*
