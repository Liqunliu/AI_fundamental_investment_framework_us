# Fact Check: 21-Item Verification — Reference Guide

> **Load this file** before executing the Fact Check.

---

## Overview

The Fact Check is a 21-item verification that screens for hidden risks not captured by the 3-pillar quantitative framework. Items 1-19 are core checks (any single VETO = automatic D rating). Items 20-21 are bonus items that can upgrade a B rating to B+.

Each item is tagged as `[AUTOMATED]` (computable from yfinance data) or `[MANUAL]` (requires SEC filing review / Bloomberg terminal).

---

## Rating Summary

| Rating | Criteria | Position Impact |
|--------|----------|----------------|
| **A** | All items pass, no warnings | Full position per tier rules |
| **B** | Core items pass, 1-2 warning items | 80% of max position |
| **B+** | Base B + Bonus ≥ 2 points | Full position per tier rules |
| **C** | 3+ warning items OR 1 item approaching veto | 50% of max position |
| **D** | Any automatic-veto item triggered | **DO NOT INVEST** |

---

## Asset Quality (Items 1-7)

### Item 1: Restricted Cash Ratio `[MANUAL]`

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Restricted Cash Ratio | Restricted Cash / Total Cash | VETO: > 20% |

**Data source**: 10-K Balance Sheet footnotes, Note on Cash & Equivalents
**Where to find**: Search 10-K for "restricted cash", "pledged", "segregated"
**yfinance**: Not directly available (may appear in `balance_sheet` for some companies)

**Impact on NAV**: Subtract restricted cash from Cash & Equivalents in all T-level calculations.

---

### Item 2: Pledged Assets `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Core operating assets pledged as collateral | VETO: Core assets pledged |

**Data source**: 10-K footnotes on debt covenants, collateral arrangements
**Where to find**: Search for "pledged", "collateral", "secured", "lien"

**Types of pledged assets**:
- Property/equipment pledged for mortgage → Moderate concern
- Inventory/receivables pledged for revolving credit → Common, less concerning if facility is undrawn
- Subsidiary shares pledged → Serious concern for Type B analysis

---

### Item 3: Goodwill Ratio `[AUTOMATED]`

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Goodwill Ratio | Goodwill / Total Assets | WARNING: 15-30%; VETO: > 30% |

**yfinance**: `Goodwill` / `Total Assets` from balance sheet

**Context matters**:
- Financial services: 5-10% typical
- Technology: 20-40% common (acquisitive)
- Manufacturing: 10-20% typical
- If goodwill > 30%, check Item #4 for impairment history

---

### Item 4: Goodwill Impairment History `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Material goodwill impairment in last 3 years | WARNING: Any impairment > 5% of goodwill |

**Data source**: 10-K Income Statement footnotes, Note on Goodwill
**Where to find**: Search for "impairment", "goodwill impairment", "write-down"

**Concern**: Goodwill impairment signals that past acquisitions destroyed value. If goodwill is high (Item #3) AND impairment occurred, the remaining goodwill balance may be overstated.

---

### Item 5: Accounts Receivable Quality `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| AR > 90 days as % of total AR | VETO: > 30% |
| Related-party AR as % of total AR | VETO: > 20% |

**Data source**: 10-K AR aging schedule (footnotes), Related-party transactions note
**yfinance**: Only total AR available; aging requires SEC filings

**DSO (Days Sales Outstanding)** as proxy:
```
DSO = (Accounts Receivable / Revenue) × 365
```
DSO > 90 days warrants investigation.

---

### Item 6: Inventory Turnover `[AUTOMATED]`

| Metric | Formula | Threshold |
|--------|---------|-----------|
| DIO Trend | DIO = (Inventory / COGS) × 365 | VETO: Rising 3 consecutive years AND > 50% above peers |

**yfinance**: Computable from `Inventory` and `Cost Of Revenue` in financials

**Calculation**:
```
DIO = (Average_Inventory / COGS) × 365
```

**Peer comparison**: Compare DIO to 3-5 industry peers. > 50% deviation = significant concern.

---

### Item 7: Intangible Asset Reasonableness `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Unidentifiable intangible assets / Total Assets | VETO: > 40% |

**Data source**: 10-K Balance Sheet footnotes on intangible assets
**Where to find**: Search for "intangible", "identifiable", "amortization schedule"

**Key distinction**:
- Identifiable intangibles (patents, licenses, customer relationships): Have amortization schedules, more reliable
- Unidentifiable intangibles (assembled workforce, synergies): Higher risk of overstatement

---

## Liability Risk (Items 8-13)

### Item 8: Off-Balance-Sheet Liabilities `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Off-BS liabilities / Market Cap | VETO: > 15% |

**Data source**: 10-K footnotes on commitments, contingencies, VIEs
**Where to find**: "Off-balance sheet", "variable interest entity", "special purpose"

**Common off-BS items**: Operating lease commitments (pre-ASC 842), purchase obligations, guarantees

---

### Item 9: Capital Commitments `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Capital commitments / Net Cash | VETO: > 30% |

**Data source**: 10-K footnotes on contractual obligations
**Where to find**: "Capital commitments", "contractual obligations", "purchase commitments"

---

### Item 10: Guarantees / Cross-Guarantees `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Material guarantees to related parties | VETO: Yes |

**Data source**: 10-K related-party footnotes, guarantee footnotes
**Where to find**: "Guarantee", "cross-guarantee", "indemnification"

---

### Item 11: Pension Deficit `[MANUAL]`

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Pension Deficit / Market Cap | (PBO − Plan Assets) / Market Cap | VETO: > 10% |

**Data source**: 10-K pension footnote (ASC 715)
**Where to find**: "Defined benefit", "pension", "projected benefit obligation"

---

### Item 12: Environmental / Legal Liabilities `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Material litigation with uncertain amounts | VETO: Material + uncertain |

**Data source**: 10-K legal proceedings, contingencies footnote (ASC 450)
**Where to find**: "Legal proceedings", "contingencies", "litigation", "environmental remediation"

**US-specific**: SEC enforcement actions, DOJ investigations, state AG actions

---

### Item 13: Other Payables Anomaly `[AUTOMATED]`

| Metric | Formula | Threshold |
|--------|---------|-----------|
| Other Payables / Total Liabilities | Accrued expenses, other payables | VETO: > 30% without explanation |

**yfinance**: `Other Current Liabilities` + `Other Non Current Liabilities` from balance sheet

**Red flags**: Sudden spike in other payables, unclear descriptions, related-party payables

---

## Operating Quality (Items 14-19)

### Item 14: Related-Party Transactions `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Related-party revenue / Total Revenue | VETO: > 30% |
| Pricing deviation from market rates | VETO: Material deviation |

**Data source**: 10-K related-party footnote, proxy statement (DEF 14A)
**US-specific**: SEC requires detailed related-party disclosure under ASC 850

---

### Item 15: Revenue Concentration `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Top 5 customers / Total Revenue | VETO: > 60% without long-term contracts |

**Data source**: 10-K revenue disaggregation, customer concentration footnote
**Where to find**: "Major customers", "significant customers", "concentration"

---

### Item 16: Q4 Revenue Spike `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Q4 Revenue / Annual Revenue | VETO: > 40% |

**Data source**: 10-Q quarterly revenue comparison
**yfinance**: Can be computed from quarterly financials if available

**Concern**: Extreme Q4 seasonality may indicate channel stuffing or aggressive revenue recognition.

---

### Item 17: Audit Opinion `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Qualified / Adverse / Disclaimer opinion | VETO: Any non-clean opinion |
| Going concern emphasis | VETO: Going concern |

**Data source**: 10-K auditor's report (first few pages)
**US-specific**: PCAOB-registered auditors required for US public companies

**Additional check**: Recent auditor change (past 2 years) without clear reason = WARNING

---

### Item 18: Management Integrity `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| History of fraud, insider trading, self-dealing | VETO: Confirmed incidents |

**Data source**: SEC EDGAR (enforcement actions), proxy statement, news
**Where to check**: SEC AAER database, short-seller reports (Hindenburg, Muddy Waters, Citron)

---

### Item 19: Government Subsidy Dependence `[MANUAL]`

| Metric | Threshold |
|--------|-----------|
| Subsidies / Revenue (3 consecutive years) | VETO: > 50% |

**Data source**: 10-K revenue disaggregation, government contracts
**US context**: Less common than in other markets; watch for defense contractors, renewable energy credits

---

## Bonus Items (Items 20-21)

### Item 20: Listed Subsidiary / Associate Equity Value `[MANUAL]`

| Coverage Ratio | Formula | Points |
|---------------|---------|--------|
| > 100% | Σ(Subsidiary MktCap × Ownership%) / Parent MktCap | +3 pts |
| 50-100% | — | +2 pts |
| 20-50% | — | +1 pt |
| < 20% | — | +0 pts |

**Data source**: Bloomberg OWN<GO>, SEC 13F filings, parent 10-K investment footnote
**Relevance**: Directly relevant for Type B (Holding Company) classification

---

### Item 21: Ownership & Governance Quality `[MANUAL]`

| Factor | Threshold | Points |
|--------|-----------|--------|
| High insider ownership | > 10% | +3 pts |
| Institutional ownership | > 70% | +2 pts |
| Activist investor involved | Any 13D filing | +1 pt |

**Data source**: DEF 14A (insider ownership), 13F filings (institutional), Schedule 13D (activist)
**yfinance**: `info.get('heldPercentInsiders')`, `info.get('heldPercentInstitutions')`

---

## Fact Check Output Format

```markdown
### Fact Check: 21-Item Verification

#### Asset Quality (Items 1-7)
| # | Item | Value | Status | Source |
|---|------|-------|--------|--------|
| 1 | Restricted Cash Ratio | [MANUAL] | — | 10-K footnote |
| 2 | Pledged Assets | [MANUAL] | — | 10-K footnote |
| 3 | Goodwill/Assets | XX.X% | [OK/WARNING/VETO] | [AUTOMATED] |
| 4 | Goodwill Impairment | [MANUAL] | — | 10-K footnote |
| 5 | AR Quality (>90 days) | [MANUAL] | — | 10-K aging schedule |
| 6 | Inventory (DIO trend) | XX days | [OK/WARNING/VETO] | [AUTOMATED] |
| 7 | Intangible Assets | [MANUAL] | — | 10-K footnote |

#### Liability Risk (Items 8-13)
| # | Item | Value | Status | Source |
|---|------|-------|--------|--------|
| 8 | Off-BS Liabilities | [MANUAL] | — | 10-K footnote |
| 9 | Capital Commitments | [MANUAL] | — | 10-K footnote |
| 10 | Guarantees | [MANUAL] | — | 10-K footnote |
| 11 | Pension Deficit | [MANUAL] | — | 10-K footnote |
| 12 | Legal Liabilities | [MANUAL] | — | 10-K/8-K |
| 13 | Other Payables | XX.X% | [OK/WARNING/VETO] | [AUTOMATED] |

#### Operating Quality (Items 14-19)
| # | Item | Value | Status | Source |
|---|------|-------|--------|--------|
| 14 | Related-Party | [MANUAL] | — | 10-K/DEF 14A |
| 15 | Revenue Concentration | [MANUAL] | — | 10-K |
| 16 | Q4 Revenue Spike | [MANUAL] | — | 10-Q |
| 17 | Audit Opinion | [MANUAL] | — | 10-K auditor |
| 18 | Management Integrity | [MANUAL] | — | SEC/news |
| 19 | Subsidy Dependence | [MANUAL] | — | 10-K |

#### Bonus (Items 20-21)
| # | Item | Value | Points | Source |
|---|------|-------|--------|--------|
| 20 | Subsidiary Value | [MANUAL] | +X pts | Bloomberg/13F |
| 21 | Ownership Quality | [MANUAL] | +X pts | DEF 14A/13D |

**Automated Items Checked**: [X/21]
**Manual Items Pending**: [Y/21]
**Veto Items**: [List any]
**Warning Items**: [List any]
**Bonus Points**: [X]

**Fact Check Rating**: [A / B / B+ / C / D]
**Rationale**: [1-2 sentence summary]
```

---

*Reference file for Cigar Butt Deep Value Strategy — Fact Check*
