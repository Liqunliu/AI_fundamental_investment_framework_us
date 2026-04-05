# Factor C2: Cycle Phase Detection

> Determines where the stock sits in its business cycle using a composite
> scoring model. The phase classification drives position sizing and
> entry/exit decisions.

---

## 5-Phase Model

| Phase | Score Range | Name | Action |
|-------|------------|------|--------|
| 1 | >= 0.80 | Deep Trough | BUY (max position) |
| 2 | 0.65-0.80 | Early Recovery | BUY (standard) |
| 3 | 0.40-0.65 | Mid-Cycle | HOLD only |
| 4 | 0.20-0.40 | Late Cycle | REDUCE |
| 5 | < 0.20 | Peak | SELL/AVOID |

**Key insight**: Higher score = more trough-like = better buying opportunity.

---

## Composite Score Formula

```
Composite = 40% × Company + 35% × Sector + 15% × Macro + 10% × Price
```

Each component produces a score from 0.0 (peak) to 1.0 (deep trough).

---

## Component 1: Company Fundamentals (40%)

Score the company's current financial position relative to its own history.

### Revenue Position (45% of company score)

```
Revenue_Percentile = (Current_Revenue - Min_5yr) / (Max_5yr - Min_5yr)
Revenue_Score = 1.0 - Revenue_Percentile
```

Low revenue relative to 5-year range = trough signal.

### EBITDA Margin Position (35% of company score)

```
Current_Margin = Current_EBITDA / Current_Revenue
Margin_Percentile = (Current_Margin - Min_5yr_Margin) / (Max_5yr_Margin - Min_5yr_Margin)
Margin_Score = 1.0 - Margin_Percentile
```

Compressed margins = trough signal.

### Capex Trend (20% of company score)

| Capex YoY Change | Score | Interpretation |
|-------------------|-------|---------------|
| < -15% | 0.85 | Deep cuts — trough behavior |
| -15% to -5% | 0.70 | Cutting — approaching trough |
| -5% to +5% | 0.50 | Stable — mid-cycle |
| +5% to +15% | 0.30 | Growing — expansion |
| > +15% | 0.15 | Rapid growth — peak behavior |

Companies cut capex at troughs and increase it at peaks.

### Company Score Calculation

```
Company_Score = 0.45 × Revenue_Score + 0.35 × Margin_Score + 0.20 × Capex_Score
```

---

## Component 2: Sector Indicators (35%)

Use commodity prices and sector indices as cycle indicators.

### Sector Mapping

| Sector | Primary Indicator | Symbol |
|--------|-------------------|--------|
| Energy (Oil & Gas) | WTI Crude Oil | CL=F |
| Semiconductors | PHLX Semiconductor Index | ^SOX |
| Shipping | Baltic Dry Index (BDRY proxy) | BDRY |
| Mining / Metals | Copper Futures | HG=F |
| Steel | VanEck Steel ETF | SLX |

### Indicator Percentile Score (65% of sector score)

```
Indicator_Percentile = (Current - 5yr_Low) / (5yr_High - 5yr_Low)
Sector_Percentile_Score = 1.0 - Indicator_Percentile
```

Low commodity price = trough = high score.

### Trend Score (35% of sector score)

| 12M Change | Score | Interpretation |
|------------|-------|---------------|
| < -30% | 0.90 | Crash — deep trough |
| -30% to -15% | 0.75 | Declining — trough forming |
| -15% to 0% | 0.55 | Weak — possible trough |
| 0% to +15% | 0.35 | Recovering — early cycle |
| > +15% | 0.15 | Strong — mid/late cycle |

### Sector Score Calculation

```
Sector_Score = 0.65 × Percentile_Score + 0.35 × Trend_Score
```

---

## Component 3: Macro Overlay (15%)

Broad economic indicators that affect all cyclical stocks.

### Yield Curve (40% of macro score)

| 10Y-2Y Spread | Score | Interpretation |
|----------------|-------|---------------|
| < -0.50% | 0.85 | Deeply inverted — recession imminent |
| -0.50% to 0% | 0.70 | Inverted — late cycle stress |
| 0% to +0.50% | 0.50 | Flat — uncertain |
| +0.50% to +1.50% | 0.35 | Normal — expansion |
| > +1.50% | 0.20 | Steep — early expansion |

### Credit Spreads (30% of macro score)

Use HYG (high-yield) price as proxy. Low HYG price = wide spreads = stress.

```
Credit_Score = 1.0 - (HYG_5yr_Percentile / 100)
```

### Interest Rate Environment (30% of macro score)

| 10Y Yield Percentile | Score | Interpretation |
|----------------------|-------|---------------|
| > 80% | 0.70 | High rates — restrictive, trough-inducing |
| 60-80% | 0.55 | Elevated — late cycle |
| 40-60% | 0.40 | Normal |
| < 40% | 0.30 | Low rates — expansion |

### Macro Score Calculation

```
Macro_Score = average of available sub-scores
```

---

## Component 4: Price Position (10%)

Simple price-based contrarian signal.

```
Price_Percentile = (Current_Price - 5yr_Low) / (5yr_High - 5yr_Low)
Price_Score = 1.0 - Price_Percentile
```

Stock near 5-year low = trough = high score.

---

## Scoring Output Format

```
C2 Cycle Phase Detection

Composite Score: X.XXXX
Phase: X — [Phase Name]
Action: [Action]

Score Breakdown:
| Component | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Company   | 40%    | X.XXXX | X.XXXX  |
| Sector    | 35%    | X.XXXX | X.XXXX  |
| Macro     | 15%    | X.XXXX | X.XXXX  |
| Price     | 10%    | X.XXXX | X.XXXX  |
| Composite | 100%   | —     | X.XXXX  |

Company Details:
  Revenue percentile: XX.X% (5yr range)
  EBITDA margin percentile: XX.X%
  Capex YoY change: ±XX.X%

Sector Details:
  Primary indicator: [Name] at XX.X% of 5yr range
  12M change: ±XX.X%

Macro Details:
  Yield curve spread: X.XX%
  Credit conditions: [Tight / Normal / Loose]

Price Details:
  Stock at XX.X% of 5yr range
```

---

## Cross-Validation Rules

1. **Divergence check**: If Company says trough but Sector says peak, flag
   as "company-specific distress" (may not be cyclical — could be structural).

2. **Sector confirmation**: Ideally Company + Sector agree within 1 phase.
   If they diverge by 2+ phases, reduce confidence and note in report.

3. **Macro override**: If Macro says deep recession (score > 0.80) and
   Company shows moderate trough, upgrade the assessment by 0.5 phase.

---

*Cyclical Trough Strategy v1.0 | Factor C2 — Cycle Phase Detection*
