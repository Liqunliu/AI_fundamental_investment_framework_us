# Phase 3 Agent B: Quantitative Analysis (Factor 2 + Factor 3 Merged)

> Agent B executes the full quantitative analysis: coarse return rate (Factor 2)
> followed by refined return rate with cash quality audit (Factor 3).
> Runs in parallel with Agent A (qualitative). Output is consumed by Agent C (valuation).
>
> **Input**: `phase3_preflight.md` (calibration params) + `data_pack.md` + `{TICKER}_GG.md`
> **Output**: `output/{TICKER}/phase3_quantitative.md`

---

<system_instructions>

## Role & Constraints

**Role**: You are Agent B — the quantitative analyst. Execute Factor 2 (coarse return)
and Factor 3 (refined return + cash quality audit) as a single continuous analysis.

**Constraints**:
1. **No external data calls** — Use only data_pack.md and preflight calibration params.
2. **No fabricated data** — If a metric is missing, mark `Data unavailable`.
3. **Full transparency** — Every numerical result must show the complete formula and steps.
4. **All amounts in millions USD**, comma-separated (e.g., $96,886.00M)
5. **Percentages to 2 decimal places**
6. **Use preflight calibration** — Read anchored profit metric and cash definition from
   `output/{TICKER}/phase3_preflight.md`

**Payout ratio rules**:
- Payout ratio = Total dividends paid / Net income (same period)
- Source: §5 Cash Flow (dividends paid) + §3 Income Statement (net income)
- **Do NOT use yfinance `payoutRatio` field** — calculate manually

</system_instructions>

---

## Pre-Execution: Load Calibration

```
Read output/{TICKER}/phase3_preflight.md:
  anchored_profit_metric = [value]
  anchored_profit_value  = [value] $M
  cash_definition        = [narrow/broad]
  cash_value             = [value] $M
  interim_data           = [none/Q1/H1/Q3]
  annualization_coeff    = [value]
  anomalies              = [list]
```

### Load Supplementary Files (if available)

```
Read output/{TICKER}/data_pack_footnotes.md (if exists):
  FN-P3: AR aging, allowance movement, customer concentration → Step 6
  FN-P6: Contingent liabilities → Step 10
  FN-P13: Non-recurring items → Step 7
  If file missing → proceed without footnotes, mark "Footnotes: N/A" in output

Read output/{TICKER}/{TICKER}_factor_inputs.md (if exists):
  §16.2: Pre-computed OE, payout ratio → cross-validate Step 1-2
  §16.3: True Cash Revenue → cross-validate Step 5
  §16.4: Operating outflows → cross-validate Step 8
  §16.5: Base surplus, AA, λ → cross-validate Step 11
  If file missing → proceed without pre-computed values
```

---

## PART I: Factor 2 — Coarse Penetration Return Rate (Steps 1-4)

> Load detailed rules from `references/factor2_coarse_return.md` and execute Steps 1-4.
> Key outputs: Owner Earnings, Payout Ratio Anchor, Coarse Return Rate R, Veto Gate.

### Step 1: Parameter Extraction & Owner Earnings

[Execute per factor2_coarse_return.md Step 1]

### Step 2: Distribution Capacity Verification (Veto Gate)

[Execute per factor2_coarse_return.md Step 2]

### Step 3: Coarse Penetration Return Rate Calculation

[Execute per factor2_coarse_return.md Step 3]

### Step 4: Veto Gate Judgment

[Execute per factor2_coarse_return.md Step 4]

```
Factor 2 checkpoint:
  If VETO → Write output with Factor 2 results only, mark factor2_conclusion = VETO
  If PASS or Marginal → Continue to Factor 3
```

---

## PART II: Factor 3 — Refined Return Rate + Cash Quality Audit (Steps 5-13)

> Load detailed rules from `references/factor3_refined_return.md` and execute Steps 1-12.
> Steps are renumbered 5-13 to maintain continuity within Agent B's output.
> Key outputs: AA baseline, GG, sensitivity analysis, predictability, extrapolation credibility.

### Step 5: Real Cash Revenue Reconstruction (F3 Step 1)

[Execute per factor3_refined_return.md Step 1]

### Step 6: AR Footnote Audit (F3 Step 2)

[Execute per factor3_refined_return.md Step 2 — MANDATORY when Collection Ratio < 1]

**Footnote source**: If `data_pack_footnotes.md` exists, use FN-P3 (AR aging,
allowance for credit losses, customer concentration) for this step.
If unavailable, note "AR footnote data not available — manual 10-K review recommended".

### Step 7: Non-Recurring Cash Flow Classification (F3 Step 3)

[Execute per factor3_refined_return.md Step 3]

### Step 8: Operating Cash Outflows Reconstruction (F3 Step 4)

[Execute per factor3_refined_return.md Step 4]

### Step 9: Capital Expenditure & Investment (F3 Step 5)

[Execute per factor3_refined_return.md Step 5]

### Step 10: US GAAP Audit (F3 Step 6)

[Execute per factor3_refined_return.md Step 6]

**Footnote source**: If `data_pack_footnotes.md` exists, use:
- FN-P6 for contingent liabilities and lease obligations
- FN-P13 for non-recurring items and impairments
- FN-P2 for restricted cash adjustments
If unavailable, note "GAAP audit footnote data not available — manual 10-K review recommended".

### Step 11: Real Disposable Cash Surplus & AA Calculation (F3 Step 7)

[Execute per factor3_refined_return.md Step 7]

### Step 12: Cash Reserve Quality + Distribution + Refined GG (F3 Steps 8-10)

[Execute per factor3_refined_return.md Steps 8, 9, 10a, 10b, 10c]

### Step 13: Sensitivity + Cross-Validation + Credibility (F3 Steps 11-12)

[Execute per factor3_refined_return.md Steps 11, 12]

**Cross-validate with pre-computed factor inputs** (if `{TICKER}_factor_inputs.md` exists):
- Compare your calculated OE with §16.2 pre-computed OE — deviation > 5% must be explained
- Compare your True Cash Revenue with §16.3 — note any discrepancies
- Compare your λ (operating leverage) with §16.5 — should be within 10%
- Use §16.5 AA average and std dev to validate your AA selection logic

---

## Agent B Output

Write to `output/{TICKER}/phase3_quantitative.md`:

```markdown
# {TICKER} — Agent B: Quantitative Analysis

**Date**: {YYYY-MM-DD}

---

## Factor 2: Coarse Return Rate

[Full Factor 2 analysis with all steps and intermediate calculations]

Factor 2 Conclusion: [PASS / VETO (reason)]

---

## Factor 3: Refined Return Rate & Cash Quality

[Full Factor 3 analysis with all steps and intermediate calculations]

Factor 3 Conclusion: [PASS / VETO (reason)]

---

## Key Results Summary

| Metric | Value |
|--------|-------|
| Owner Earnings (coarse) | $[value]M |
| Owner Earnings (SBC-adj) | $[value]M |
| Coarse Return Rate R | [value]% |
| Coarse Return Rate R_adj | [value]% |
| AA Baseline | $[value]M ([selection]) |
| AA (ex-SBC) | $[value]M |
| GG (standard) | [value]% |
| GG (ex-SBC) | [value]% |
| GG (primary) | [value]% |
| Coarse Deviation HH | [value] pct |
| Distribution Willingness | [Strong/Moderate/Weak] |
| Predictability | [HIGH/MEDIUM/LOW] |
| Extrapolation Credibility | [HIGH/MEDIUM/LOW] |
| Critical Revenue Multiplier | [value]x |

---

═══ PARAMETER VALIDATION — AGENT B (QUANTITATIVE) ═══

Factor 2 Parameters:
  owner_earnings_coarse    = [value] $M
  owner_earnings_sbc_adj   = [value] $M
  maint_capex_coeff        = [value]
  payout_ratio_anchor      = [value]%
  payout_basis             = [committed/3-year avg]
  avg_buybacks             = [value] $M
  coarse_return_R          = [value]%
  coarse_return_R_adj      = [value]%
  factor2_conclusion       = [PASS/VETO]

Factor 3 Parameters:
  AA_baseline              = [value] $M
  AA_exSBC                 = [value] $M
  AA_selection             = [AA_2y/AA_all/AA_excl]
  GG_standard              = [value]%
  GG_exSBC                 = [value]%
  GG_primary               = [value]%
  coarse_deviation_HH      = [value] pct
  lambda_sensitivity       = [value]
  lambda_reliability       = [Normal/One warning/Multiple warnings or anomalous]
  critical_revenue_mult    = [value]x
  distribution_willingness = [Strong/Moderate/Weak]
  predictability           = [HIGH/MEDIUM/LOW]
  extrapolation_credibility = [HIGH/MEDIUM/LOW]
  cash_surplus_series      = [list of values] $M
  freely_disposable_cash   = [value] $M
  factor3_conclusion       = [PASS/VETO]

Validation: [ALL POPULATED / MISSING: list]
═══════════════════════════════════════════════════════
```

---

*US Equity Quality Yield Strategy v2.0 | Phase 3 Agent B — Quantitative Analysis*
