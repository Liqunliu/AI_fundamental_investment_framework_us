# Pillar 1: Net Asset Cushion — Reference Guide

> **Load this file** before executing Pillar 1 analysis.

---

## Overview

Pillar 1 determines whether a stock's **static net asset value** (realizable balance-sheet assets at a point in time) exceeds its market capitalization. This is the core margin-of-safety test for the cigar butt strategy.

Three tiers of increasing asset quality:

| Tier | Formula | Meaning |
|------|---------|---------|
| **T0** | (Cash & Equivalents − Total Liabilities) / Shares | Net cash far exceeds market cap; extremely safe |
| **T1** | (Cash & Equivalents − Interest-Bearing Debt) / Shares | Moderate; only subtracts hard debt obligations |
| **T2** | (Cash×1.0 + AR×0.85 + Inventory×discount + OtherCA×0.50 − Total Liabilities) / Shares | Wider asset base with haircuts; longer liquidation cycle |

---

## T0 NAV: Pure Net Cash

### Formula
```
T0_NAV_Total = Cash_and_Equivalents − Total_Liabilities
T0_NAV_Per_Share = T0_NAV_Total / Shares_Outstanding
Entry Price < T0_NAV_Per_Share × 0.85
```

### Line-Item Mapping (US-GAAP)

| Concept | US-GAAP Line Item | yfinance Key |
|---------|-------------------|-------------|
| Cash & Equivalents | Cash and cash equivalents | `Cash And Cash Equivalents` |
| Short-term investments | Short-term investments / Marketable securities | `Cash Cash Equivalents And Short Term Investments` |
| Total Liabilities | Total liabilities | `Total Liabilities Net Minority Interest` |

**Include in Cash**: Cash, money market funds, Treasury bills (< 3 months), certificates of deposit
**Exclude from Cash**: Restricted cash (see Fact Check #1), pledged deposits, margin accounts

---

## T1 NAV: Cash vs Interest-Bearing Debt

### Formula
```
T1_NAV_Total = Cash_and_Equivalents − Interest_Bearing_Debt
T1_NAV_Per_Share = T1_NAV_Total / Shares_Outstanding
Entry Price < T1_NAV_Per_Share × 0.80
```

### Interest-Bearing Debt (IBD) Components

| Component | US-GAAP Line | yfinance Key |
|-----------|-------------|-------------|
| Short-term borrowings | Notes payable, Current portion of LT debt | `Current Debt` |
| Long-term debt | Long-term debt, net | `Long Term Debt` |
| Capital lease obligations | Finance lease liabilities (ASC 842) | Included in `Total Debt` |

**Include in IBD**: Bank loans, bonds payable, commercial paper, convertible debt, finance leases
**Exclude from IBD**: Accounts payable, accrued expenses, deferred revenue, operating leases

---

## T2 NAV: Adjusted Current Assets

### Formula
```
T2_NAV_Total = Cash×1.00 + AR×0.85 + Inventory×Sector_Discount
             + Other_Current_Assets×0.50 − Total_Liabilities
T2_NAV_Per_Share = T2_NAV_Total / Shares_Outstanding
Entry Price < T2_NAV_Per_Share × 0.70
```

### Haircut Coefficients

| Asset | Coefficient | Rationale |
|-------|-----------|-----------|
| Cash & Equivalents | 1.00 | Face value, most liquid |
| Accounts Receivable | 0.85 | 15% haircut for bad debt, collection risk |
| Inventory — Consumer/Retail | 0.80 | Branded goods retain value |
| Inventory — Manufacturing/Industrial | 0.70 | WIP and raw materials less liquid |
| Inventory — Electronics/Technology | 0.50 | Rapid obsolescence |
| Inventory — Pharmaceutical | 0.40 | Regulatory, expiry risk |
| Inventory — Default | 0.65 | Conservative mid-point |
| Other Current Assets | 0.50 | Prepaid, deposits — partially recoverable |

### Accounts Receivable Adjustments

Apply additional haircuts when:
- **AR > 90 days**: Apply 0.70 coefficient instead of 0.85
- **Related-party AR > 20%**: Apply 0.50 coefficient to related-party portion
- **Concentration**: If single customer > 30% of AR, apply 0.75

### Inventory Adjustments

Apply additional haircuts when:
- **DIO rising 3+ consecutive years**: Apply sector discount × 0.80
- **DIO > 50% above peer median**: Apply sector discount × 0.70
- **Write-downs in last 2 years**: Apply sector discount × 0.85

---

## Special Treatments

### Deferred Revenue
- **Do NOT subtract** from liabilities. Deferred revenue represents an obligation to deliver services/goods, not a cash liability. Including it in Total Liabilities is conservative and correct for NAV purposes.

### Restricted Cash (Fact Check Item #1)
- **VETO** if restricted cash > 20% of total cash position
- Restricted cash must be subtracted from the Cash & Equivalents figure
- Common sources: regulatory reserves (banks, insurance), escrow deposits, collateral requirements

### Pledged Assets (Fact Check Item #2)
- **VETO** if core operating assets are pledged
- Pledged assets cannot be liquidated freely — they secure debt obligations
- Subtract pledged asset value from T2 numerator

### Operating Leases (ASC 842)
- Under ASC 842, operating lease liabilities appear on the balance sheet
- For T0/T1: Operating lease liabilities are already in Total Liabilities (conservative)
- For T2: Do NOT double-count. If using Total Liabilities that includes operating lease liabilities, no adjustment needed

### Lease Right-of-Use Assets
- **Do NOT include** ROU assets in T2 numerator (they are non-liquid)

---

## Entry Price Thresholds

| Tier | NAV/Share | Discount Required | Entry Price |
|------|-----------|-------------------|-------------|
| T0 | T0_NAV | 15% | < T0_NAV × 0.85 |
| T1 | T1_NAV | 20% | < T1_NAV × 0.80 |
| T2 | T2_NAV | 30% | < T2_NAV × 0.70 |

Higher tiers require smaller discounts because the underlying assets are more liquid and certain.

---

## P/B Zones

P/B ratio provides a quick sanity check alongside NAV tiers:

| Zone | P/B Range | Interpretation |
|------|-----------|---------------|
| Deep Value | ≤ 0.50 | Trading at half of book value; strong cigar-butt candidate |
| Value | 0.51 – 0.70 | Below book; moderate discount |
| Neutral | 0.71 – 1.00 | Near book; may not qualify |
| Premium | > 1.00 | Above book; not a cigar-butt candidate |

---

## Pillar 1 Output Format

```markdown
### Pillar 1: Net Asset Cushion

**T0 NAV**: $XX.XX per share (Total: $X,XXX.XM)
  Formula: (Cash $X,XXX.X − Total Liabilities $X,XXX.X) / Shares X,XXX.X
  Entry threshold: < $XX.XX (85% of T0 NAV)
  Current price $XX.XX → [QUALIFIES / DOES NOT QUALIFY]

**T1 NAV**: $XX.XX per share (Total: $X,XXX.XM)
  Formula: (Cash $X,XXX.X − IBD $X,XXX.X) / Shares X,XXX.X
  Entry threshold: < $XX.XX (80% of T1 NAV)
  Current price $XX.XX → [QUALIFIES / DOES NOT QUALIFY]

**T2 NAV**: $XX.XX per share (Total: $X,XXX.XM)
  Formula: (Cash×1.0 + AR×0.85 + Inv×0.XX + OtherCA×0.50 − TotalLiab) / Shares
  Entry threshold: < $XX.XX (70% of T2 NAV)
  Current price $XX.XX → [QUALIFIES / DOES NOT QUALIFY]

**NAV Tier Classification**: [T0 / T1 / T2 / NONE]
**P/B Ratio**: X.XX ([Deep Value / Value / Neutral])
**NAV Discount**: XX.X%

Special adjustments applied:
- [List any restricted cash, pledged assets, lease adjustments]
```

---

*Reference file for Cigar Butt Deep Value Strategy — Pillar 1*
