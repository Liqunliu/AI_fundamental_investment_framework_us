# Business Analysis — Standalone Qualitative Assessment

## Overview

The `/business-analysis` skill performs a standalone 6-dimension qualitative assessment of a company.
It produces a `qualitative_report.md` that can be used independently or as input to strategy-specific
analyses (Quality Yield, Cigar Butt, Cyclical, Valuation).

## Usage

```
/business-analysis AAPL
/business-analysis NVO --source bloomberg
```

## Pipeline

```
Step 1: Data Collection (5 min)
  yfinance_collector.py → output/{TICKER}/data_pack.md
  (skipped if data_pack.md exists and < 7 days old)

Step 2: Qualitative Assessment (8 min)
  LLM analyzes data_pack.md using 6-dimension framework
  → output/{TICKER}/qualitative_report.md
```

## 6 Dimensions

| Dimension | What It Assesses | Output |
|-----------|-----------------|--------|
| D1: Business Model & Capital | Revenue/profit quality, capital intensity, payment pattern, model classification | `capital-light/hungry`, profit quality rating |
| D2: Moat & Competitive Advantage | Two-tier moat (business + technical), pricing power, flywheel | `WIDE/NARROW/NONE`, compound flywheel |
| D3: External Environment | Cyclicality, regulatory/policy risk | `strong/weak/non-cycle`, regulatory risk |
| D4: Management & Governance | CEO tenure, capital allocation track record, related-party transactions | `Excellent/Adequate/Destroying value` |
| D5: MD&A Interpretation | Forward guidance credibility, narrative consistency | `HIGH/MEDIUM/LOW` credibility |
| D6: Complex Structure | SOTP vs market cap, holding discount (conditional — only for holding companies) | Discount decomposition |

### Revenue & Profit Quality (D1-C, D1-D — New in v2)

D1 now includes deeper quality decomposition:

- **Revenue quality**: Separates core recurring revenue from low-quality items (one-time gains,
  related-party, subsidies). Calculates core revenue growth rate independently.
- **Profit quality**: Decomposes profit growth into gross margin, expense efficiency, and
  non-operational items. Flags if non-operational contribution exceeds 15%.

### Cross-Validation (New in v2)

After D1-D6, a cross-validation section checks:
- Number vs narrative consistency across dimensions
- Core contradictions (e.g., "WIDE moat" but declining gross margins)
- Overlooked signals (auditor changes, insider selling, concentration risk)

## Output Schema

The qualitative report ends with a structured summary block:

```
═══ QUALITATIVE ASSESSMENT SUMMARY ═══

D1 — Business Model & Capital:
  Capital intensity, payment pattern, business model type
  Revenue quality: core share, core growth vs headline
  Profit quality: rating, non-operational contribution

D2 — Competitive Advantage & Moat:
  Moat rating, moat type, compound flywheel, pricing power

D3 — External Environment:
  Cyclicality, cycle position, regulatory risk

D4 — Management & Governance:
  Management rating, capital allocation summary

D5 — MD&A Interpretation:
  Credibility, key findings, impact

D6 — Complex Structure:
  Holding structure, discount (if applicable)

Cross-Validation:
  Consistency, contradictions, overlooked signals

Competitors: [list for monitoring]
Industry keywords: [list for monitoring]

Overall Business Quality: [A / B / C / D]
Qualitative Conclusion: [PASS / VETO]
═══════════════════════════════════════
```

## Integration with Other Strategies

The qualitative report is consumed by strategy-specific analyses:

| Strategy | How It Uses qualitative_report.md |
|----------|----------------------------------|
| `/us-qy` | Agent A output (F1 Asset Quality). Competitors + industry_keywords feed the Thesis Card. |
| `/us-cigar` | Fact check — validates business is operational, not a shell. |
| `/us-cycle` | Factor C1-D — survival assessment during trough. |
| `/valuation` | Qualitative adjustments to DCF growth rates, terminal value, and governance discount. |

## Key Files

| File | Description |
|------|-------------|
| `prompts/shared/qualitative/qualitative_assessment.md` | Main assessment framework |
| `prompts/shared/qualitative/references/framework_guide.md` | Moat classification definitions |
| `prompts/shared/qualitative/references/market_rules_us.md` | US GAAP and regulatory specifics |
| `prompts/shared/qualitative/references/judgment_examples.md` | Calibration examples |
| `prompts/shared/qualitative/references/output_schema.md` | Typed parameter definitions |
| `.claude/skills/business-analysis/skill.md` | Skill entry point |

## Examples

After running `/business-analysis NVO`, you get:

```
| Dimension | Rating | Key Finding |
|-----------|--------|-------------|
| D1: Business Model | Capital-hungry manufacturing | GLP-1 biologics, 33% net margin |
| D2: Moat | WIDE | Dual-layer: brand + technical, compound flywheel |
| D3: Environment | Non-cycle, Neutral regulatory | Beta 0.272, FDA/IRA exposure |
| D4: Management | Excellent | Jorgensen 9yr tenure, Foundation governance |
| D5: MD&A | HIGH | Market share loss acknowledged, guidance consistent |
| D6: Structure | N/A | Simple operating structure |

Overall Quality: A
```

Suggested next steps based on results:
- Quality A/B → `/us-qy NVO` for full Quality Yield analysis
- Capital-hungry + cyclical → `/us-cycle CAT` for Cyclical analysis
- Low P/B deep value → `/us-cigar` for Cigar Butt screening

---

*Business Analysis Module v2.0*
