# Factor 1: Asset Quality & Business Model — Detailed Analysis Rules

> Reference file for Phase 3 executor. Load when executing Factor 1. All amounts in millions USD.

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

## Factor 1B: Deep Qualitative Analysis

### Module 0: Data Validation & Calibration

**Instruction**: Scan data_pack.md §3-§5, §11, §12, complete these 3 checks.

**(1) Anomaly scan**
- Flag any metrics with YoY change > 30% or margin change > 5 pct
- Brief cause for each (non-recurring items / cycle / M&A / accounting change)
- Max 3 items; if more, list only the most significant

**(2) Profit calibration**
- Determine which profit metric to use for Factor 2/3:
  GAAP Net Income / Adjusted Net Income (ex-SBC) / Operating Income
- For US tech companies: Consider using Adjusted Net Income = Net Income - SBC
  (SBC is a real cost in US tech; GAAP net income may overstate cash earnings)
- State reasoning and anchor: Anchored metric = [X], from §3 line item = [name]

**(3) Cash calibration**
- Determine if broad cash definition should be used (incl. short-term investments, marketable securities)
- US companies often hold large Treasury/bond portfolios (e.g., AAPL, GOOGL)
- State: Using [narrow/broad] cash definition, rationale: [one sentence]

Output:
```
Anomalies found: [≤ 3 items]
Anchored profit metric: [metric name] = §3 [line item]
Cash definition: [narrow/broad], rationale: [one sentence]
```

### Module 1: Capital Intensity

Analysis:
- Annual capital reinvestment required to maintain current earnings level
- Capital investment time structure: one-time → long-term benefit vs. recurring each period
- Criterion: "sustained capital consumed per unit of earnings maintained"

Output: `[capital-light / capital-hungry]`, confirm or revise 1A assessment with evidence

### Module 2: Payment Pattern

Analysis:
- Complete cash flow timeline for a typical transaction (cost incurred → payment received)
- Working capital direction: company advances to customers vs. occupies supplier/customer funds
- US-specific: SaaS subscription models, deferred revenue patterns

Output: `[prepaid / subscription / post-delivery / advance-funded]`, net effect on cash position

### Module 3: Competitive Landscape & Moat

Analysis:
- Market structure: [monopoly / oligopoly / monopolistic competition / perfect competition]
- Porter's Five Forces assessment (brief)
- Moat sources: network effects, switching costs, brand, patents, cost advantages, scale
- Moat durability: [widening / stable / narrowing]
- Competitive threat from AI/technology disruption (US-specific consideration)

Output: Moat rating [WIDE / NARROW / NONE], durability assessment

### Module 4: Business Model Classification

Based on Modules 1-3, classify into one of:

| Type | Characteristics | Typical US Examples |
|------|----------------|---------------------|
| Light-asset platform | Near-zero marginal cost, network effects | META, GOOGL, MSFT (cloud) |
| Light-asset brand | Premium pricing, brand moat | AAPL, NKE, COST |
| Capital-light SaaS | Subscription, high retention, <5% capex/rev | ADBE, CRM, INTU |
| Capital-light fintech | Transaction-based, low capex | V, MA, PYPL |
| Capital-hungry manufacturing | High capex/revenue ratio, cyclical | CAT, DE, GE |
| Capital-hungry retail | Inventory-heavy, store footprint | WMT, TGT, HD |
| Leverage-dependent | Profits from interest spread | JPM, BAC, BRK |

### Module 5: Receivables Quality (from §4 Balance Sheet)

- Accounts receivable / Revenue ratio trend (5 years)
- Days sales outstanding (DSO) trend
- Allowance for doubtful accounts / Total AR ratio
- Red flag: AR growing faster than revenue

### Module 6: Inventory Analysis (from §4, if applicable)

- Inventory / COGS ratio trend
- Days inventory outstanding trend
- Inventory write-downs (from §3 or footnotes)
- N/A for service/platform companies

### Module 7: Fixed Assets & Capex (from §4, §5)

- PP&E / Total assets ratio
- Capex / Revenue ratio trend
- Capex / Depreciation ratio (> 1.5 = expanding, < 0.8 = underinvesting)
- US-specific: Right-of-use assets (ASC 842 operating leases)

### Module 8: Intangible Assets & Goodwill (from §4)

- Goodwill / Total assets ratio
- Goodwill / Equity ratio (> 50% = significant acquisition risk)
- Any goodwill impairments in past 5 years
- US-specific: R&D capitalization vs. expense (software companies)

### Module 9: Stock-Based Compensation Assessment (US-Specific)

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

## Factor 1 Final Output

```
Factor 1A Quick Screen: [PASS / VETO (item #, reason)]
Business Model Type: [type from Module 4]
Capital Intensity: [capital-light / capital-hungry]
Payment Pattern: [type]
Moat: [WIDE / NARROW / NONE] — [one sentence description]
Cyclicality: [strong-cycle / weak-cycle / non-cycle]
SBC Concern: [LOW / MODERATE / HIGH]
Asset Quality Score: [A / B / C / D]
  A = High quality (light-asset, wide moat, low SBC, clean balance sheet)
  B = Good quality (moderate capex, narrow moat, manageable SBC)
  C = Acceptable (capital-hungry but profitable, or narrow moat with risks)
  D = Poor quality (VETO recommended — high risk factors)
Factor 1 Conclusion: [PASS / VETO (reason)]
```

---

*US Equity Turtle Strategy v1.0 | Factor 1 Reference File*
