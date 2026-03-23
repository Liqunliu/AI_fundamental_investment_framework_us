# Factor 4: Valuation & Safety Margin — Detailed Steps

> Reference file for Phase 3 executor. Load when executing Factor 4. All amounts in millions USD.

## Purpose

Determine if the current stock price offers adequate safety margin based on multiple
valuation approaches. Combine relative and absolute valuation with a composite floor price.

**Instruction**: Read data_pack.md §1, §2, §4, §5, §10, §11, §15 and gg_result.md. Execute step by step.

---

## Steps 1-4: Relative Valuation

### Step 1: PE Historical Percentile

```
From §10 (historical prices) and §11 (financial ratios):
  Current PE (TTM) = [value]
  5-year PE range: [min] – [max]
  Current PE percentile = [value]% (where 0% = cheapest, 100% = most expensive)

  PE < 10th percentile → "Extreme discount"
  PE 10-25th percentile → "Attractive"
  PE 25-50th percentile → "Fair value"
  PE 50-75th percentile → "Full valuation"
  PE > 75th percentile → "Expensive"
```

### Step 2: PB Historical Percentile

```
From §1 and §11:
  Current PB = [value]
  5-year PB range: [min] – [max]
  Current PB percentile = [value]%
```

### Step 3: Sector Comparison

```
Compare current PE/PB with sector median:
  Sector median PE = [value] (from §1 or industry data)
  Premium/discount to sector = [value]%

  Trading at [premium/discount] to sector → [justified/unjustified] because [reason]
```

### Step 4: Relative Valuation Summary

```
PE percentile: [value]% — [assessment]
PB percentile: [value]% — [assessment]
Sector comparison: [premium/discount]%
Relative Valuation: [CHEAP / FAIR / EXPENSIVE]
```

---

## Step 5-1: Absolute Valuation Indicators (11 items)

Calculate all available indicators:

| # | Indicator | Formula | Value | Assessment |
|---|-----------|---------|-------|------------|
| 1 | EV/EBITDA | (Market Cap + Net Debt) / EBITDA | [value] | < 10 good, < 8 attractive |
| 2 | Cash-adjusted PE | (Market Cap − Net Cash) / Net Income | [value] | Lower = better |
| 3 | FCF Yield | FCF / Market Cap × 100 | [value]% | > 5% good, > 8% attractive |
| 4 | Earnings Yield | Net Income / Market Cap × 100 | [value]% | Compare vs Rf |
| 5 | Buyback Yield | Annual Buybacks / Market Cap × 100 | [value]% | > 3% = significant |
| 6 | Shareholder Yield | (Div + Buyback) / Market Cap × 100 | [value]% | > 5% attractive |
| 7 | EV/Revenue | Enterprise Value / Revenue | [value] | Industry-dependent |
| 8 | EV/FCF | Enterprise Value / FCF | [value] | < 15 good |
| 9 | Goodwill/Equity | Goodwill / Total Equity × 100 | [value]% | > 50% = risk |
| 10 | Net Debt/EBITDA | Net Debt / EBITDA | [value] | < 2 good, > 4 concern |
| 11 | Capex/OCF | Capital Expenditure / OCF × 100 | [value]% | < 30% = capital-light |

---

## Step 5-2: Floor Price (5-Method Composite)

Calculate floor price using 5 methods, then take arithmetic average:

### Method 1: Net Liquid Assets per Share

```
Net Liquid Assets = Cash + Short-term Investments + Trading Assets − Total Interest-bearing Debt
                  = [value] $M
Shares Outstanding = [value]M
Net Liquid Assets / Share = $[value]
```

### Method 2: Book Value per Share (BVPS)

```
Total Shareholders' Equity (excl. minority) = [value] $M
Shares Outstanding = [value]M
BVPS = $[value]
```

### Method 3: 10-Year Historical Low Price

```
From §10 (weekly close prices, 10 years):
  10-year minimum close = $[value]
  Date of low = [YYYY-MM-DD]
```

### Method 4: Dividend Discount Price

```
Average annual dividend per share (3-year) = $[value]
Discount rate = max(Rf, 3%) = [value]%
Dividend Discount Price = Avg DPS / Discount Rate = $[value]

Note: If company pays no dividends, this method is N/A.
Use buyback yield as alternative:
  Buyback-implied price = Annual Buyback per Share / Discount Rate = $[value]
```

### Method 5: Pessimistic FCF Capitalization Price

```
Past 5 years FCF: [FCF1, FCF2, FCF3, FCF4, FCF5] $M
Minimum FCF = [value] $M

Condition: Valid only if ALL 5 years FCF > 0
If valid:
  Pessimistic FCF Cap Price = Min_FCF / Rf / Shares = $[value]
If invalid (any year FCF ≤ 0):
  Method 5 = N/A
```

### Composite Floor Price

```
Valid methods: [list which methods produced valid results]
Floor Price = Arithmetic average of valid method values = $[value]

Current Price: $[value]
Premium over Floor: (Current / Floor − 1) × 100 = [value]%
```

### Premium Assessment

| Premium Range | Interpretation |
|--------------|----------------|
| ≤ 0% | "Buying is winning" — price below floor |
| 0 – 30% | Adequate safety margin |
| 30 – 80% | Reasonable premium, needs growth validation |
| > 80% | High premium, requires strong growth thesis |

---

## Final Rating

```
Combine all valuation inputs:

1. GG vs Threshold II:
   GG = [value]%, Threshold II = [value]%
   Safety margin = GG − Threshold II = [value] pct

2. Relative valuation: [CHEAP / FAIR / EXPENSIVE]

3. Floor price premium: [value]%

4. Absolute indicators: [summary of key metrics]

Rating matrix:
  BUY:   GG > Threshold II AND (PE < 25th percentile OR Premium < 30%)
  WATCH: GG > Threshold II AND (PE 25-50th OR Premium 30-80%)
  AVOID: GG < Threshold II OR Premium > 80% without strong growth

Rating: [BUY / WATCH / AVOID]

Recommended position size:
  BUY + thick margin (> 3 pct): 100% standard position
  BUY + moderate margin (1-3 pct): 70% standard position
  BUY + thin margin (0-1 pct): 50% standard position
  WATCH: 30% observation position
  AVOID: 0%
```

---

## Factor 4 Output

```
Relative Valuation:
  PE percentile: [value]% — [assessment]
  PB percentile: [value]% — [assessment]
  Sector premium/discount: [value]%

Absolute Valuation:
  EV/EBITDA: [value]
  Cash-adj PE: [value]
  FCF Yield: [value]%
  Shareholder Yield: [value]%

Floor Price: $[value] (methods used: [list])
Current Price: $[value]
Premium: [value]%

GG: [value]%
Threshold II: [value]%
Safety Margin: [value] pct

Rating: [BUY / WATCH / AVOID]
Position Size: [value]% of standard
Factor 4 Conclusion: [PASS / VETO (reason)]
```

---

*US Equity Turtle Strategy v1.0 | Factor 4 Reference File*
