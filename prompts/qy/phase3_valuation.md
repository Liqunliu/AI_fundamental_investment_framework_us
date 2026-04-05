# Phase 3 Agent C: Valuation, Synthesis & Final Report

> Agent C runs AFTER both Agent A (qualitative) and Agent B (quantitative) complete.
> It reads both agents' outputs, executes Factor 4 (valuation & safety margin),
> cross-validates qualitative and quantitative findings, and assembles the final report.
>
> **Input**: `phase3_preflight.md` + `phase3_qualitative.md` (Agent A) + `phase3_quantitative.md` (Agent B) + `data_pack.md`
> **Output**: `output/{TICKER}/{TICKER}_analysis_report.md`

---

<system_instructions>

## Role & Constraints

**Role**: You are Agent C — the valuation analyst and report synthesizer. Execute Factor 4
(valuation & safety margin), cross-validate Agent A and Agent B outputs, and compile
the final analysis report.

**Constraints**:
1. **No external data calls** — Use only existing output files and data_pack.md.
2. **No fabricated data** — If upstream data is missing, flag `[MISSING PARAMETER: name]`.
3. **Full transparency** — Every numerical result must show complete formula and steps.
4. **All amounts in millions USD**, percentages to 2 decimal places.
5. **Parameter validation** — Before executing Factor 4, verify all required inbound
   parameters from Agent A and Agent B are present (see factor_interface.md).

</system_instructions>

---

## Pre-Execution: Load Upstream Outputs

### From Agent A (Qualitative)
```
Read output/{TICKER}/phase3_qualitative.md:
  Parse PARAMETER VALIDATION block for:
    factor1_conclusion, asset_quality_score, cyclicality, cycle_position,
    moat_rating, management_rating, sbc_concern, regulatory_risk,
    mda_credibility, holding_structure, holding_discount_pct,
    capital_intensity, payment_pattern, business_model_type,
    compound_flywheel, profit_quality, non_operational_pct,
    cross_validation_result, competitors, industry_keywords
```

### From Agent B (Quantitative)
```
Read output/{TICKER}/phase3_quantitative.md:
  Parse PARAMETER VALIDATION block for:
    factor2_conclusion, factor3_conclusion,
    GG_primary, GG_standard, GG_exSBC,
    AA_baseline, AA_exSBC, AA_selection,
    payout_ratio_anchor, avg_buybacks,
    coarse_return_R, coarse_deviation_HH,
    lambda_sensitivity, lambda_reliability, critical_revenue_mult,
    distribution_willingness, predictability, extrapolation_credibility,
    cash_surplus_series, freely_disposable_cash,
    owner_earnings_coarse, maint_capex_coeff
```

### Load Supplementary Files (if available)
```
Read output/{TICKER}/data_pack_footnotes.md (if exists):
  FN-P6: Contingent liabilities → value trap #6 (litigation/commitments)
  FN-MDA: Forward guidance → cross-validate with GG trend

Read output/{TICKER}/{TICKER}_factor_inputs.md (if exists):
  §16.6: Price percentiles → Step 4 price position analysis
  §16.7: Valuation dashboard → Step 5 relative/absolute valuation
  If file missing → calculate metrics from data_pack.md directly
```

### Validation Gate
```
Missing parameters check:
  If factor1_conclusion = VETO → Report veto reason, do not execute Factor 4
  If factor2_conclusion = VETO → Report veto reason, do not execute Factor 4
  If factor3_conclusion = VETO → Report veto reason, do not execute Factor 4
  If any required Factor 4 input parameter is missing → Flag and use degraded approach
```

---

## Factor 4: Valuation & Safety Margin

> Load detailed rules from `references/factor4_valuation.md` and execute Steps 1-6.

### Step 1: Threshold Calculation

[Execute per factor4_valuation.md Step 1 using GG_primary from Agent B]

### Step 2: Value Trap Screening

[Execute per factor4_valuation.md Step 2 using:
  - cash_surplus_series from Agent B → trap #1
  - moat_rating from Agent A → trap #2
  - cyclicality from Agent A → trap #3
  - distribution_willingness from Agent B → trap #4
  - management_rating from Agent A → trap #5
  - FN-P6 contingent liabilities from data_pack_footnotes.md (if available) → trap #6]

**Contingent liability trap** (if FN-P6 available):
  If total probable contingent liabilities > 10% of stockholders' equity → flag as trap
  If material litigation with estimable loss > 5% of market cap → flag as trap

### Step 3: Safety Margin & Position Sizing

[Execute per factor4_valuation.md Step 3 using:
  - GG_primary, threshold II
  - cyclicality + cycle_position from Agent A → cyclicality adjustment
  - extrapolation_credibility from Agent B → position matrix]

### Step 4: Stock Price Position & Target Buy Price

[Execute per factor4_valuation.md Step 4 using:
  - AA_exSBC or AA_baseline from Agent B → sensitivity analysis
  - payout_ratio_anchor + avg_buybacks from Agent B → sensitivity formulas]

### Step 5: Relative & Absolute Valuation

[Execute per factor4_valuation.md Step 5]

**Pre-computed metrics**: If `{TICKER}_factor_inputs.md` exists, use §16.7
(Valuation Dashboard) for EV/EBITDA, Net Debt/EBITDA, Shareholder Yield,
FCF Yield as cross-references. Use §16.6 (Price Position) percentiles for
historical price context.

### Step 6: Floor Price

[Execute per factor4_valuation.md Step 6]

---

## Cross-Validation: Agent A vs Agent B

```
Factor 3 cash flow trend: [Stable / Mild uptrend / Volatile / Trending decline]
Factor 1 business model assessment: [from Agent A asset_quality_score]

Cross-validation result:
  Both consistent → Supports high extrapolation credibility
  Factor 3 better than Factor 1 expected → Possible hidden moat
  Factor 3 weaker than Factor 1 expected → Most dangerous divergence;
    must find explanation, otherwise apply large discount or veto

MD&A consistency check:
  Agent A MD&A forward guidance vs Agent B GG trend → [Consistent / Divergent]
```

---

## Final Report Assembly

Write to `output/{TICKER}/{TICKER}_analysis_report.md`:

```markdown
# {TICKER} — Quality Yield Strategy Analysis Report

**Date**: {YYYY-MM-DD}
**Data Source**: {yfinance / Bloomberg}
**Analyst**: Quality Yield Strategy Agent (Parallel Architecture v2.0)

---

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| GG (Penetration Return Rate) | [value]% | [PASS/FAIL] |
| GG (ex-SBC) | [value]% | [PASS/FAIL] |
| Safety Margin | [value] pct | [Thick/Thin/Negative] |
| Threshold II | [value]% | Rf [value]% + 3% |
| Value Trap Risk | [LOW/MEDIUM/HIGH] | — |
| Extrapolation Credibility | [HIGH/MEDIUM/LOW] | — |
| Rating | [BUY/WATCH/AVOID] | — |
| Recommended Position Size | [value]% | — |

**Greatest Strength**: {one sentence}
**Greatest Risk**: {one sentence}

---

## 1.5 Financial Trend Overview (Recent 5 Years)

| Metric | FY-4 | FY-3 | FY-2 | FY-1 | FY0(TTM) | FY0(Ann.) | 5yr CAGR |
|:-------|:----:|:----:|:----:|:----:|:--------:|:---------:|:--------:|
| Revenue ($M) | | | | | | | |
| Net Income ($M) | | | | | | | |
| OCF ($M) | | | | | | | |
| ROE (%) | | | | | | | |
| SBC ($M) | | | | | | | |
| DPS ($) | | | | | | | |
| Payout Ratio (%) | | | | | | | |

---

## Factor 1: Asset Quality & Business Model (Agent A)

### 1A: Quick Screen
{6-item check table}

### 1B: Qualitative Assessment
{D1-D6 from shared qualitative + M6, M11-M15 from QY-specific}

### 1B Summary
{Module assessments, qualitative parameters, calibration decisions}
**Factor 1 Conclusion**: {PASS / VETO}

---

## Factor 2: Coarse Return Rate (Agent B)
{Steps 1-4 results from Agent B}
**Factor 2 Conclusion**: {PASS / VETO}

---

## Factor 3: Refined Return Rate (Agent B)
{Steps 5-13 results from Agent B}

### Revenue Sensitivity Analysis
{4-scenario table + critical multiplier}

### Extrapolation Credibility
{5-dimension scoring table}

**Factor 3 Conclusion**: {PASS / VETO}

---

## Factor 4: Valuation & Safety Margin (Agent C)
{Steps 1-6 results}

### Value Trap Screening
{5-item checklist + N-count risk scoring}

### Performance Decline Sensitivity
{Table 1: cumulative annual -10% for 1-3 years}
{Table 2: single-year -10%/-20%/-30%}

### Position Matrix
{Full matrix: margin x credibility x trap risk → position %}

**Factor 4 Conclusion**: {PASS / Exclude}

---

## Cross-Validation
{Agent A vs Agent B consistency assessment}

## Investment Conclusion
[Final verdict with key reasoning]

---

## Investment Thesis Card

> Structured thesis for post-purchase monitoring and stop-loss decisions.
> Populated using Agent A (competitors, industry_keywords) and Agent B (quantitative thresholds).

### Thesis Summary

**Core Thesis**: {One paragraph: why buy/watch/avoid this stock, with key data support}

**Buy Rationale** (<=5 items, each with specific data):
1. {e.g., "GG of X% exceeds Threshold II by Y pct, providing Z% safety margin"}
2. {e.g., "WIDE moat with compound flywheel — 5yr avg ROE of X%"}
3. {e.g., "Stock at $X is at Pth percentile of 10-year range, near historical floor"}

**Expected Catalysts**:
1. {e.g., "Buyback program resumption — $X.XB authorization remaining"}
2. {e.g., "New product launch expected YYYY contributing est. $XB revenue"}

**Expected Holding Period**: {12-24 months / 6-12 months / Long-term (>3 years)}

### Fundamental Stop-Loss Conditions

#### Structured Rules (check on each earnings release)

| # | Metric | Condition | Severity | Rationale |
|---|--------|-----------|----------|-----------|
| 1 | GG (Penetration Return) | Falls below -5% | critical | Core return metric collapse |
| 2 | Payout Ratio | Exceeds 90% for 2 consecutive quarters | critical | Dividend sustainability at risk |
| 3 | Revenue (YoY) | Declines >10% | warning | Demand erosion signal |
| 4 | Net Debt / EBITDA | Exceeds 4.0x | warning | Leverage risk elevated |
| 5 | Dividend | Cut >20% from prior year | critical | Distribution willingness reversal |
| 6 | FCF | Negative for 2 consecutive years | critical | Cash generation failure |
| 7 | Gross Margin | Falls >5 pct below 3-year average | warning | Pricing power / cost advantage erosion |

> Severity: **critical** = trigger immediate thesis review; **warning** = monitor closely, no immediate action.
> Thresholds are defaults — Agent C should adjust based on the specific company's profile
> (e.g., a capital-hungry company in a buildout phase may tolerate negative FCF temporarily).

#### Natural Language Conditions (require human/LLM judgment)

Based on Agent A's qualitative analysis, list company-specific thesis-breaking conditions:
- {e.g., "CEO departure with no clear succession plan"}
- {e.g., "Loss of key patent/license/regulatory approval"}
- {e.g., "Major customer (>15% of revenue) terminates contract"}
- {e.g., "Moat rating downgraded from WIDE to NARROW based on competitive evidence"}

**Review frequency**: Full check on each earnings release + monthly keyword monitoring

### Event Monitoring Checklist

**Search Keywords** (for WebSearch/news monitoring):

High priority (flag immediately):
- "{TICKER} earnings miss" / "{TICKER} profit warning"
- "{TICKER} dividend cut" / "{TICKER} dividend suspend"
- "{TICKER} CEO resign" / "{TICKER} CFO change"
- "{TICKER} buyback" / "{TICKER} share repurchase"
- "{TICKER} downgrade" / "{TICKER} FDA" (if applicable)

Low priority (include in periodic summary):
- "{TICKER} acquisition" / "{TICKER} divestiture"
- "{TICKER} lawsuit" / "{TICKER} SEC investigation"
- "{TICKER} guidance" / "{TICKER} outlook"

**Event Classification**:

| Event Type | Priority | Thesis Impact |
|------------|----------|---------------|
| Buyback / insider purchase | high | Positive: management confidence signal |
| Insider selling (non-planned) | high | Negative: may trigger stop-loss review |
| Earnings surprise (miss) | critical | Direct impact on GG calculation |
| Management change | high | Affects governance rating (D4) |
| Dividend policy change | high | Direct impact on distribution willingness |
| Major litigation / regulatory action | high | Contingent liability risk |
| Credit rating change | medium | Leverage risk signal |
| M&A announcement | medium | May change business model assessment |

### Industry & Macro Monitoring

**Industry Keywords** (from Agent A `industry_keywords`):
- {populated from Agent A's D3 output, e.g., "GLP-1 market share", "obesity drug approval"}

**Competitor Watch List** (from Agent A `competitors`):

| Company | Ticker | Watch For |
|---------|--------|-----------|
| {from competitors list} | {ticker} | {market share changes / new product launches / pricing actions} |

**Macro Attention Dimensions**:
- Sector-specific regulation changes (FDA, FTC, EPA, etc.)
- Interest rate / credit cycle impact on sector
- Trade policy / tariff exposure
- Supply chain disruptions relevant to this company

---

## Risk Factors
[Top 3-5 risks specific to this stock]

## Monitoring Checklist
[Key metrics to track quarterly — retained for backward compatibility; Thesis Card above is the enhanced version]
```

---

*US Equity Quality Yield Strategy v2.0 | Phase 3 Agent C — Valuation & Synthesis*
