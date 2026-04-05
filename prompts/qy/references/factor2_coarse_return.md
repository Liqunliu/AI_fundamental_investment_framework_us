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

  Non-cash one-time item adjustment:
  If the most recent fiscal year contains significant non-cash one-time items
  (goodwill impairment, restructuring charges, litigation settlements, etc.):
    Reported Net Income = [value] $M (C_reported)
    Adjusted Net Income = [value] $M (C_adjusted) (after removing one-time items)
    Subsequent calculations use C_adjusted as the base, but show C_reported results alongside

**Interim data reference**:
If §3 contains an interim column (e.g., 2025Q3):
  Annualized Net Income = 2025Q3 × 4/3 = [value] $M (C_ann)
  Annualized OE = C_ann + D_ann − H_ann
  Annualized R = [value]% (R_ann)
  Display alongside FY-based R, labeled "annualized estimate"

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
Payout ratio anchoring:

  ⚠️ CRITICAL: Do NOT use the yfinance `payoutRatio` field.
  Calculate manually from financial statements: Dividends Paid (§5) / Net Income (§3).

  Past 3 years payout ratio: [X1%, X2%, X3%]
  Average payout ratio = [value]% (M)

  Payout ratio anchor rule: → See shared_tables.md §T1

  Payout ratio anchor = [value]% (M_anchor), basis: [committed policy / 3-year average]

Buybacks O = Average annual cancellation-type buybacks (3-year, from §14) = [value] $M

Tax rate Q = 15% (→ See shared_tables.md §T2)

Market Cap from §1.

Coarse Penetration Return Rate:
  R = [C × M_anchor × (1 − Q) + O] / Market_Cap × 100

  = [value]% (R)

Alternative (SBC-adjusted):
  R_adj = [C_adj × M_anchor × (1 − Q) + O] / Market_Cap × 100
  = [value]% (R_adj)
```

---

## Step 4: Veto Gate Judgment

```
Rf and Threshold II: → See shared_tables.md §T3

Coarse veto rules: → See shared_tables.md §T4
```

---

## Factor 2 Output

```
Distribution Capacity: [PASS / VETO (reason)]
Dividend Tax Rate: Q = 15% (US qualified)
Owner Earnings (coarse): I = $[value]M (coefficient G = [value])
Owner Earnings (SBC-adj): I_adj = $[value]M
Payout Ratio Anchor: M_anchor = [value]% (basis: [committed / 3-year avg])
Coarse Penetration Return Rate: R = [value]%
Coarse Return Rate (SBC-adj): R_adj = [value]%
Veto Gate: [PASS④ / Marginal③ / VETO①② (reason)]
Factor 2 Conclusion: [PASS / VETO (reason)]
```

> Note: Distribution willingness assessment and predictability rating are covered in Factor 3's
> in-depth analysis. See Factor 3 Step 10a for distribution willingness details.

---

## Parameter Validation Block

> At the end of Factor 2 output, append this block with all values populated.
> See `references/factor_interface.md` §3 for type definitions.

```
═══ PARAMETER VALIDATION — FACTOR 2 (COARSE RETURN) ═══

  owner_earnings_coarse    = [value] $M
  owner_earnings_sbc_adj   = [value] $M
  maint_capex_coeff        = [value]
  payout_ratio_anchor      = [value]%
  payout_basis             = [committed/3-year avg]
  avg_buybacks             = [value] $M
  coarse_return_R          = [value]%
  coarse_return_R_adj      = [value]%
  factor2_conclusion       = [PASS/VETO]

Validation: [ALL POPULATED / MISSING: list]
═══════════════════════════════════════════════════════
```

---

*US Equity Quality Yield Strategy v2.0 | Factor 2 Reference File*
