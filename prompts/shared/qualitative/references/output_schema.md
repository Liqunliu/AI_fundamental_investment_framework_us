# Qualitative Assessment Output Schema

> Typed parameter definitions for the 6 dimensions (D1-D6).
> Downstream agents parse these parameters from the summary block in the qualitative output.

---

## D1: Business Model & Capital Structure

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `capital_intensity` | enum | `"capital-light"` \| `"capital-hungry"` | Annual reinvestment requirement relative to earnings |
| `payment_pattern` | enum | `"prepaid"` \| `"subscription"` \| `"post-delivery"` \| `"advance-funded"` | Cash flow timing of typical transaction cycle |
| `business_model_type` | string | One of the 7 classification types | Business model category from classification table |

## D2: Competitive Advantage & Moat

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `moat_rating` | enum | `"WIDE"` \| `"NARROW"` \| `"NONE"` | Overall moat durability assessment |
| `moat_type_business` | string | Free text describing Layer 1 barriers | Business barrier layer (e.g., "Scale economies + Brand") |
| `moat_type_technical` | string | Free text or `"not applicable"` | Technical barrier layer (e.g., "Data flywheel + Algorithm") |
| `compound_flywheel` | bool | `YES` \| `NO` | Whether cross-layer reinforcing flywheel exists |
| `pricing_power` | enum | `"Strong"` \| `"Moderate"` \| `"Weak"` \| `"None"` | Ability to raise prices without losing customers |

## D3: External Environment

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `cyclicality` | enum | `"strong-cycle"` \| `"weak-cycle"` \| `"non-cycle"` | Revenue/profit volatility classification |
| `cycle_position` | enum | `"bottom"` \| `"mid-cycle"` \| `"top"` \| `"N/A"` | Current position (only for strong-cycle) |
| `regulatory_risk` | enum | `"Favorable"` \| `"Neutral"` \| `"Negative"` | Net regulatory/policy risk assessment |

## D4: Management & Governance

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `management_rating` | enum | `"Excellent"` \| `"Adequate"` \| `"Destroying value"` \| `"Observation"` | Overall management quality assessment |
| `management_tenure_yrs` | int | >= 0 | Current CEO tenure in years |
| `capital_allocation_summary` | string | Free text, <= 1 sentence | Summary of capital allocation track record |

## D5: MD&A Interpretation

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `mda_credibility` | enum | `"HIGH"` \| `"MEDIUM"` \| `"LOW"` | Based on historical guidance track record |
| `mda_key_findings` | list[string] | <= 3 items | Most important MD&A takeaways |
| `mda_consistency` | enum | `"Consistent"` \| `"Partial divergence"` \| `"Major contradiction"` | Cross-validation vs. independent analysis |
| `mda_impact` | enum | `"Positive"` \| `"Neutral"` \| `"Negative"` | Net impact on investment judgment |

## D6: Complex Structure (Conditional)

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `holding_structure` | enum | `"Applicable"` \| `"Not applicable"` | Whether conglomerate analysis was triggered |
| `sotp_value` | float ($M) \| null | >= 0 or null | Sum-of-the-parts value (null if N/A) |
| `holding_discount_pct` | float \| null | 0-100 or null | Actual holding discount % (null if N/A) |
| `reasonable_discount_pct` | float \| null | 18-40 or null | Estimated reasonable discount (null if N/A) |
| `excess_discount_pct` | float \| null | any or null | Actual minus reasonable (null if N/A) |
| `holding_type` | enum \| null | `"Pure holding"` \| `"Hybrid"` \| `"Primarily operating"` \| null | Classification based on visible stake % of SOTP |

## Calibration Parameters (Pre-Analysis)

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `anchored_profit_metric` | string | `"GAAP Net Income"` \| `"Adjusted Net Income (ex-SBC)"` \| `"Operating Income"` | Earnings base for downstream quantitative analysis |
| `anchored_profit_value` | float ($M) | > 0 | Dollar value of anchored metric |
| `anchored_profit_ref` | string | e.g., `"§3 Net Income FY2024"` | Exact data_pack reference |
| `cash_definition` | enum | `"narrow"` \| `"broad"` | Cash scope for balance sheet analysis |
| `cash_value` | float ($M) | >= 0 | Dollar value under selected definition |
| `interim_data` | enum | `"none"` \| `"Q1"` \| `"H1"` \| `"Q3"` | Interim data availability |
| `annualization_coeff` | float | 1.0 \| 2.0 \| 4/3 \| 4.0 | Multiplier for interim annualization |
| `anomalies` | list[string] | <= 3 items | Flagged data anomalies |

## Overall Assessment

| Parameter | Type | Allowed Values | Description |
|-----------|------|---------------|-------------|
| `business_quality_score` | enum | `"A"` \| `"B"` \| `"C"` \| `"D"` | Overall business quality grade |
| `qualitative_conclusion` | enum | `"PASS"` \| `"VETO"` | Gate decision |
| `veto_reason` | string \| null | Free text or null | Reason if VETO |

---

## Scoring Rubric

| Score | Criteria |
|-------|----------|
| **A** | Light-asset, wide moat, excellent management, clean balance sheet, low SBC |
| **B** | Moderate capex, narrow moat, adequate management, manageable risks |
| **C** | Capital-hungry but consistently profitable, or narrow moat with identified risks |
| **D** | VETO recommended — multiple red flags, destroying value, or fundamental concerns |

---

*Shared Qualitative Assessment v1.0 | Output Schema*
