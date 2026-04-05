# Porting Turtle v2_beta Changes to US Framework

**Date**: 2026-04-05
**Source**: Turtle_investment_framework commits `c291fad` + `29fef5f` (v2_beta)
**Target**: AI_fundamental_investment_framework_us (current: `49a986b`)

---

## Overview

Turtle v2_beta introduced several architectural changes. This doc identifies which changes are applicable to the US framework and provides implementation specs.

---

## HIGH Priority — Implement

### 1. Revenue & Profit Quality Decomposition (D1 Enhancement)

**Source**: `shared/qualitative/qualitative_assessment_v2.md` — new D1 sub-sections

**What it adds**:
- **Revenue quality breakdown**: Separate core revenue (main business, recurring) from low-quality revenue (one-time gains, government subsidies, related-party transactions, investment income). Calculate core revenue growth rate independently.
- **Profit quality breakdown**: Decompose profit drivers (gross margin vs SGA vs non-operating), detect non-operational profit contribution (>15% = warning), check for hidden fee manipulation (capitalized expenses, off-balance-sheet items), calculate core operating profit growth.
- **Cross-validation section**: Number-vs-narrative consistency check, core contradictions surfacing, overlooked signals detection.

**Target file**: `prompts/shared/qualitative/qualitative_assessment.md`

**Why it matters**: The NVO analysis surfaced issues (AP spike, capex explosion, 340B one-time revenue) that a structured quality decomposition would flag more systematically. PFE's structural capital allocation problem would also be caught earlier.

**Implementation**:
1. Add revenue quality sub-section under D1 (Financial Health) — after existing revenue/margin analysis
2. Add profit quality sub-section under D1 — after revenue quality
3. Add cross-validation section at end of assessment (after D6)
4. Keep US-specific terminology (SEC filings, GAAP, 10-K/20-F references)

---

### 2. Investment Thesis Card (Agent C Report Enhancement)

**Source**: `strategies/turtle/phase3_valuation.md` — new sections 10.1-10.4 in report template

**What it adds**:
- **10.1 Investment thesis summary**: Core thesis statement, buy rationale (<=5 bullet points with data), expected catalysts, expected holding period
- **10.2 Fundamental stop-loss conditions**: Structured rules table with 7 quantitative conditions, severity levels (critical/warning), natural language conditions for monitoring
- **10.3 Event monitoring checklist**: WebSearch keywords (high/low priority), event type classification with priority and thesis linkage
- **10.4 Industry & macro monitoring**: Industry keywords, competitor watch list (name + ticker), macro attention dimensions

**Target file**: `prompts/qy/phase3_valuation.md`

**Why it matters**: The NVO report has a monitoring checklist but lacks structured stop-loss conditions, search keywords, and competitor tracking. This makes portfolio management more actionable — especially for WATCH-rated stocks where re-evaluation timing matters.

**Implementation**:
1. Add Thesis Card as new section in Agent C report template (after Investment Conclusion, before Risk Factors)
2. Adapt stop-loss conditions for US context:
   - GG falls below -5% (critical)
   - Payout ratio exceeds 90% for 2 consecutive quarters (critical)
   - Revenue declines >10% YoY (warning)
   - Debt/EBITDA exceeds 4.0x (warning)
   - Dividend cut >20% (critical)
   - Moat rating downgraded from WIDE to NARROW (warning)
   - Management turnover — CEO departure (warning)
3. Event monitoring keywords in English: "earnings miss", "dividend cut", "CEO resign", "FDA reject", "patent expire", "downgrade", "buyback suspend", etc.
4. Competitor watch list populated from Agent A's D2 (moat) analysis

---

### 3. Factor Interface: Competitors & Industry Keywords

**Source**: `strategies/turtle/references/factor_interface.md` — new Agent A → Agent C params

**What it adds**:
- `competitors`: List of competitor names + tickers from D2 moat analysis (e.g., `["Eli Lilly (LLY)", "AstraZeneca (AZN)"]`)
- `industry_keywords`: List of industry monitoring search terms from D3 (e.g., `["GLP-1", "obesity drug", "semaglutide", "tirzepatide"]`)

**Target file**: `prompts/qy/references/factor_interface.md`

**Why it matters**: Required by the Thesis Card (#2 above) for event monitoring and competitor tracking. Without these params in the interface contract, Agent C can't populate sections 10.3-10.4.

**Implementation**:
1. Add both parameters to Agent A → Agent C parameter block
2. Define value domains and example values

---

## LOW Priority — Not Applicable

### Preflight Merged into Agent B (Step 0)

**Why skip**: US framework uses parallel Agent A || Agent B architecture. Both agents consume preflight output. Merging preflight into Agent B would break Agent A's access to calibration parameters (profit anchor, cash scope, anomalies) unless Agent A independently derives them, adding redundant work. The serial Turtle architecture (Agent B → Agent C) naturally benefits from this merge; the parallel US architecture does not.

### PDF-First Architecture

**Why skip**: US framework uses EDGAR HTML filings (parsed by `edgar_parser.py`) + yfinance data packs, not PDF annual reports. The PDF-first approach was designed for Chinese A-share companies where annual report PDFs are the canonical source.

### Decoupled Qualitative as Prerequisite

**Why skip**: Turtle moved to sequential (qualitative first, then quantitative) because it switched to single-agent mode. US framework's parallel Agent A || Agent B is more time-efficient and doesn't suffer from information silos since both agents share the same data_pack.md + preflight.

### Coordinator Restructuring

**Why skip**: US coordinator already well-structured for its parallel architecture. Turtle's simplification came from decoupling qualitative, which we're not doing.

### Standalone Valuation Module (`/valuation`)

**Why skip for now**: 1500-line Python script (`valuation_engine.py`) + 5 reference files built around Tushare data and Chinese market conventions. Porting requires adapting to yfinance/Bloomberg + US GAAP. This is a separate project, not a delta.

### Single-Agent Mode for Qualitative

**Why skip**: Turtle found single-agent cross-validation superior for qualitative analysis. However, the US Agent A runs qualitative only (D1-D6 + F1A), not both qual + quant. The benefit of single-agent mode is eliminating information silos between dimensions, but Agent A already processes all qualitative dimensions in one context window.

---

## Implementation Order

```
Step 1: prompts/shared/qualitative/qualitative_assessment.md
        → Add revenue quality decomposition (D1 sub-section)
        → Add profit quality decomposition (D1 sub-section)
        → Add cross-validation section (after D6)

Step 2: prompts/qy/references/factor_interface.md
        → Add competitors + industry_keywords to Agent A → C contract

Step 3: prompts/qy/phase3_valuation.md
        → Add Investment Thesis Card (sections 10.1-10.4)
        → Reference competitors + industry_keywords from factor_interface
```

Steps 1 and 2 can be done in parallel. Step 3 depends on Step 2 (needs the interface params).

---

## Validation

After implementation, validate by re-running NVO analysis:
- Agent A should now produce revenue/profit quality decomposition + competitors list
- Agent C should produce a Thesis Card with stop-loss conditions + monitoring keywords
- Cross-check that the Thesis Card's NVO monitoring items match the ad-hoc checklist from the current report

---

*Analysis based on Turtle v2_beta (2026-04-05) → US Framework port assessment*
