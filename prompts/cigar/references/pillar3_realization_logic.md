# Pillar 3: Realization Logic — Reference Guide

> **Load this file** before executing Pillar 3 analysis.

---

## Overview

Pillar 3 answers: **How will the NAV discount close?** A stock trading below net asset value needs a catalyst or mechanism for value realization. Without one, the discount can persist indefinitely (a "value trap").

Three sub-types with distinct realization mechanisms:

| Sub-Type | Mechanism | Example Catalysts |
|----------|-----------|-------------------|
| **A** | High-Dividend Below-Book | Dividend yield returns capital while waiting |
| **B** | Holding Company Discount | SOTP gap narrows via activism, spin-off, buyback |
| **C1** | Event-Driven (Traditional) | Asset disposition, buyback program, liquidation |
| **C2** | Event-Driven (Regulatory) | Policy resolution removes overhang |

Stocks may qualify for **dual tags** (e.g., A+B: dividend-paying holding company).

---

## Sub-Type Classification Decision Tree

```
START: Stock qualifies for Pillar 1 (T0/T1/T2) + Pillar 2 (2/3 conditions)
  │
  ├─ Dividend Yield ≥ 5% AND P/B ≤ 0.50 AND ≥5 consecutive div years?
  │    └─ YES → Type A (High-Dividend Below-Book)
  │
  ├─ Company holds listed/unlisted subsidiaries with identifiable value?
  │    └─ YES → Is Holding Discount ≥ 30%?
  │         └─ YES → Type B (Holding Company Discount)
  │
  ├─ Is there an identifiable near-term event catalyst?
  │    ├─ Asset disposition / spin-off announced or likely? → Type C1a
  │    ├─ Active buyback program (execution > 30%)? → Type C1b
  │    └─ Liquidation / going-private / takeout offer? → Type C1c
  │
  ├─ Is the discount primarily due to regulatory/policy uncertainty?
  │    └─ YES → C2 score ≥ 6? → Type C2
  │
  └─ No realization mechanism identified → CAUTION (potential value trap)
```

---

## Type A: High-Dividend Below-Book

### Entry Criteria

| Criterion | Threshold | Source |
|-----------|-----------|--------|
| Dividend yield | ≥ 5% (US market) | Market data |
| P/B ratio | ≤ 0.50 | Market data / Balance sheet |
| Consecutive dividend years | ≥ 5 | Cash flow statement |
| Payout ratio | < 80% | Net income vs dividends paid |
| FCF dividend coverage | > 0.80 | FCF / Dividends |

### Dividend Sustainability Scorecard (0-10 points)

| Item | Points | Criterion |
|------|--------|-----------|
| Payout ratio safety | 0-2 | < 60%: 2 pts; 60-80%: 1 pt; > 80%: 0 pts |
| FCF coverage | 0-2 | > 1.2x: 2 pts; 0.8-1.2x: 1 pt; < 0.8x: 0 pts |
| Consecutive years | 0-1 | ≥ 5 years: 1 pt |
| Dividend growth | 0-1 | Growing dividends 3 yrs: 1 pt |
| Earnings stability | 0-1 | 3+ years positive NI: 1 pt |
| Debt manageable | 0-1 | D/E < 1.5: 1 pt |
| Industry norm | 0-1 | Yield in-line with sector: 1 pt |
| Cash reserves | 0-1 | Cash > 1yr dividends: 1 pt |

**Rating**: 8-10: Highly sustainable, 6-7: Sustainable, 4-5: At risk, 0-3: Unsustainable

### Dividend Recovery Period

```
Recovery_Period = Entry_Price / (Annual_Dividend_Per_Share × (1 − Tax_Rate))
```

US qualified dividend tax = 15%. A recovery period < 10 years is preferred.

### Type A Entry Rules (Scaled Building)

| Tranche | Weight | Trigger |
|---------|--------|---------|
| 1st | 40% | Price hits buy threshold |
| 2nd | 30% | Price drops another 10% |
| 3rd | 30% | Another 10% drop OR catalyst confirmation |

### Type A Exit Rules

| Trigger | Action |
|---------|--------|
| P/B recovers to 0.65-0.70 | Sell 50% |
| P/B recovers to 0.80-0.85 | Sell remaining |
| Dividend cut > 30% | Immediate full exit |
| Payout > 100% for 2 consecutive quarters | Reassess; likely exit |

---

## Type B: Holding Company / Conglomerate Discount

### SOTP (Sum-of-the-Parts) Valuation

```
SOTP_Value = Σ(Subsidiary_Market_Cap × Ownership_%) + Parent_Net_Cash
Holding_Discount = (SOTP_Value − Parent_Market_Cap) / SOTP_Value × 100%
```

### Entry Criteria

| Criterion | Threshold |
|-----------|-----------|
| Holding discount | ≥ 30% |
| Ownership in key subsidiary | ≥ 10% |
| Parent net cash | > 0 (not net debt) |

### SOTP Sensitivity Analysis

Run three scenarios:

| Scenario | Subsidiary Valuation | Net Cash | Resulting Discount |
|----------|---------------------|----------|-------------------|
| **Bull** | +20% above current | Full | X% |
| **Base** | Current market prices | Full | X% |
| **Bear** | −20% below current | 80% | X% |

If discount > 30% even in bear case → Strong Type B candidate.

### Discount Decomposition

Analyze the sources of the holding discount:

| Factor | Weight | Assessment |
|--------|--------|-----------|
| Liquidity discount | 20% | Parent share trading volume vs subsidiaries |
| Governance discount | 30% | Related-party transactions, dual-class shares |
| Complexity discount | 25% | Number of subsidiaries, transparency |
| Information asymmetry | 25% | Disclosure quality, analyst coverage |

### Type B Entry Rules

| Tranche | Weight | Trigger |
|---------|--------|---------|
| 1st | 40% | Discount ≥ 30% |
| 2nd | 30% | Discount widens to ≥ 40% |
| 3rd | 30% | Discount widens to ≥ 50% OR catalyst emerges |

### Type B Exit Rules

| Trigger | Action |
|---------|--------|
| Discount narrows to 20% | Sell 50% |
| Discount narrows to 15% | Sell remaining |
| Subsidiary deterioration > 30% | Reassess thesis |
| Expected holding period | 12-24 months |

---

## Type C1: Event-Driven (Traditional)

### C1a: Asset Disposition / Spin-Off

| Criterion | Threshold |
|-----------|-----------|
| Post-disposition NAV > current mktcap × 1.5 | 50% minimum upside |
| Event probability | ≥ B grade (50%+) |
| Entry price | < estimated post-disposition NAV × 0.70 |
| Position size | 5-8% |

### C1b: Share Buybacks

| Criterion | Threshold |
|-----------|-----------|
| Net cash > mktcap × 10% | Company has firepower |
| P/B | < 0.60 |
| Actual execution > 30% of authorization | Not just announced, but executing |
| Entry price | < BVPS × 0.55 |
| Position size | 5% |

### C1c: Liquidation / De-listing / Going-Private

| Criterion | Threshold |
|-----------|-----------|
| Liquidation value (20% haircut) > mktcap | Net positive after haircut |
| Offer price > current price × 1.05 | 5% arbitrage spread minimum |
| Position size | 5-8% |

### Event Timeline & Probability Matrix

| Phase | Description | Risk Level |
|-------|-------------|-----------|
| T0 | Event signal emerges (rumors, filings) | High uncertainty |
| T1 | Formal announcement (8-K, press release) | Moderate |
| T2 | Shareholder vote / regulatory approval | Lower |
| T3 | Event completion / settlement | Execution risk only |

| Probability Grade | Likelihood | Position Modifier |
|-------------------|-----------|-------------------|
| A | > 80% | Full position |
| B | 50-80% | 75% of max position |
| C | 30-50% | 50% of max position |
| D | < 30% | Watchlist only |

---

## Type C2: Regulatory / Policy Resolution

### Admission Criteria

All four must be true:
1. **Regulatory direction confirmed**: Clear signals from regulators / legislature
2. **Precedent exists**: Similar situations have resolved favorably before
3. **Business fundamentally healthy**: Operations would be profitable absent regulatory overhang
4. **Valuation reflects pessimism**: Trading at extreme discount vs intrinsic value

### C2 Scoring System (max 10 points)

| Factor | Weight | Max Points | Criteria |
|--------|--------|-----------|----------|
| Regulatory certainty | 30% | 3 | 3: Formal guidance; 2: Strong signals; 1: Speculation |
| Precedent comparability | 20% | 3 | 3: Identical situation resolved; 2: Similar; 1: Loosely analogous |
| Company's own progress | 20% | 2 | 2: Compliance achieved; 1: In progress |
| Valuation safety margin | 30% | 2 | 2: P/E < 5x or P/B < 0.3; 1: P/E < 10x or P/B < 0.5 |

### C2 Rating

| Rating | Score | Position Size |
|--------|-------|--------------|
| C2+ | ≥ 8 | 5-8% |
| C2 | 6-7 | 5% |
| C2− | 4-5 | 2-5% |
| Below | < 4 | Do not enter |

**Additional requirement**: Fact Check base rating ≥ B

---

## Dual-Tag Mechanism

Stocks may qualify for multiple sub-types:

| Combination | Example | Handling |
|-------------|---------|---------|
| A + B | Dividend-paying holding company | Use stricter entry from both; higher position cap |
| C + B | Holding company with spin-off catalyst | Layer event-driven analysis on SOTP |
| A + C1b | High-yield stock doing buybacks | Buyback enhances dividend sustainability |

When dual-tagged, apply the **more conservative** entry rule and the **higher** of the two position size limits.

---

## Pillar 3 Output Format

```markdown
### Pillar 3: Realization Logic

**Sub-Type Classification**: [A / B / C1a / C1b / C1c / C2 / Dual: X+Y / NONE]

[Type-specific analysis based on sub-type:]

#### Type A Assessment (if applicable)
- Dividend Yield: X.X% [≥5%: PASS / <5%: FAIL]
- Consecutive Div Years: X [≥5: PASS / <5: FAIL]
- Sustainability Score: X/10
  [Itemized scorecard]
- Dividend Recovery Period: X.X years
- Recommendation: [Strong / Moderate / Weak / Not recommended]

#### Type B Assessment (if applicable)
- SOTP Valuation: $X,XXXM
- Parent Market Cap: $X,XXXM
- Holding Discount: XX.X%
- Sensitivity: Bull XX%, Base XX%, Bear XX%
- Discount Sources: [Liquidity / Governance / Complexity / Info Asymmetry]

#### Type C Assessment (if applicable)
- Event: [Description]
- Phase: [T0 / T1 / T2 / T3]
- Probability: [A / B / C / D]
- Expected Upside: XX%
- C2 Score (if applicable): X/10

**Realization Thesis**: [1-2 sentence summary of how value will be unlocked]
**Expected Timeframe**: [X-Y months/years]
**Position Sizing**: [X%] based on [tier + sub-type]
```

---

*Reference file for Cigar Butt Deep Value Strategy — Pillar 3*
