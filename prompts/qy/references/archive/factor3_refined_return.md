# Factor 3: Refined Penetration Return Rate (Bottom-Up) + Cash Quality Audit — Detailed Steps

> Reference file for Phase 3 executor. Load when executing Factor 3. All amounts in millions USD.

## Purpose & Instruction

> **Purpose**: Bottom-up cash flow analysis to calculate the refined GG (penetration return rate),
> with concurrent cash reserve quality audit. The final valuation is anchored on this factor's GG%.

**Instruction**: Trace cash flows line by line. Only execute for stocks that passed Factor 1 and Factor 2.
Apply extreme conservative assumptions throughout.

---

## Step 1: Real Cash Revenue Reconstruction

Calculate year by year:

```
Revenue = [value] $M (S)
Accounts Receivable net change = [value] $M (T) (increase = positive, decrease = negative)
Deferred Revenue / Contract Liability net change = [value] $M (U)
  (increase = positive, decrease = negative) ← data_pack §4 Balance Sheet

Conservative processing rules:
  AR net increase → Deduct (revenue earned but cash not collected)
  AR net decrease → Add back (collected previously owed cash)
  Deferred Revenue / Contract Liability net increase → Do NOT add back
    (represents undelivered obligations to customers)
  Deferred Revenue / Contract Liability net decrease → Deduct
    (consumed previously collected cash)
  Exception: High-certainty prepaid models (e.g., SaaS with >95% renewal rate)
    may add back net increase — must annotate rationale

Real Cash Revenue = S − T_net_increase − U_net_decrease
Collection Ratio = Real Cash Revenue / S

Assessment: Is collection ratio consistently near 1?
  If consistently < 1 → Explain cause, proceed to Step 2 AR footnote audit
```

Year-by-year table:

| Year | Revenue | AR Net Change | Deferred Rev Net Change | Real Cash Revenue | Collection Ratio |
|------|---------|--------------|------------------------|-------------------|-----------------|
| 20XX | | | | | |

---

## Step 2: AR Footnote Audit (MANDATORY when Collection Ratio < 1)

```
Aging analysis:
  AR > 1 year as % of total: [X]%, trend: [rising / stable / declining]

Bad debt provision vs peers:
  Allowance rate: [X]% vs industry average [X]%
  Assessment: [Lenient / In-line / Conservative]

Customer concentration:
  Top 5 customers as % of AR: [X]%
  Top 1 customer as % of AR: [X]%

Related-party AR:
  Related-party AR as % of total AR: [X]%

US GAAP revenue recognition aggressiveness (ASC 606):
  Assessment: [Normal / Aggressive recognition risk exists]
  Indicators: Bill-and-hold arrangements, multiple performance obligations, variable consideration
```

---

## Step 3: Non-Recurring Cash Flow Classification

```
Classification principle: Categorize by "whether constitutes distributable cash"

═══ Retained Items (Real distributable cash — NOT deducted) ═══

(A) Asset Disposal Proceeds = [V1]
    Source: §5 Cash Flow Statement "proceeds from disposal of fixed assets" line item
    List significant disposals:
    Item 1: [name], amount [X]
    Item 2: [name], amount [X]
    Processing rule: Do NOT deduct. Asset disposal proceeds are real cash in hand;
    management can use for dividends, buybacks, or reinvestment — constitutes distributable source.
    Annotation: Note impact on future earning capacity
      → Post-disposal revenue/profit expected to decrease by [X] $M/year
      → Is this a non-core asset (divestiture doesn't affect core earnings)? [YES/NO]

(B) Other Investment Income = [V5]
    Source: §5 Cash Flow Statement "investment income received" line item
    Includes but not limited to:
    - Dividends received from associates/JVs = [V5a]
    - Financial asset interest income (deposits, bonds) = [V5b]
    - Money market / fund redemption gains = [V5c]
    - Other investment-related cash inflows = [V5d]
    Processing rule: Do NOT deduct. Investment income is real cash received — distributable source.
    Note: Only count cash actually received per cash flow statement,
    NOT equity-method investment gains recognized in income statement but not received in cash.

═══ Deducted Items (Non-distributable — remove) ═══

(C) Items to deduct:
    Government subsidies / grants = [V2]
    Insurance proceeds = [V3]
    Other one-time non-investment inflows = [V4]
    Total deductions = [V_deduct] = V2 + V3 + V4

═══ Summary ═══

Retained items total = V1 + V5 (counted as distributable cash)
  As % of current year OCF = [X]%
  If retained items > 50% of current year OCF:
    Flag as "non-operating income dominated year";
    Step 7 AA calculation must distinguish averages with/without this year
```

---

## Step 4: Operating Cash Outflows Reconstruction

Calculate year by year:

```
Supplier payments = COGS + Inventory increase (or − decrease) − AP increase (or + decrease) = [value] $M (W1)
  Is AP being consistently stretched: [YES/NO]

Employee payments = Cash paid to employees from cash flow statement = [value] $M (W2)
  US-specific: SBC component
  Cash employee costs = W2 − SBC = [value] $M (W2_cash)
  SBC is non-cash → separate from W2 for cash flow analysis
  Deferred compensation / equity-based non-cash component = [value] $M (W2a)

Cash taxes = Income tax expense − Deferred tax change = [value] $M (W3)
  Deferred tax asset persistently increasing: [YES/NO]

Cash interest = Interest expense actually paid in cash = [value] $M (W4)
  Capitalized interest = [value] $M (W4a), as % of total interest = [value]%
  If capitalized interest > 30% of total: Restore as current expense,
    adjusted cash interest = W4 + W4a

Total operating cash outflows = W1 + W2_cash + W3 + W4 (or adjusted) = [value] $M (W)
```

---

## Step 5: Capital Expenditure & Investment — Extreme Conservative Treatment

```
Core principle: Include ALL in deductions; do not distinguish maintenance/growth or required/optional

(a) Total capital expenditure = [value] $M (E, carried from Factor 2) (fully deducted)
(b) Investment purchases = [value] $M (X1) (external investments + acquisitions + equity stakes, fully deducted)
    List significant items:
    Item 1: [name], amount [X]
    Item 2: [name], amount [X]
(c) Hidden mandatory expenditure reconstruction = [value] $M (X2)
    R&D capitalized (per ASC 985-20 internal-use software / ASC 350-40 cloud computing):
      Capitalized R&D = [value] $M
    Deferred asset amortization reversals: [value] $M
    Other capitalized costs requiring restoration: [value] $M

Total deductions = Capex + Investments + Hidden expenditures = [value] $M (Y = E + X1 + X2)

Supplementary annotation (does NOT affect calculation):
  Suspected growth capex = [value] $M (Z) (criterion: if stopped, earnings would not decline within 1-2 years)
  As % of total deductions = Z / Y = [value]%
```

---

## Step 6: US GAAP Audit

```
US GAAP (ASC) audit items:

Revenue recognition aggressiveness (ASC 606):
  Multiple performance obligations: [Normal / Aggressive allocation]
  Variable consideration: [Normal / Overly optimistic estimates]
  Bill-and-hold: [Not used / Used — flag]
  Assessment: [Normal / Aggressive]

Deferred tax asset trends:
  DTA balance trend: [Stable / Persistently increasing]
  Valuation allowance adequacy: [Adequate / Potentially insufficient]

Impairment provisions vs peers:
  Goodwill testing (ASC 350): [Adequate / Potential understatement]
  Long-lived asset impairment (ASC 360): [Adequate / Potential understatement]

Operating leases (ASC 842):
  Right-of-use asset balance: [value] $M
  Lease liability (current + non-current): [value] $M
  Off-balance-sheet lease commitments (short-term/low-value exemptions): [value] $M

Contingent liabilities & off-balance-sheet:
  Guarantees: [value] $M, to: [related / unrelated parties]
  Material litigation: [value] $M, probability of loss: [Remote / Reasonably possible / Probable]
  Capital commitments (unpaid): [value] $M
```

---

## Step 7: Real Disposable Cash Surplus & AA Calculation

Calculate year by year:

```
Real Disposable Cash Surplus = Real Cash Revenue
                             + Asset Disposal Proceeds (V1)
                             + Other Investment Income (V5)
                             − Non-recurring deductions (V_deduct)
                             − Operating Cash Outflows (W)
                             − Total Capital Deductions (Y = E + X1 + X2)
```

| Year | Real Cash Rev | + Disposal | + Inv Income | − Non-recur | − Op Outflows | − Cap Deductions | = Surplus | Growth Capex % | Non-op Income % |
|------|--------------|-----------|-------------|------------|--------------|-----------------|---------|---------------|----------------|
| 20XX | | | | | | | | | |

```
2-year average = [value] $M (AA_2y) (default baseline — reflects current operating capability)
All-years average = [value] $M (AA_all) (reference value)
Excl. non-operating-dominated years average = [value] $M (AA_excl) (reference value)

Default: Use AA_2y as extrapolation baseline. Rationale: Recent 2 years better reflect
current operating capability; avoids distortion from non-recurring events (pandemic, cycle trough).

Exception rules (switch to AA_all or AA_excl):
  (a) Recent 2 years include obvious non-recurring peak (e.g., one-time disposal > 30% of surplus) → Use AA_all
  (b) Less than 2 years of data available → Use AA_all
  (c) Analyst judgment identifies other distortion in recent 2 years → State rationale and select

Selected baseline = [value] $M (AA = AA_2y / AA_all / AA_excl), rationale: [explanation]

US-specific SBC adjustment:
  AA (excluding SBC) = AA − annual SBC expense = [value] $M (AA_exSBC)
  Rationale: SBC creates real dilution for shareholders. Even though non-cash,
  it transfers value from existing to new shareholders. Must subtract to get true owner economics.
```

---

## Step 8: Cash Reserve Quality Verification

```
Book cash (using Module 0 cash calibration) = [value] $M (BB) (source: data_pack §4)
  Narrow cash = [value] $M (BB_narrow) (§4 Cash & equivalents + Short-term investments)
  Deposits/money market = [value] $M (BB_deposit) (§4 broad − narrow difference)
Restricted cash (pledged / frozen / regulatory accounts) = [value] $M (CC)
Foreign-trapped cash (overseas subsidiaries with repatriation constraints) = [value] $M (DD)
  Note: Post-TCJA, US companies can generally repatriate overseas cash, but may face
  state taxes or withholding taxes in certain jurisdictions
Special-purpose funds (escrowed, dedicated) = [value] $M (EE)
Freely disposable cash (broad) = BB − CC − DD − EE = [value] $M (FF)
Freely disposable cash (narrow) = BB_narrow − CC − DD − EE = [value] $M (FF_narrow)
⚠️ Difference between definitions = FF − FF_narrow = [value] $M

═══ Cash Definition Selection Rule ═══

Default: Use narrow definition FF_narrow as freely disposable cash.
Upgrade to broad definition conditions (ALL must be met):
  (a) Deposits/money market instruments have remaining maturity ≤ 1 year
  (b) No pledge, freeze, or other usage restrictions
  (c) BB_deposit / BB_narrow < 50% (avoid over-reliance on non-cash-equivalent assets)
If all conditions met → Use broad definition FF
If not → Use narrow definition FF_narrow

Selected definition = [Broad FF / Narrow FF_narrow], rationale: [explanation]
```

---

## Step 9: Post-Dividend Cash Reserve Movement

Year by year:

```
Ending freely disposable cash − Beginning freely disposable cash − Current year surplus + Current year dividends & buybacks
Is this consistently positive? [YES → Cash generation > distribution, healthy / NO → Explain]
```

---

## Step 10: Distribution Willingness + Refined Penetration Return Rate

### Step 10a: Distribution Willingness Assessment

```
Dividend commitment: [Explicit dollar commitment / Minimum payout ratio commitment /
                     No commitment but historically stable / No commitment and volatile]
Commitment source: [Annual report / Earnings call / Investor day / None]

Past 3-5 years payout ratio series: [X1%, X2%, X3%, X4%, X5%]
  (Source: data_pack §5 dividends paid / §3 net income, same currency)
Payout ratio average = [value]% (M), standard deviation = [value]% (N)

Cancellation-type buyback average (3-year) = [value] $M (O) (source: data_pack §14)
Net dilution effect (buyback share reduction − new issuance increase): [Positive / Negative / Neutral]

Distribution willingness assessment: [Strong / Moderate / Weak]

US-specific: Many US tech companies return cash primarily through buybacks, not dividends.
  Include both dividends and buybacks in distribution willingness assessment.
```

### Step 10b: Refined Penetration Return Rate Calculation (Final Valuation Input)

```
Selected baseline AA = [Step 7 determined value] $M
Payout ratio anchor = Committed ratio (if committed); otherwise 3-year average
  (same calibration as Factor 2, source: data_pack §5 + §3)

Refined Penetration Return Rate:
  GG = [AA × M_anchor × (1 − Q) + O] / Market_Cap × 100
  = [value]% (GG)

SBC-adjusted variant:
  GG_exSBC = [AA_exSBC × M_anchor × (1 − Q) + O] / Market_Cap × 100
  = [value]% (GG_exSBC)

Primary GG = GG_exSBC for US stocks with significant SBC (SBC > 10% of Net Income)
```

### Step 10c: Factor 2 Cross-Check

```
vs Factor 2 coarse value R = [value]%:
  Coarse deviation = R − GG = [value] pct (HH)
  If |HH| > 2 pct: Flag deviation source (coarse overestimate/underestimate cause)
```

---

## Step 11: Revenue Sensitivity Analysis

```
Assume next fiscal year revenue changes relative to current FY,
while other cost structure (operating expense ratio, capex, tax rate, payout ratio) holds constant.

Current FY Revenue = [S_current] $M
Current FY Real Disposable Cash Surplus = [AA_current] $M (latest single-year value)
Operating leverage estimate λ = median of (ΔSurplus / ΔRevenue) over past 3 years = [λ]
  (λ meaning: for each $1M change in revenue, surplus changes by λ $M)

λ reliability checks:
  If past 3 years max revenue swing (max/min − 1) < 10%
    → ⚠️ λ extrapolation unreliable: insufficient historical revenue variation; sensitivity results for reference only
  If ΔSurplus/ΔRevenue sign inconsistent across 3 years
    → ⚠️ λ unstable: cost structure may have changed
  If λ > 3 or λ < 0
    → ⚠️ λ anomalous, recommend manual cost structure review
  λ reliability = [Normal / One warning / Multiple warnings or anomalous]

CV-based λ (US complement):
  Calculate GG for each of past 5 years
  CV = StdDev(GG_series) / Mean(GG_series)
  If CV < 0.3 → High predictability
  If 0.3 ≤ CV < 0.6 → Moderate predictability
  If CV ≥ 0.6 → Low predictability

Revenue scenario surplus and return rate projections:

| Revenue Scenario | Revenue | Projected Surplus | Refined Return Rate | vs Threshold |
|-----------------|---------|-------------------|--------------------:|:------------|
| 1.0× (base) | [S] $M | [AA] $M | [GG]% | [±X pct] |
| 0.9× (mild decline) | [S×0.9] $M | [AA'] $M | [GG']% | [±X pct] |
| 0.8× (moderate decline) | [S×0.8] $M | [AA''] $M | [GG'']% | [±X pct] |
| 0.7× (severe decline) | [S×0.7] $M | [AA'''] $M | [GG''']% | [±X pct] |

Projected surplus calculation:
  AA_scenario = AA_current + (S_scenario − S_current) × λ
  Return_scenario = [AA_scenario × M_anchor × (1 − Q) + O] / Market_Cap

Critical revenue multiplier:
  Set return rate = Threshold II%, solve for revenue:
  Critical surplus = (II% × Market_Cap − O) / (M_anchor × (1 − Q))
  Critical revenue = S_current + (Critical surplus − AA_current) / λ
  Critical multiplier = Critical revenue / S_current = [X]×

  Assessment:
    Critical multiplier ≥ 0.85 → ⚠️ Safety margin sensitive to revenue fluctuation
    Critical multiplier 0.7-0.85 → Safety margin moderately resilient
    Critical multiplier < 0.7  → Safety margin strongly resilient
```

---

## Step 12: Cross-Validation with Factor 1 + Predictability + Extrapolation Credibility

### Cross-Validation with Factor 1

```
Factor 3 cash flow series trend: [Stable / Mild uptrend / Volatile / Trending decline]
Factor 1 business model assessment: [Favorable / Neutral / Negative]

Cross-validation result:
  Both consistent → Supports high extrapolation credibility
  Factor 3 better than Factor 1 expected → Possible hidden moat; recommend re-examining Factor 1
  Factor 3 weaker than Factor 1 expected → Most dangerous divergence;
    must find explanation, otherwise apply large discount or veto
```

### Predictability Rating

```
Conservative-assumption net income range:
  Revenue = current level (no growth)
  Profit margin = historical minimum [X]%
  Conservative net income = [value] $M (P)

Range width assessment: [Narrow (high predictability) / Wide (low predictability)]
Predictability rating: [HIGH / MEDIUM / LOW]

SaaS / recurring revenue consideration:
  Recurring revenue as % of total: [X]%
  Net revenue retention rate: [X]%
  If recurring > 80% AND retention > 100% → Upgrade predictability by one level
```

### Extrapolation Credibility Rating

```
Rate on 5 dimensions:

| # | Dimension | HIGH | MEDIUM | LOW |
|---|-----------|------|--------|-----|
| ① | Revenue volatility (5-year CV) | < 10% | 10-25% | > 25% |
| ② | Profit metric adjustment magnitude | C_adj/C_rep deviation < 5% | 5-15% | > 15% |
| ③ | Coarse deviation |HH| | < 1 pct | 1-3 pct | > 3 pct |
| ④ | Business model change | No major change | Adjustments but core intact | Business model pivoting |
| ⑤ | λ reliability | Normal | One warning | Multiple warnings or anomalous |

Rating rules:
  ≥ 4 of 5 rated "HIGH" → Extrapolation credibility = HIGH
  Any 2 rated "LOW" → Extrapolation credibility = LOW
  Otherwise → Extrapolation credibility = MEDIUM

This stock's ratings:
  ① = [H/M/L]  ② = [H/M/L]  ③ = [H/M/L]  ④ = [H/M/L]  ⑤ = [H/M/L]
  Extrapolation credibility = [HIGH / MEDIUM / LOW]
```

---

## Factor 3 Output

```
Real Disposable Cash Surplus series (extreme conservative): [year by year]
  Suspected growth capex as % of deductions: [year by year]
  Asset disposal proceeds: [year by year]
  Other investment income: [year by year]
  Non-operating-income-dominated years: [flag which years, if any]
Freely disposable cash reserve: [FF] $M (definition: [broad/narrow])
Factor 3 internal validation: [PASS / VETO (reason)]

Refined Penetration Return Rate: GG = [value]%
  GG (ex-SBC): GG_exSBC = [value]%
  Baseline AA: [AA_2y / AA_all / AA_excl], selection rationale: [explanation]
  AA (ex-SBC): [value] $M
  vs Factor 2 coarse value: R = [value]%, coarse deviation HH = [value] pct
  Deviation source: [if > 2 pct, explain]

Revenue sensitivity analysis:
  Operating leverage λ = [X], reliability = [Normal / Warning / Anomalous]
  CV-based predictability: CV = [X], assessment = [High / Moderate / Low]
  | Revenue Scenario | Refined Return Rate | vs Threshold |
  | 1.0× | [GG]% | [±X pct] |
  | 0.9× | [GG']% | [±X pct] |
  | 0.8× | [GG'']% | [±X pct] |
  | 0.7× | [GG''']% | [±X pct] |
  Critical revenue multiplier: [X]× → Safety margin resilience: [Sensitive / Moderate / Strong]

Distribution willingness: [Strong / Moderate / Weak], basis
Predictability: [HIGH / MEDIUM / LOW], basis

Cross-validation with Factor 1: [Consistent / Factor 3 better than expected / Factor 3 weaker than expected]
Extrapolation credibility: [HIGH / MEDIUM / LOW]
  ① Revenue CV: [H/M/L]  ② Profit adjustment: [H/M/L]  ③ Coarse deviation: [H/M/L]
  ④ Business model: [H/M/L]  ⑤ λ reliability: [H/M/L]

Conservative real disposable cash baseline estimate: AA = [value] $M
Factor 3 Conclusion: [PASS / VETO (reason)]
```

---

## Parameter Validation Block

> At the end of Factor 3 output, append this block with all values populated.
> See `references/factor_interface.md` §3 for type definitions.

```
═══ PARAMETER VALIDATION — FACTOR 3 (REFINED RETURN) ═══

  AA_baseline              = [value] $M
  AA_exSBC                 = [value] $M
  AA_selection             = [AA_2y/AA_all/AA_excl]
  GG_standard              = [value]%
  GG_exSBC                 = [value]%
  GG_primary               = [value]%
  coarse_deviation_HH      = [value] pct
  lambda_sensitivity       = [value]
  lambda_reliability       = [Normal/One warning/Multiple warnings or anomalous]
  critical_revenue_mult    = [value]×
  distribution_willingness = [Strong/Moderate/Weak]
  predictability           = [HIGH/MEDIUM/LOW]
  extrapolation_credibility = [HIGH/MEDIUM/LOW]
  cash_surplus_series      = [list of values] $M
  freely_disposable_cash   = [value] $M
  factor3_conclusion       = [PASS/VETO]

Validation: [ALL POPULATED / MISSING: list]
═══════════════════════════════════════════════════════
```

---

*US Equity Turtle Strategy v2.0 | Factor 3 Reference File*
