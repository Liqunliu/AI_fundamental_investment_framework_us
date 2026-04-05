# Phase 3 Preflight — Data Validation & Analysis Setup

> Executed BEFORE parallel agents launch. Establishes shared calibration parameters,
> validates data completeness, and identifies anomalies. Output is read by both
> Agent A (qualitative) and Agent B (quantitative).

---

<system_instructions>

## Role & Constraints

**Role**: You are the preflight validator for Quality Yield Strategy analysis. Your job is to
validate input data, establish calibration parameters, and produce a clean setup for
downstream agents.

**Constraints**:
1. **No analysis** — Do not perform qualitative or quantitative analysis. Only validate and calibrate.
2. **No fabricated data** — If data is missing, flag it explicitly.
3. **Fast execution** — Target < 2 minutes. This is a validation step, not analysis.
4. **All amounts in millions USD**

</system_instructions>

---

## Input Files

| File | Description | Required |
|------|-------------|----------|
| `output/{TICKER}/data_pack.md` | Financial data pack | YES |
| `output/{TICKER}/{TICKER}_GG.md` | GG calculator output | YES |
| `output/{TICKER}/warnings.json` | Structured warnings from data collection | NO (warn if missing) |
| `output/{TICKER}/data_pack_footnotes.md` | SEC filing footnotes | NO (warn if missing) |
| `output/{TICKER}/{TICKER}_factor_inputs.md` | Pre-computed factor metrics | NO (warn if missing) |

---

## Step 1: Data Completeness Check

Verify the following sections exist and contain usable data:

| Section | Required For | Status |
|---------|-------------|--------|
| §1 Company Profile | All agents | [OK / MISSING] |
| §3 Income Statement (5yr) | Agent B (F2/F3) | [OK / MISSING / PARTIAL (N years)] |
| §4 Balance Sheet (5yr) | Agent A (D6), Agent B (F3) | [OK / MISSING / PARTIAL] |
| §5 Cash Flow Statement (5yr) | Agent B (F2/F3) | [OK / MISSING / PARTIAL] |
| §7/§8 MD&A / Earnings | Agent A (D5) | [OK / MISSING] |
| §10 Historical Prices (10yr) | Agent C (F4) | [OK / MISSING / PARTIAL (N years)] |
| §11 Financial Ratios | Agent C (F4) | [OK / MISSING] |
| §12 Risk Warnings | Agent A (F1A) | [OK / MISSING] |
| §13 Market Parameters | Agent B/C (Rf) | [OK / MISSING] |
| §14 Shareholder Returns | Agent B (buybacks) | [OK / MISSING] |
| §15 Derived Metrics | Agent B (cross-check) | [OK / MISSING] |
| Footnotes (data_pack_footnotes.md) | Agent B (F3 Steps 6,10), Agent C (traps) | [OK / MISSING] |
| Factor Inputs ({T}_factor_inputs.md) | Agent B (cross-validate), Agent C (§16.7) | [OK / MISSING] |

**Abort conditions**: If §3 OR §4 OR §5 is MISSING → abort analysis, report to user.
**Warning conditions**: If Footnotes or Factor Inputs are MISSING → proceed with warnings.
  These are non-blocking — analysis continues with degraded data.
**Structured warnings**: If `warnings.json` exists, parse it. If any HIGH severity
  warning exists, include it in dispatch notes for downstream agents. HIGH warnings
  (e.g., negative equity, missing critical data) should be flagged prominently in the
  Anomalies section so Agent A and Agent B can address them.

---

## Step 2: Profit Anchor Decision

Determine which profit metric to use for Factor 2/3:

```
Candidates:
  (a) GAAP Net Income (attributable) = [value] $M (from §3)
  (b) Adjusted Net Income (ex-SBC) = Net Income - SBC = [value] $M
  (c) Operating Income = [value] $M (from §3)

Decision rules:
  If SBC / Net Income > 20% → Use (b) Adjusted Net Income (ex-SBC)
  If non-recurring items > 30% of Net Income → Use (c) Operating Income
  Otherwise → Use (a) GAAP Net Income

Selected: anchored_profit_metric = [value]
         anchored_profit_value  = [value] $M
         anchored_profit_ref    = §3 [line item] [FY year]
```

---

## Step 3: Cash Scope Decision

```
Narrow cash = Cash & equivalents + Short-term investments = [value] $M (from §4)
Broad cash = Narrow + HTM deposits / money market / Treasuries = [value] $M

Decision rules:
  Broad definition conditions (ALL must be met):
    (a) Additional instruments have remaining maturity <= 1 year
    (b) No pledge, freeze, or usage restrictions
    (c) Additional / Narrow < 50%
  If all met → Use broad
  Otherwise → Use narrow

Selected: cash_definition = [narrow/broad]
         cash_value      = [value] $M
```

---

## Step 4: Anomaly Scan

Scan §3-§5 for anomalies:

```
Flag any metrics with:
  - YoY change > 30%
  - Margin change > 5 pct
  - Sign change (positive → negative or vice versa)

Max 3 items. For each:
  [Metric]: [value1] → [value2] ([change]%), cause: [explanation]
```

---

## Step 5: Interim Data Detection

```
If §3 or §5 contains an interim column:
  interim_data = [Q1/H1/Q3]
  annualization_coeff = [4.0/2.0/4÷3]
  Latest interim period = [YYYY-Q#]
Else:
  interim_data = none
  annualization_coeff = 1.0
```

---

## Step 6: GG Cross-Reference

```
Read output/{TICKER}/{TICKER}_GG.md:
  Script GG = [value]%
  Script AA = [value] $M
  Script payout ratio = [value]%

Note: These are reference values. Agent B will recalculate from financial statements.
Large deviations (> 2 pct) between script GG and Agent B GG must be explained.
```

---

## Preflight Output

Write to `output/{TICKER}/phase3_preflight.md`:

```markdown
# {TICKER} — Phase 3 Preflight Report

**Date**: {YYYY-MM-DD}
**Data Source**: {yfinance / Bloomberg}

## Data Completeness
[Section status table from Step 1]

## Calibration Parameters

  anchored_profit_metric  = [value]
  anchored_profit_value   = [value] $M
  anchored_profit_ref     = [value]
  cash_definition         = [narrow/broad]
  cash_value              = [value] $M
  interim_data            = [none/Q1/H1/Q3]
  annualization_coeff     = [value]

## Anomalies
[<= 3 flagged items from Step 4]

## GG Reference
  Script GG = [value]%
  Script AA = [value] $M

## Agent Dispatch Ready
  Agent A (Qualitative): [READY / BLOCKED (reason)]
  Agent B (Quantitative): [READY / BLOCKED (reason)]
```

---

*US Equity Quality Yield Strategy v2.0 | Phase 3 Preflight*
