# Factor C1: Survival & Quality (Gate)

> This factor is a binary PASS/VETO gate. Stocks that fail C1 are excluded
> from further analysis. The goal is to ensure the company can survive the
> current cycle trough and emerge stronger.

---

## C1-A: Quick Survival Screen (5 Items)

Check these five items. **ALL must pass** or the stock is vetoed.

| # | Check | Pass Condition | Data Source |
|---|-------|---------------|-------------|
| 1 | Liquidity Ratio | Current Ratio >= 1.0 | §4 Balance Sheet |
| 2 | Debt Maturity | No >30% of debt maturing within 12 months relative to cash | §4 Balance Sheet (short-term vs total debt) |
| 3 | Interest Coverage at Trough | EBITDA / Interest Expense >= 1.5 (using trough EBITDA) | §3 Income Statement |
| 4 | Positive Trough FCF | FCF was positive in at least 3 of last 5 years | §5 Cash Flow |
| 5 | No Going-Concern | No going-concern audit opinion; no debt covenant violations | §12 Risk Warnings |

### Calculation Notes

**Trough EBITDA**: Use the minimum EBITDA from the last 5 years as the trough value.
If current EBITDA is the minimum, the company is currently at trough.

**Debt Maturity Proxy**: Compare Short-Term Debt / Total Debt. If > 30% and
Short-Term Debt > Cash, this is a warning but not automatic veto — flag for
manual review.

**Going-Concern**: Check §12 Risk Warnings for any flags. If no §12 section,
assume PASS.

### Output Format

```
C1-A Quick Survival Screen: [PASS / VETO]
  1. Liquidity:       [PASS (CR=X.XX)] / [VETO (CR=X.XX < 1.0)]
  2. Debt Maturity:   [PASS (XX% < 30%)] / [WARNING (XX% > 30%)]
  3. Interest Cover:  [PASS (X.Xx >= 1.5)] / [VETO (X.Xx < 1.5)]
  4. Trough FCF:      [PASS (X/5 years positive)] / [VETO (X/5 < 3)]
  5. Going-Concern:   [PASS] / [VETO (flag: ...)]
```

---

## C1-B: Cyclicality Confirmation

The stock must actually be cyclical. Non-cyclical stocks should use the
Quality Yield framework instead.

### Criteria (at least ONE must be met)

| Metric | Threshold | Calculation |
|--------|-----------|-------------|
| CV(Revenue) | >= 0.15 | StdDev(5yr Revenue) / Mean(5yr Revenue) |
| CV(EBITDA) | >= 0.30 | StdDev(5yr EBITDA) / Mean(5yr EBITDA) |

### Interpretation

| CV(Revenue) | CV(EBITDA) | Classification |
|-------------|------------|----------------|
| >= 0.15 | >= 0.30 | Strongly cyclical |
| >= 0.15 | < 0.30 | Moderately cyclical (revenue-driven) |
| < 0.15 | >= 0.30 | Moderately cyclical (margin-driven) |
| < 0.15 | < 0.30 | Non-cyclical → redirect to Quality Yield |

### Output Format

```
C1-B Cyclicality Confirmation: [PASS / REDIRECT TO QY]
  CV(Revenue): X.XX [>= 0.15: YES/NO]
  CV(EBITDA):  X.XX [>= 0.30: YES/NO]
  Classification: [Strongly / Moderately / Non-cyclical]
```

---

## C1-C: Balance Sheet Stress Test

Ensure the company can endure an extended trough.

| Check | Threshold | Calculation |
|-------|-----------|-------------|
| Net Debt / Mid-Cycle EBITDA | <= 3.0x | (Total Debt - Cash) / Median(5yr EBITDA) |
| 18-Month Cash Runway | PASS | (Cash + Min(5yr OCF)) / (Avg Monthly Opex) >= 18 |

### Mid-Cycle EBITDA

Use `Median(5yr EBITDA)` as the mid-cycle estimate. This is the normalized
earning power the company can sustain over a full cycle.

### Cash Runway Calculation

```
Monthly Burn = (Revenue - EBITDA) / 12   [operating costs per month, trough]
               Use worst-year Revenue and EBITDA
Cash Buffer = Current Cash + Min(5yr OCF, 0)  [if OCF was negative at trough]
Runway Months = Cash Buffer / Monthly Burn
```

If Monthly Burn is negative (company is profitable even at trough), PASS automatically.

### Output Format

```
C1-C Balance Sheet Stress Test: [PASS / VETO]
  Net Debt / Mid-Cycle EBITDA: X.Xx [<= 3.0: PASS/VETO]
    Net Debt = $X,XXXM  (Debt $X,XXXM - Cash $X,XXXM)
    Mid-Cycle EBITDA = $X,XXXM  (Median 5yr)
  Cash Runway: XX months [>= 18: PASS/VETO]
    Trough Cash = $X,XXXM
    Monthly Burn = $XXXM
```

---

## C1-D: Basic Quality Filters

Qualitative checks (use information from data pack and common knowledge):

| # | Check | Action |
|---|-------|--------|
| 1 | No fraud history | Check §12 warnings, known issues |
| 2 | Understandable business | Can you explain what they do in 2 sentences? |
| 3 | Survived prior cycle | Has the company existed for >= 10 years? Survived 2008 or 2020? |
| 4 | Adequate governance | No significant related-party transactions, reasonable insider ownership |

These are soft filters — flag concerns but don't auto-veto unless fraud.

> **Optional cross-reference**: If a shared qualitative report exists at
> `output/{TICKER}/qualitative_report.md` (from `/business-analysis`), import D4 (management)
> and D2 (moat) ratings to supplement checks #2 and #4. This is optional — C1-D can be
> executed independently with the data pack alone.

### Output Format

```
C1-D Quality Filters: [PASS / VETO / CAUTION]
  1. Fraud:       [CLEAR / FLAGGED (reason)]
  2. Business:    [Clear / Complex]
  3. Survived:    [Yes (XX years)] / [No / Unknown]
  4. Governance:  [Adequate / Concern (reason)]
```

---

## C1 Final Verdict

```
Factor C1 Survival & Quality: [PASS / VETO]

  C1-A Quick Survival:       [PASS/VETO]
  C1-B Cyclicality:          [PASS/REDIRECT]
  C1-C Balance Sheet Stress: [PASS/VETO]
  C1-D Quality Filters:      [PASS/VETO/CAUTION]

  Conclusion: [This stock passes the survival gate and is confirmed cyclical.
               Proceed to C2 Cycle Phase Detection.]
              OR
              [VETO: (reason). Exclude from cyclical strategy.]
```

---

*Cyclical Trough Strategy v1.0 | Factor C1 — Survival & Quality*
