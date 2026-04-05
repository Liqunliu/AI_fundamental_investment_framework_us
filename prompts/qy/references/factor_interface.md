# Factor Interface — Parameter Contracts Between Agents

> This file defines the typed parameter contracts passed between analysis phases.
> Each section specifies: parameter name, type, allowed values, source, and description.
> Agents MUST output a parameter validation block at the end of their output to confirm
> all outbound parameters are populated and well-formed.

---

## 1. Preflight → All Agents (Calibration Parameters)

These parameters are established during Factor 1 Module 0 (Data Validation & Calibration)
and consumed by all subsequent analysis.

| Parameter | Type | Allowed Values | Source | Description |
|-----------|------|---------------|--------|-------------|
| `anchored_profit_metric` | string | `"GAAP Net Income"` \| `"Adjusted Net Income (ex-SBC)"` \| `"Operating Income"` | F1 Module 0 | Which profit line item to use as earnings base |
| `anchored_profit_value` | float ($M) | > 0 | §3 Income Statement | Dollar value of the anchored metric (latest FY) |
| `anchored_profit_ref` | string | e.g. `"§3 Net Income FY2024"` | §3 | Exact line item and column reference in data_pack |
| `cash_definition` | enum | `"narrow"` \| `"broad"` | F1 Module 0 | Whether to include short-term investments in cash |
| `cash_value` | float ($M) | ≥ 0 | §4 Balance Sheet | Dollar value under the selected cash definition |
| `interim_data` | enum | `"none"` \| `"Q1"` \| `"H1"` \| `"Q3"` | §3/§5 | Whether interim data exists; if so, which period |
| `annualization_coeff` | float | 1.0 \| 2.0 \| 4/3 \| 4.0 | Derived | Annualization multiplier for interim data (1.0 if none) |
| `anomalies` | list[string] | ≤ 3 items | F1 Module 0 | Flagged anomalies (YoY change > 30% or margin change > 5 pct) |

---

## 2. Agent A (Qualitative) → Agent C (Valuation & Synthesis)

These parameters capture the qualitative assessment and are consumed by Agent C for
position sizing, value trap screening, and cross-validation.

| Parameter | Type | Allowed Values | Source | Description |
|-----------|------|---------------|--------|-------------|
| `capital_intensity` | enum | `"capital-light"` \| `"capital-hungry"` | F1 Module 1 | Capital reinvestment requirement |
| `payment_pattern` | enum | `"prepaid"` \| `"subscription"` \| `"post-delivery"` \| `"advance-funded"` | F1 Module 2 | Cash flow timing of typical transaction |
| `cyclicality` | enum | `"strong-cycle"` \| `"weak-cycle"` \| `"non-cycle"` | F1 Module 5 | Revenue/profit volatility classification |
| `cycle_position` | enum | `"bottom"` \| `"mid-cycle"` \| `"top"` \| `"N/A"` | F1 Module 5 | Current position in cycle (only for strong-cycle) |
| `moat_rating` | enum | `"WIDE"` \| `"NARROW"` \| `"NONE"` | F1 Module 3 | Overall moat assessment |
| `moat_type_business` | string | Free text (e.g., `"Scale economies + Brand"`) | F1 Module 3 | Business barrier layer description |
| `moat_type_technical` | string | Free text or `"not applicable"` | F1 Module 3 | Technical barrier layer description |
| `compound_flywheel` | bool | `YES` \| `NO` | F1 Module 3 | Whether cross-layer flywheel exists |
| `management_rating` | enum | `"Excellent"` \| `"Adequate"` \| `"Destroying value"` \| `"Observation"` | F1 Module 7 | Management & governance assessment |
| `business_model_type` | string | One of Module 4 classifications | F1 Module 4 | Business model classification |
| `asset_quality_score` | enum | `"A"` \| `"B"` \| `"C"` \| `"D"` | F1 Summary | Overall asset quality grade |
| `sbc_concern` | enum | `"LOW"` \| `"MODERATE"` \| `"HIGH"` | F1 Module 15 | Stock-based compensation concern level |
| `regulatory_risk` | enum | `"Favorable"` \| `"Neutral"` \| `"Negative"` | F1 Module 8 | Regulatory & policy risk assessment |
| `mda_credibility` | enum | `"HIGH"` \| `"MEDIUM"` \| `"LOW"` | F1 Module 9 | MD&A narrative credibility |
| `holding_structure` | enum | `"Applicable"` \| `"Not applicable"` | F1 Module 10 | Whether conglomerate analysis applies |
| `holding_discount_pct` | float \| null | 0–100 or null | F1 Module 10 | Holding discount % (null if not applicable) |
| `factor1_conclusion` | enum | `"PASS"` \| `"VETO"` | F1 Summary | Factor 1 gate result |

---

## 3. Agent B (Quantitative) → Agent C (Valuation & Synthesis)

These parameters capture the quantitative analysis and are consumed by Agent C for
GG-based valuation, safety margin calculation, and sensitivity analysis.

| Parameter | Type | Allowed Values | Source | Description |
|-----------|------|---------------|--------|-------------|
| `owner_earnings_coarse` | float ($M) | any | F2 Step 1 | Coarse owner earnings (I) |
| `owner_earnings_sbc_adj` | float ($M) | any | F2 Step 1 | SBC-adjusted owner earnings (I_adj) |
| `maint_capex_coeff` | float | 0.7–1.8 | F2 Step 1 | Maintenance capex coefficient (G) |
| `payout_ratio_anchor` | float (%) | 0–100 | F2 Step 3 | Anchored payout ratio (M_anchor) |
| `payout_basis` | enum | `"committed"` \| `"3-year avg"` | F2 Step 3 | How payout ratio was determined |
| `avg_buybacks` | float ($M) | ≥ 0 | F2 Step 3 | 3-year average cancellation-type buybacks (O) |
| `coarse_return_R` | float (%) | any | F2 Step 3 | Coarse penetration return rate (R) |
| `coarse_return_R_adj` | float (%) | any | F2 Step 3 | SBC-adjusted coarse return rate (R_adj) |
| `factor2_conclusion` | enum | `"PASS"` \| `"VETO"` | F2 Step 4 | Factor 2 gate result |
| `AA_baseline` | float ($M) | any | F3 Step 7 | Real disposable cash surplus baseline |
| `AA_exSBC` | float ($M) | any | F3 Step 7 | SBC-adjusted AA |
| `AA_selection` | enum | `"AA_2y"` \| `"AA_all"` \| `"AA_excl"` | F3 Step 7 | Which AA variant was selected |
| `GG_standard` | float (%) | any | F3 Step 10 | Refined penetration return rate |
| `GG_exSBC` | float (%) | any | F3 Step 10 | SBC-adjusted GG |
| `GG_primary` | float (%) | any | F3 Step 10 | Primary GG used for Factor 4 |
| `coarse_deviation_HH` | float (pct) | any | F3 Step 10c | Deviation between R and GG |
| `lambda_sensitivity` | float | any | F3 Step 11 | Operating leverage estimate (λ) |
| `lambda_reliability` | enum | `"Normal"` \| `"One warning"` \| `"Multiple warnings or anomalous"` | F3 Step 11 | λ reliability assessment |
| `critical_revenue_mult` | float | 0–2 | F3 Step 11 | Critical revenue multiplier |
| `distribution_willingness` | enum | `"Strong"` \| `"Moderate"` \| `"Weak"` | F3 Step 10a | Distribution willingness assessment |
| `predictability` | enum | `"HIGH"` \| `"MEDIUM"` \| `"LOW"` | F3 Step 12 | Predictability rating |
| `extrapolation_credibility` | enum | `"HIGH"` \| `"MEDIUM"` \| `"LOW"` | F3 Step 12 | Extrapolation credibility rating |
| `cash_surplus_series` | list[float] ($M) | 3–5 values | F3 Step 7 | Year-by-year real disposable cash surplus |
| `freely_disposable_cash` | float ($M) | ≥ 0 | F3 Step 8 | Freely disposable cash reserve (FF) |
| `factor3_conclusion` | enum | `"PASS"` \| `"VETO"` | F3 Output | Factor 3 gate result |

---

## Parameter Validation Block Format

Each agent MUST append a validation block at the end of its output in the following format.
This enables downstream agents to parse parameters programmatically and catch missing values.

### Agent A (Qualitative) Validation Block

```
═══ PARAMETER VALIDATION — AGENT A (QUALITATIVE) ═══

Calibration Parameters (Preflight):
  anchored_profit_metric  = [value]
  anchored_profit_value   = [value] $M
  anchored_profit_ref     = [value]
  cash_definition         = [narrow/broad]
  cash_value              = [value] $M
  interim_data            = [none/Q1/H1/Q3]
  annualization_coeff     = [value]
  anomalies               = [list]

Qualitative Parameters:
  capital_intensity        = [capital-light/capital-hungry]
  payment_pattern          = [prepaid/subscription/post-delivery/advance-funded]
  cyclicality              = [strong-cycle/weak-cycle/non-cycle]
  cycle_position           = [bottom/mid-cycle/top/N/A]
  moat_rating              = [WIDE/NARROW/NONE]
  moat_type_business       = [description]
  moat_type_technical      = [description or "not applicable"]
  compound_flywheel        = [YES/NO]
  management_rating        = [Excellent/Adequate/Destroying value/Observation]
  business_model_type      = [classification]
  asset_quality_score      = [A/B/C/D]
  sbc_concern              = [LOW/MODERATE/HIGH]
  regulatory_risk          = [Favorable/Neutral/Negative]
  mda_credibility          = [HIGH/MEDIUM/LOW]
  holding_structure        = [Applicable/Not applicable]
  holding_discount_pct     = [value or null]
  factor1_conclusion       = [PASS/VETO]

Validation: [ALL POPULATED / MISSING: list of missing params]
═══════════════════════════════════════════════════════
```

### Agent B (Quantitative) Validation Block

```
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
  critical_revenue_mult    = [value]×
  distribution_willingness = [Strong/Moderate/Weak]
  predictability           = [HIGH/MEDIUM/LOW]
  extrapolation_credibility = [HIGH/MEDIUM/LOW]
  cash_surplus_series      = [list of values] $M
  freely_disposable_cash   = [value] $M
  factor3_conclusion       = [PASS/VETO]

Validation: [ALL POPULATED / MISSING: list of missing params]
═══════════════════════════════════════════════════════
```

---

*US Equity Quality Yield Strategy v2.0 | Factor Interface — Parameter Contracts*
