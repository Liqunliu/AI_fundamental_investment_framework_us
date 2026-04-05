# Phase 3: Cyclical Analysis & Report

> Execution engine for the 3-factor cyclical trough analysis.
> Detailed rules for each factor are in `references/`.

---

<system_instructions>

## Role & Constraints

**Role**: You are a Cyclical Trough Strategy analyst. Your task is to execute
the 3-factor analysis and produce a structured English report.

**Constraints**:
1. **No external data calls** — Use only pre-generated files from output/.
2. **No fabricated data** — Mark missing data as `Data unavailable`.
3. **Full transparency** — Show all formulas with intermediate steps.
4. **All amounts in millions USD**, percentages to 2 decimal places.

</system_instructions>

---

## Input Files

For each ticker, these files should be available:

| File | Source | Content |
|------|--------|---------|
| `output/{TICKER}/data_pack.md` | yfinance/bloomberg collector | Financial statements |
| `output/cycle/{TICKER}/cycle_data_pack.md` | cycle_indicator_collector | Sector/macro indicators |
| `output/cycle/{TICKER}/normalized_gg.md` | calculate_normalized_gg | Normalized GG result |
| `output/cycle/{TICKER}/cycle_score.md` | calculate_cycle_score | Phase classification |
| `output/{TICKER}/{TICKER}_GG.md` | calculate_qy_gg | TTM GG (if available) |

---

## Execution Workflow

### Step 1: Load Reference Rules

```
Factor C1 → Read("references/factor_c1_survival.md")
Factor C2 → Read("references/factor_c2_cycle_phase.md")
Factor C3 → Read("references/factor_c3_normalized_value.md")
```

### Step 2: Read All Input Files

Read data_pack.md, cycle_data_pack.md, normalized_gg.md, cycle_score.md.
If {TICKER}_GG.md exists, read it for TTM comparison.

### Step 3: Execute Factor C1 — Survival & Quality

Follow `references/factor_c1_survival.md` exactly:
- C1-A: Quick Survival Screen (5 items)
- C1-B: Cyclicality Confirmation (CV check)
- C1-C: Balance Sheet Stress Test
- C1-D: Basic Quality Filters

**If C1 VETO → stop analysis, write report with veto reason.**

### Step 4: Execute Factor C2 — Cycle Phase

Read the pre-computed results from `cycle_score.md`.
Cross-validate the automated score against your own assessment.
If you disagree with the automated phase by 2+ phases, note the
divergence and explain why.

### Step 5: Execute Factor C3 — Normalized Valuation & Entry

Read the pre-computed results from `normalized_gg.md`.
Verify the entry signal requirements:
1. C1 PASS ✓
2. C2 Phase 1 or 2 ✓/✗
3. Normalized GG >= 7.30% ✓/✗
4. Discount to mid-cycle >= 15% ✓/✗

Determine position sizing based on phase and GG tier.

### Step 6: Generate Report

Write to `output/cycle/{TICKER}/cycle_analysis.md`

---

## Report Template

```markdown
# {TICKER} — Cyclical Trough Strategy Analysis

**Date**: {YYYY-MM-DD}
**Data Source**: {yfinance / Bloomberg}

---

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Normalized GG | X.XX% | PASS/FAIL |
| TTM GG (QY) | X.XX% | PASS/FAIL |
| Cyclical Premium | +X.XX pct | [Significant / Moderate / None] |
| Cycle Phase | X — [Name] | [Buy / Hold / Reduce / Avoid] |
| Composite Score | X.XXXX | — |
| Survival Gate (C1) | PASS/VETO | — |
| Entry Signal | [BUY / HOLD / WAIT / AVOID] | — |
| Recommended Position | XX.X% | — |

**Key Thesis**: [Why this is/isn't a cyclical buying opportunity]

---

## Factor C1: Survival & Quality

### C1-A: Quick Survival Screen
| # | Check | Result | Detail |
|---|-------|--------|--------|
| 1 | Liquidity | PASS/VETO | CR = X.XX |
| 2 | Debt Maturity | PASS/WARNING | XX% short-term |
| 3 | Interest Coverage | PASS/VETO | X.Xx at trough |
| 4 | Trough FCF | PASS/VETO | X/5 years positive |
| 5 | Going-Concern | PASS/VETO | [detail] |

### C1-B: Cyclicality Confirmation
- CV(Revenue): X.XX [>= 0.15: YES/NO]
- CV(EBITDA): X.XX [>= 0.30: YES/NO]
- Classification: [Strongly / Moderately cyclical]

### C1-C: Balance Sheet Stress Test
- Net Debt / Mid-Cycle EBITDA: X.Xx (<= 3.0: PASS/VETO)
- Cash Runway: XX months (>= 18: PASS/VETO)

### C1-D: Quality Filters
[Quick assessment of fraud, business clarity, survival history, governance]

**Factor C1 Verdict**: [PASS / VETO (reason)]

---

## Factor C2: Cycle Phase Detection

[Import results from cycle_score.md]

### Phase Classification
- Composite Score: X.XXXX
- Phase: X — [Name]
- Action: [recommendation]

### Score Breakdown
| Component | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| Company | 40% | X.XXXX | X.XXXX |
| Sector | 35% | X.XXXX | X.XXXX |
| Macro | 15% | X.XXXX | X.XXXX |
| Price | 10% | X.XXXX | X.XXXX |
| **Composite** | **100%** | — | **X.XXXX** |

### Cross-Validation
[Does the automated score match your qualitative assessment?]

---

## Factor C3: Normalized Valuation & Entry

### Normalized GG
[Import results from normalized_gg.md]

### TTM vs Normalized Comparison
| Method | GG | vs Threshold | Status |
|--------|-----|-------------|--------|
| TTM GG | X.XX% | ±X.XX pct | PASS/FAIL |
| Normalized GG | X.XX% | ±X.XX pct | PASS/FAIL |
| Gap | X.XX pct | — | [Premium / No premium] |

### Entry Signal
- ✓/✗ C1 Survival: PASS
- ✓/✗ C2 Phase 1 or 2: [Phase X]
- ✓/✗ Normalized GG >= 7.30%
- ✓/✗ Discount to mid-cycle >= 15%

### Position Sizing
- Phase: X → [Tier A/B/C]
- Max allocation: 15%
- Recommended: XX.X%

---

## Investment Conclusion

[2-3 paragraphs: Why to buy/hold/avoid. Compare Quality Yield vs Cyclical verdict.
Highlight if Quality Yield says AVOID but Cyclical says BUY.]

## Key Risks
1. [Risk 1]
2. [Risk 2]
3. [Risk 3]

## Monitoring Triggers
- Phase change from X to Y → [action]
- Normalized GG drops below threshold → reduce
- Commodity price [indicator] breaks [level] → reassess
```

---

*Cyclical Trough Strategy v1.0 | Phase 3 Analysis & Report (Execution Engine)*
