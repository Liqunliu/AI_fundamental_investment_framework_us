# Pillar 2: Operating Maintenance — Reference Guide

> **Load this file** before executing Pillar 2 analysis.

---

## Overview

Pillar 2 assesses whether the company can **maintain its asset base** without rapidly burning cash. A stock trading below NAV is only a good cigar butt if the company is not hemorrhaging cash — otherwise the NAV floor erodes before the value can be realized.

Three conditions (must pass **2 of 3**):

| # | Condition | Threshold |
|---|-----------|-----------|
| 1 | Latest fiscal year FCF > 0 | Positive free cash flow |
| 2 | Asset Burn Rate meets tier threshold | T0: ≥0%, T1: ≥5%, T2: ≥10% |
| 3 | 3+ consecutive years of positive operating cash flow | OCF > 0 for 3 straight years |

---

## Condition 1: Free Cash Flow > 0

### Formula
```
FCF = Operating Cash Flow − Capital Expenditures
```

### Data Sources (US-GAAP)

| Component | US-GAAP | yfinance Key |
|-----------|---------|-------------|
| Operating Cash Flow | Net cash from operating activities | `Operating Cash Flow` |
| Capital Expenditures | Purchases of property, plant & equipment | `Capital Expenditure` |

### Interpretation

- **FCF > 0**: Company generates more cash from operations than it spends on maintenance/growth capex. PASS.
- **FCF < 0**: Company is a net cash consumer. Does not automatically VETO — check if negative FCF is due to one-time growth capex vs structural unprofitability.

### FCF Conversion Ratio (Supplementary)

```
FCF_Conversion = FCF / Net_Income
```

| Ratio | Interpretation |
|-------|---------------|
| > 1.0 | Excellent — cash generation exceeds reported earnings |
| 0.8 – 1.0 | Good — strong cash conversion |
| 0.5 – 0.8 | Acceptable — some working capital consumption |
| < 0.5 | Warning — earnings quality concern |

---

## Condition 2: Asset Burn Rate (ABR)

### Formula
```
ABR = (Cash_t − Cash_t-1) / Cash_t-1
```

Where:
- `Cash_t` = Most recent year-end cash & equivalents
- `Cash_t-1` = Prior year-end cash & equivalents

### Tiered Thresholds

| Tier | PASS | WARNING | VETO |
|------|------|---------|------|
| T0 | ABR ≥ 0% | −5% ≤ ABR < 0% | ABR < −5% |
| T1 | ABR ≥ 5% | −5% ≤ ABR < 5% | ABR < −5% |
| T2 | ABR ≥ 10% | 0% ≤ ABR < 10% | ABR < 0% |

### Rationale for Tiered Thresholds

- **T0** (net cash exceeds market cap): Can tolerate mild cash burn since the safety cushion is enormous
- **T1** (cash exceeds IBD): Moderate tolerance — needs cash to service remaining obligations
- **T2** (adjusted current assets): Strictest — needs positive cash generation because the asset base includes illiquid items (AR, inventory) that can deteriorate

### ABR Adjustments

When ABR shows negative (cash declining), investigate the **source** of cash reduction:
- **Share buybacks**: If cash declined due to buybacks, add back buyback amount. Buybacks are value-accretive for below-book stocks.
- **Debt repayment**: If cash declined due to debt reduction, partially acceptable (improves T1 NAV).
- **Operating losses**: Genuine concern — check if temporary (one-time charges) or structural.
- **Acquisitions**: May be concerning if paid premium; check goodwill creation.

### Adjusted ABR Formula (when applicable)
```
ABR_Adjusted = (Cash_t − Cash_t-1 + Buybacks_t + DebtRepaid_t) / Cash_t-1
```

---

## Condition 3: Consecutive Positive OCF

### Threshold
```
OCF > 0 for at least 3 consecutive most-recent years
```

### Data Extraction

Extract OCF from each available year in the cash flow statement. Count backwards from the most recent year — how many consecutive years show positive OCF?

| Years Positive | Assessment |
|---------------|-----------|
| 5+ years | Excellent operating consistency |
| 3-4 years | Acceptable — meets minimum |
| 2 years | Warning — borderline |
| 0-1 years | Fail — unreliable operations |

---

## SG&A Trend Analysis (Supplementary)

Check whether the company is maintaining cost discipline:

```
SGA_Ratio = SG&A_Expenses / Total_Revenue
```

| Trend (3-year) | Assessment |
|----------------|-----------|
| Declining | Positive — improving efficiency |
| Stable (±2 pct pts) | Neutral |
| Rising | Warning — potential cost bloat |

---

## Working Capital Changes (Supplementary)

Monitor working capital for signs of deterioration:

```
Working_Capital = Current_Assets − Current_Liabilities
WC_Change = WC_t − WC_t-1
```

Concerning patterns:
- **Rising AR with flat/declining revenue**: Collection problems
- **Rising inventory with declining revenue**: Potential write-down risk
- **Rising payables disproportionate to revenue**: Stretching suppliers (liquidity stress)

---

## Pillar 2 Output Format

```markdown
### Pillar 2: Operating Maintenance

**Condition 1 — FCF**: $X,XXX.XM → [PASS / WARNING]
  Formula: OCF $X,XXX.XM − Capex $X,XXX.XM = FCF $X,XXX.XM
  FCF Conversion Ratio: X.XX → [Excellent / Good / Acceptable / Warning]

**Condition 2 — Asset Burn Rate**: XX.X% → [PASS / WARNING / VETO]
  Formula: (Cash $X,XXX.X − Prior Cash $X,XXX.X) / Prior Cash $X,XXX.X
  Tier: [T0 / T1 / T2], Required: [≥0% / ≥5% / ≥10%]
  [If negative ABR, explain source of cash decline]

**Condition 3 — Consecutive OCF**: X years → [PASS / WARNING]
  OCF history: [Year-4: $X,XXXM, Year-3: $X,XXXM, Year-2: $X,XXXM, Year-1: $X,XXXM, Latest: $X,XXXM]

**Pillar 2 Overall**: [PASS (2/3 or 3/3) / FAIL (0/3 or 1/3)]

Supplementary:
- SG&A/Revenue trend: [Declining / Stable / Rising]
- Working capital change: $X,XXXM → [Healthy / Concerning]
```

---

*Reference file for Cigar Butt Deep Value Strategy — Pillar 2*
