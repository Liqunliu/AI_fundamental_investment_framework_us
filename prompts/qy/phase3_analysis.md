# Phase 3: Analysis & Report — US Equity Quality Yield Strategy

> **Dispatch guide for the parallel agent architecture.**
> This file defines the execution engine's common rules and report template.
> Individual agent instructions are in their own files:
> - `phase3_preflight.md` — Data validation & calibration
> - `phase3_quantitative.md` — Agent B (Factor 2 + Factor 3)
> - `phase3_valuation.md` — Agent C (Factor 4 + synthesis)
> - `prompts/shared/qualitative/qualitative_assessment.md` — Shared qualitative framework
>
> Factor-specific detailed rules are in `references/`:
> - `factor1_asset_quality.md` — QY-specific F1 modules
> - `factor2_coarse_return.md` — Coarse return rate steps
> - `factor3_refined_return.md` — Refined return rate steps
> - `factor4_valuation.md` — Valuation & safety margin steps
> - `factor_interface.md` — Parameter contracts between agents

---

<system_instructions>

## Common Rules (Apply to All Agents)

**Constraints**:
1. **No external data calls** — All analysis uses only `data_pack.md` and `{TICKER}_GG.md` from the output folder.
2. **No fabricated data** — If a metric is missing, mark it `Data unavailable` and use a degraded approach.
3. **Full transparency** — Every numerical result must show the complete formula and intermediate steps.
4. **Parameter contracts** — Each agent MUST output a parameter validation block per `references/factor_interface.md`.

**Output format**:
- Markdown file
- **All amounts in millions USD**, comma-separated (e.g., $96,886.00M)
- Percentages to 2 decimal places
- All key judgments must include supporting evidence

**Payout ratio rules**:
- Payout ratio = Total dividends paid / Net income (same period)
- Preferred source: §5 Cash Flow (dividends paid line) + §3 Income Statement (net income)
- **Do NOT use yfinance `payoutRatio` field** — must calculate manually from statements

</system_instructions>

---

## Progressive Disclosure: Factor Reference Loading

**Key mechanism**: Before executing each factor, load the corresponding detailed rules file from `references/`.

```
Factor Interface → Read("references/factor_interface.md")  ← load once at start
Factor 1 → Read("references/factor1_asset_quality.md")
Factor 2 → Read("references/factor2_coarse_return.md")
Factor 3 → Read("references/factor3_refined_return.md")
Factor 4 → Read("references/factor4_valuation.md")
```

> **Parameter contracts**: `references/factor_interface.md` defines the typed parameters
> passed between agents. Each factor output MUST include a parameter validation block
> (see the interface file for the exact format). Factor 4 MUST validate inbound parameters
> before executing.

---

## Agent Architecture

```
Preflight (phase3_preflight.md)
  → Data validation, profit anchor, cash scope, anomaly scan
  → Writes: phase3_preflight.md

Agent A ‖ Agent B (parallel)
  Agent A: F1A + shared qualitative (D1-D6) + QY M6/M11-M15
    → Writes: phase3_qualitative.md
  Agent B: F2 (Steps 1-4) + F3 (Steps 5-13)
    → Writes: phase3_quantitative.md

Agent C (sequential, after A+B complete)
  → F4 (Steps 1-6) + cross-validation + report assembly
  → Writes: {TICKER}_analysis_report.md
```

### Veto Propagation

```
F1A VETO → Agent A stops, Agent B continues (may VETO independently at F2)
F2 VETO  → Agent B stops, Agent C reads VETO from both agents
F3 VETO  → Agent B marks VETO, Agent C reads from output
Any VETO → Agent C assembles partial report noting veto point
```

---

## Interim Data Handling

When data_pack §3 contains an interim column (e.g., 2025Q3, 2025H1):

| Statement | Interim | Annualization |
|-----------|---------|---------------|
| Income Statement / Cash Flow (§3/§5) | Q3 | x 4/3 |
| Income Statement / Cash Flow | H1 | x 2 |
| Balance Sheet (§4) | Any | No annualization — use latest point value |

Priority: Q3 > H1 > Q1 (Q3 annualization has smallest bias)

Use for: FY0(Ann.) column in financial trend overview; Factor 2 current-period OE and R% reference
Do NOT use for: Payout ratio (use FY data only); 5-year average series (use FY data only)

---

## Report Template

```markdown
# {TICKER} — Quality Yield Strategy Analysis Report

**Date**: {YYYY-MM-DD}
**Data Source**: {yfinance / Bloomberg}
**Analyst**: Quality Yield Strategy Agent (Parallel Architecture v2.0)

---

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| GG (Penetration Return Rate) | [value]% | [PASS/FAIL] |
| GG (ex-SBC) | [value]% | [PASS/FAIL] |
| Safety Margin | [value] pct | [Thick/Thin/Negative] |
| Threshold II | [value]% | Rf [value]% + 3% |
| Value Trap Risk | [LOW/MEDIUM/HIGH] | — |
| Extrapolation Credibility | [HIGH/MEDIUM/LOW] | — |
| Rating | [BUY/WATCH/AVOID] | — |
| Recommended Position Size | [value]% | — |

**Greatest Strength**: {one sentence}
**Greatest Risk**: {one sentence}

---

## 1.5 Financial Trend Overview (Recent 5 Years)

| Metric | FY-4 | FY-3 | FY-2 | FY-1 | FY0(TTM) | FY0(Ann.) | 5yr CAGR |
|:-------|:----:|:----:|:----:|:----:|:--------:|:---------:|:--------:|
| Revenue ($M) | | | | | | | |
| Net Income ($M) | | | | | | | |
| OCF ($M) | | | | | | | |
| ROE (%) | | | | | | | |
| SBC ($M) | | | | | | | |
| DPS ($) | | | | | | | |
| Payout Ratio (%) | | | | | | | |

---

## Factor 1: Asset Quality & Business Model (Agent A)

### 1A: Quick Screen
{6-item check table}

### 1B: Qualitative Assessment
{D1-D6 from shared qualitative + M6, M11-M15 from QY-specific}

### 1B Summary
{Module assessments, qualitative parameters, calibration decisions}
**Factor 1 Conclusion**: {PASS / VETO}

---

## Factor 2: Coarse Return Rate (Agent B)
{Steps 1-4 results}
**Factor 2 Conclusion**: {PASS / VETO}

---

## Factor 3: Refined Return Rate (Agent B)
{Steps 5-13 results}

### Revenue Sensitivity Analysis
{4-scenario table + critical multiplier}

### Extrapolation Credibility
{5-dimension scoring table}

**Factor 3 Conclusion**: {PASS / VETO}

---

## Factor 4: Valuation & Safety Margin (Agent C)
{Steps 1-6 results}

### Value Trap Screening
{5-item checklist + N-count risk scoring}

### Performance Decline Sensitivity
{Table 1: cumulative annual -10% for 1-3 years}
{Table 2: single-year -10%/-20%/-30%}

### Position Matrix
{Full matrix: margin x credibility x trap risk -> position %}

**Factor 4 Conclusion**: {PASS / Exclude}

---

## Cross-Validation
{Agent A vs Agent B consistency assessment}

## Investment Conclusion
[Final verdict with key reasoning]

## Risk Factors
[Top 3-5 risks specific to this stock]

## Monitoring Checklist
[Key metrics to track quarterly]
```

---

*US Equity Quality Yield Strategy v2.0 | Phase 3 Analysis & Report (Dispatch Guide)*
