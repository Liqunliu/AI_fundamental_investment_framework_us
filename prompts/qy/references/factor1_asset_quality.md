# Factor 1: Asset Quality & Business Model — Detailed Analysis Rules

> Reference file for Phase 3 executor. Load when executing Factor 1. All amounts in millions USD.
>
> **Prerequisite**: The shared qualitative assessment must be completed first.
> Read `output/{TICKER}/qualitative_report.md` (or execute the qualitative assessment inline)
> to obtain D1-D6 dimensional ratings and calibration parameters before proceeding.
> See `prompts/shared/qualitative/qualitative_assessment.md` for the full framework.

---

## Factor 1A: Five-Minute Quick Screen

**Instruction**: Using only available data, evaluate each of the 6 items below.
If ANY item is "YES" → output "VETO" and stop all subsequent analysis.

| # | Check Item | Criteria | Result |
|---|-----------|----------|--------|
| 1 | Abnormal audit opinion | Most recent annual report: qualified/adverse/disclaimer/going concern emphasis → VETO | [YES/NO] |
| 2 | Frequent auditor changes | Changed auditors ≥ 2 times in past 5 years, especially from Big 4 to smaller firm → VETO | [YES/NO] |
| 3 | Financial fraud or major violations | Company or controlling shareholder has SEC enforcement actions, accounting restatements, class action settlements → VETO | [YES/NO] |
| 4 | Cannot understand | Cannot explain in one sentence: revenue source, cost structure, profit generation → VETO | [YES/NO] |
| 5 | Unproven business model | Not tested through at least 1 full economic cycle, or underwent major pivot → VETO | [YES/NO] |
| 6 | Major insider red flags | Insider selling > 20% of holdings / SEC investigation / criminal charges / poison pill adoption → VETO | [YES/NO] |

If all pass, output initial profile:

```
Capital intensity: [capital-light / capital-hungry]
Payment pattern: [prepaid / subscription / post-delivery / advance-funded]
Cyclicality: [strong-cycle / weak-cycle / non-cycle]
Moat intuition: [one sentence]
```

---

## Factor 1B: Deep Analysis — QY-Specific Modules

> **Shared qualitative dimensions (D1-D6) are loaded from the shared module.**
> This file defines only the QY-specific balance sheet quality modules (M6, M11-M15)
> that supplement the shared qualitative assessment.
>
> When executing Factor 1B:
> 1. Load shared qualitative output from `output/{TICKER}/qualitative_report.md`
>    (or execute `prompts/shared/qualitative/qualitative_assessment.md` inline)
> 2. Import calibration parameters: anchored profit metric, cash definition, anomalies
> 3. Import dimensional ratings: D1 (capital/payment/model), D2 (moat), D3 (cycle/regulatory),
>    D4 (management), D5 (MD&A), D6 (complex structure)
> 4. Execute M6 and M11-M15 below for QY-specific balance sheet analysis

### Module 6: Human Capital Dependency

Analysis:
- Core competitiveness reliance on key talent: [High >50% / Medium 30-50% / Low <30%]
- Whether competitive advantage has been systematized (codified into processes, IP, platforms)

Output: `[System-type / Talent-type]`

### Module 11: Receivables Quality (from §4 Balance Sheet)

- Accounts receivable / Revenue ratio trend (5 years)
- Days sales outstanding (DSO) trend
- Allowance for doubtful accounts / Total AR ratio
- Red flag: AR growing faster than revenue

### Module 12: Inventory Analysis (from §4, if applicable)

- Inventory / COGS ratio trend
- Days inventory outstanding trend
- Inventory write-downs (from §3 or footnotes)
- N/A for service/platform companies

### Module 13: Fixed Assets & Capex (from §4, §5)

- PP&E / Total assets ratio
- Capex / Revenue ratio trend
- Capex / Depreciation ratio (> 1.5 = expanding, < 0.8 = underinvesting)
- US-specific: Right-of-use assets (ASC 842 operating leases)

### Module 14: Intangible Assets & Goodwill (from §4)

- Goodwill / Total assets ratio
- Goodwill / Equity ratio (> 50% = significant acquisition risk)
- Any goodwill impairments in past 5 years
- US-specific: R&D capitalization vs. expense (software companies per ASC 985-20 / ASC 350-40)

### Module 15: Stock-Based Compensation Assessment (US-Specific)

- SBC / Revenue ratio trend
- SBC / Net Income ratio (> 30% = significant dilution concern)
- Share count dilution trend (5 years)
- Buyback offset: Does the company buy back enough to offset SBC dilution?
- Net dilution = shares issued (SBC) - shares repurchased

Output:
```
SBC Concern Level: [LOW / MODERATE / HIGH]
SBC/Revenue: [value]%
SBC/Net Income: [value]%
Net Share Dilution (5-year): [value]%
Buyback Offset: [YES - fully offset / PARTIAL / NO]
```

---

## Factor 1B Summary Output

> Combine shared qualitative ratings (D1-D6) with QY-specific modules (M6, M11-M15).

```
Shared qualitative assessment (from qualitative_report.md):
  Data validation & calibration: Anomalies [<=3 items], Profit anchor [result], Cash definition [narrow/broad]
  D1 — Business model: [capital intensity] + [payment pattern] + [classification]
  D2 — Moat: [WIDE/NARROW/NONE], type: [Business] xxx + [Technical] xxx, flywheel: [YES/NO]
  D3 — Cyclicality: [strong-cycle/weak-cycle/non-cycle], Regulatory: [Favorable/Neutral/Negative]
  D4 — Management: [Excellent/Adequate/Destroying value/Observation]
  D5 — MD&A: Credibility [H/M/L], Impact [Positive/Neutral/Negative]
  D6 — Complex structure: [Applicable (discount X%) / Not applicable]

QY-specific modules:
  Human capital dependency (Module 6): [Favorable / Neutral / Negative], rationale (<=3 points)
  Receivables quality (Module 11): [assessment]
  Inventory analysis (Module 12): [assessment / N/A]
  Fixed assets & capex (Module 13): [assessment]
  Intangible assets & goodwill (Module 14): [assessment]
  SBC assessment (Module 15): [LOW / MODERATE / HIGH]

Qualitative parameters passed to Factor 2/3:
  Capital intensity: [capital-light / capital-hungry]
  Payment pattern: [type]
  Cyclicality: [strong-cycle / weak-cycle / non-cycle]
  Moat type: [Business] xxx + [Technical] xxx (mark "not applicable" if Layer 2 N/A)
  Compound moat flywheel: [YES / NO]
  Management assessment: [Excellent / Adequate / Destroying value / Observation]
  Business model type: [classification]

Calibration decisions passed to Factor 2/3/4 (from Pre-Analysis):
  Anchored profit metric: [metric name] = §3 [line item]
  Cash definition: [narrow / broad]
  Subsequent factors read directly from data_pack tables; reference format:
    Parameter = X $M (§N line_item YYYY column)

Business Model Type: [type from classification]
Asset Quality Score: [A / B / C / D]
  A = High quality (light-asset, wide moat, low SBC, clean balance sheet)
  B = Good quality (moderate capex, narrow moat, manageable SBC)
  C = Acceptable (capital-hungry but profitable, or narrow moat with risks)
  D = Poor quality (VETO recommended — high risk factors)
Factor 1 Conclusion: [PASS / VETO (reason)]
```

---

*US Equity Quality Yield Strategy v2.0 | Factor 1 Reference File*
