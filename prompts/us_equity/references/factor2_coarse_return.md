# Factor 2: Coarse Penetration Return Rate (Top-Down) — Detailed Steps

> Reference file for Phase 3 executor. Load when executing Factor 2. All amounts in millions USD.

## Purpose

Top-down approximation based on reported profits for early screening. If the coarse return rate
is already far below the threshold, veto immediately without proceeding to Factor 3 refinement.

**Instruction**: Read data_pack.md, calculate step by step. Only execute for stocks that passed Factor 1.
Use the profit and cash metrics anchored in Module 0.

---

## Step 1: Parameter Extraction & Owner Earnings

```
From data_pack §3 (Income Statement), using anchored profit metric:
  Net Income (attributable) = [value] $M (C)
  Minority Interest = [value] $M (B)
  Total Net Income = [value] $M (A)
  Minority Share = B / A = [value]%

  US-specific: Stock-Based Compensation = [value] $M (SBC)
  Adjusted Net Income = C - SBC = [value] $M (C_adj)
  Note: Use C_adj if SBC/NI > 20%, otherwise use C

From data_pack §5 (Cash Flow):
  Depreciation & Amortization = [value] $M (D)
  Total Capital Expenditure = [value] $M (E)

Capex/D&A ratio (5-year median) = [value] (F = E/D median)

Maintenance capex estimate = D × coefficient
  Light-asset (software/platform/brand): coefficient = 0.7 – 1.0
  Medium-asset (manufacturing/retail): coefficient = 1.0 – 1.3
  Heavy-asset (energy/utilities/mining): coefficient = 1.2 – 1.8
  Selected coefficient = [value] (G), rationale: [explanation]

Maintenance capex = D × G = [value] $M (H)
Owner Earnings = C + D − H = [value] $M (I)
Owner Earnings (SBC-adjusted) = C_adj + D − H = [value] $M (I_adj)
```

---

## Step 2: Distribution Capacity Verification (Veto Gate)

List past 3-5 years (from data_pack §5):

| Year | Operating CF | Investing CF | Free CF | Financing CF | Ending Cash |
|------|-------------|-------------|---------|-------------|-------------|
| 20XX | | | | | |

Judgment rules:
- Has free cash flow been consistently positive over 3-5 years?
- Is financing cash flow consistently positive (ongoing borrowing)?
- Is cash reserve still growing after dividends and buybacks?

```
If FCF is consistently negative AND financing CF consistently positive
  → Pseudo-penetration return → VETO
```

**Share buyback sustainability check** (US-specific):
```
Annual buybacks = [value] $M (from §14 or §5)
Annual SBC expense = [value] $M
Net shareholder return = Buybacks + Dividends - SBC dilution cost
If Net shareholder return < 0 → Flag as "Value extraction via SBC"
```

---

## Step 3: Coarse Penetration Return Rate Calculation

```
Payout ratio M = 3-year average (from §5 dividends paid / §3 net income)
  Past 3 years payout ratio: [X1%, X2%, X3%]
  Average payout ratio = [value]% (M)

Buybacks O = Average annual cancellation-type buybacks (3-year, from §14) = [value] $M

Tax rate Q = 15% (US qualified dividend rate, default for long-term holdings)

Market Cap from §1.

Coarse Penetration Return Rate:
  R = [C × M × (1 − Q) + O] / Market_Cap × 100

  = [value]% (R)

Alternative (SBC-adjusted):
  R_adj = [C_adj × M × (1 − Q) + O] / Market_Cap × 100
  = [value]% (R_adj)
```

---

## Step 4: Veto Gate Judgment

```
Rf from data_pack §13 (or default 4.30% for US 10-Year Treasury)

Threshold II = max(5%, Rf + 3%)
  Current: max(5%, 4.30% + 3%) = 7.30%

Coarse veto rules:

① If R < Rf → IMMEDIATE VETO, do not proceed to Factor 3
   Reason: Coarse return can't even beat risk-free rate

② If Rf ≤ R < Threshold_II × 0.5 → IMMEDIATE VETO
   Reason: Factor 3 cash quality adjustments are typically ±2 pct, cannot bridge this gap

③ If Threshold_II × 0.5 ≤ R < Threshold_II → Mark "Factor 2 marginally below threshold", proceed to Factor 3
   Reason: Factor 3 analysis may correct (e.g., growth capex reclassification)

④ If R ≥ Threshold_II → NORMAL PASS
```

---

## Factor 2 Output

```
Distribution Capacity: [PASS / VETO (reason)]
Dividend Tax Rate: Q = 15% (US qualified)
Owner Earnings (coarse): I = $[value]M (coefficient G = [value])
Owner Earnings (SBC-adj): I_adj = $[value]M
Coarse Penetration Return Rate: R = [value]%
Coarse Return Rate (SBC-adj): R_adj = [value]%
Veto Gate: [PASS④ / Marginal③ / VETO①② (reason)]
Factor 2 Conclusion: [PASS / VETO (reason)]
```

---

*US Equity Turtle Strategy v1.0 | Factor 2 Reference File*
