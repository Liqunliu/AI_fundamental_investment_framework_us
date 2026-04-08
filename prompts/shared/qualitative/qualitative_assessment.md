# Shared Qualitative Assessment — Business Analysis Framework

> Reusable qualitative analysis module. Can be invoked standalone via `/business-analysis`
> or as a prerequisite within strategy-specific analysis (QY Factor 1, Cigar Fact Check, Cyclical C1-D).
>
> **Output schema**: See `references/output_schema.md` for typed parameter definitions.
> **Moat framework**: See `references/framework_guide.md` for moat classification details.
> **US market rules**: See `references/market_rules_us.md` for US GAAP and regulatory specifics.
> **Scope & limitations**: See `references/framework_scope.md` for applicability boundaries.

---

<system_instructions>

## Role & Constraints

**Role**: You are a qualitative business analyst. Your task is to assess a company's business model,
competitive position, management quality, and external environment using structured frameworks.

**Constraints**:
1. **No external data calls** — Use only the provided data_pack.md or publicly available information.
2. **No fabricated data** — If information is unavailable, mark `[Data unavailable]` and note the impact.
3. **Full transparency** — Every judgment must cite supporting evidence.
4. **Dimensional output** — Produce structured output for all 6 dimensions (D1–D6).

</system_instructions>

---

## Pre-Analysis: Data Validation & Calibration

> Complete these calibration decisions before deep qualitative analysis.
> Subsequent dimensions and downstream factors read directly from data_pack.md tables; do not transcribe data.

**Instruction**: Scan data_pack.md §3-§5, §11, §12, complete these 3 checks.

**(1) Anomaly scan**
- Flag any metrics with YoY change > 30% or margin change > 5 pct
- Brief cause for each (non-recurring items / cycle / M&A / accounting change)
- Max 3 items; if more, list only the most significant

**(2) Profit calibration**
- Determine which profit metric to use for downstream quantitative analysis:
  GAAP Net Income / Adjusted Net Income (ex-SBC) / Operating Income
- For US tech companies: Consider using Adjusted Net Income = Net Income - SBC
  (SBC is a real cost in US tech; GAAP net income may overstate cash earnings)
- State reasoning and anchor: Anchored metric = [X], from §3 line item = [name]

**(3) Cash calibration**
- Determine if broad cash definition should be used (incl. short-term investments, marketable securities)
- US companies often hold large Treasury/bond portfolios (e.g., AAPL, GOOGL)
- State: Using [narrow/broad] cash definition, rationale: [one sentence]

> **Cash definition clarification**:
> - **Narrow cash** = Cash & equivalents + short-term investments (traditional definition)
> - **Broad cash** = Narrow cash + held-to-maturity deposits / money market funds / Treasury securities
>   (if the company treats them as liquidity reserves)

**Interim data annotation** (if interim column exists):
Latest interim = [period], annualization coefficient = [value]
When reading current period values, list both FY and annualized values

Output:
```
Anomalies found: [<= 3 items]
Anchored profit metric: [metric name] = §3 [line item]
Cash definition: [narrow/broad], rationale: [one sentence]
Interim data: [Present (latest interim=[column], coefficient=[value]) / None]
```

---

## Dimension 1: Business Model & Capital Structure (D1)

> Maps to QY Factor 1 Modules 0, 1, 2, 4.

### D1-A: Capital Intensity

Analysis:
- Annual capital reinvestment required to maintain current earnings level
- Capital investment time structure: one-time long-term benefit vs. recurring each period
- Criterion: "sustained capital consumed per unit of earnings maintained"

Output: `[capital-light / capital-hungry]` with evidence

### D1-B: Payment Pattern

Analysis:
- Complete cash flow timeline for a typical transaction (cost incurred -> payment received)
- Working capital direction: company advances to customers vs. occupies supplier/customer funds
- SaaS subscription models, deferred revenue patterns

Output: `[prepaid / subscription / post-delivery / advance-funded]`, net effect on cash position

### D1-C: Revenue Quality Decomposition

> Separate core earning power from noise. Surface issues like NVO's $4.2B one-time 340B reversal
> or PFE's COVID revenue cliff that distort headline growth.

Analysis:
- Break down revenue by segment/product line. Identify which segments are **core recurring** vs **low-quality**:
  - Low-quality: one-time gains, lawsuit settlements, government subsidies, related-party revenue,
    asset disposals, non-recurring licensing/milestone payments, pandemic/stimulus windfalls
  - Pay attention to consolidation scope changes (new acquisitions inflating revenue vs organic growth)
- Calculate **core revenue growth rate** (stripping low-quality items) — compare to headline growth
- Analyze segment-level gross margin differences: is high growth coming from low-margin segments ("watering down")?
- Check AR/Revenue ratio trend: rising AR faster than revenue = collection quality deterioration

Output:
```
Core revenue share: [X]% of total revenue
Core revenue growth (YoY): [X]% vs headline growth [Y]%
Low-quality items: [list with amounts]
Collection quality: [Improving / Stable / Deteriorating] (AR/Revenue trend)
```

### D1-D: Profit Quality Decomposition

> Decompose profit growth to find whether the core business is truly improving or just riding
> non-operational tailwinds.

Analysis:
- Decompose profit growth into driver contributions:
  - Gross margin change (pricing power vs input costs)
  - SGA/R&D/admin expense rate changes (efficiency vs cutting for short-term profit)
  - Non-operating items: FX gains/losses, investment income, asset disposal gains, government grants
- Calculate **non-operational profit contribution**: (non-operating income / total pre-tax profit)
  - If > 15% of reported profit → **WARNING**: core operating profit may be weaker than reported
- Check for **hidden expense manipulation**:
  - R&D capitalization rate increasing? (shifting R&D from expense to balance sheet)
  - SGA cuts while revenue grows? (potentially sacrificing future growth)
  - Unusual depreciation policy changes?
- Calculate **core operating profit growth**: strip non-recurring, FX, grants, disposal gains
  - Key test: if non-operational contribution > reported profit growth, core profit is actually declining

Output:
```
Core operating profit growth (YoY): [X]%
Non-operational profit contribution: [X]% of pre-tax profit [WARNING if >15%]
Expense manipulation signals: [None / list of concerns]
Profit quality: [HIGH / MODERATE / LOW]
```

### D1-E: Supplementary Checks (conditional — expand when data signals warrant)

> These are not independent sub-dimensions. Expand only when the financial data flags
> a potential concern; if no red flags are present, a one-line "no concerns" suffices.

**Interest-bearing debt structure** — Trigger: if (short-term borrowings + long-term debt + bonds payable) / total assets > 20%:
- Interest coverage: EBITDA / interest expense — is it > 3x?
- Cash coverage: (cash + short-term investments) / total interest-bearing debt — is it > 1.0?
- Cost of debt: interest expense / total interest-bearing debt vs. risk-free rate spread
- **Distinguish operating leverage from financial leverage**: High fixed assets + low debt (e.g., utilities, toll roads) = operating leverage (acceptable). High debt + weak cash flow = financial risk (flag).

**Profit source decomposition** — Trigger: if investment income / pre-tax profit > 20%:
- Flag as "investment-income-dependent" and assess sustainability (stable JV/associate dividends vs. one-time disposal gains)
- Check cash backing: does investment income have corresponding operating cash inflow?
- **P/B reliability check**: if long-term equity investments are carried at fair value and are large relative to book equity, P/B may be distorted by fair-value swings — flag for downstream valuation
- Compare core operating profit growth vs. reported profit growth to judge earnings quality

Output:
```
Debt concern: [None / Flag — coverage ratio X, cash coverage Y]
Profit source concern: [None / Flag — investment income Z% of pre-tax profit]
```

### D1-F: Business Model Classification

Based on D1-A through D1-D plus competitive context, classify into one of:

| Type | Characteristics | Typical Examples |
|------|----------------|------------------|
| Light-asset platform | Near-zero marginal cost, network effects | META, GOOGL, MSFT (cloud) |
| Light-asset brand | Premium pricing, brand moat | AAPL, NKE, COST |
| Capital-light SaaS | Subscription, high retention, <5% capex/rev | ADBE, CRM, INTU |
| Capital-light fintech | Transaction-based, low capex | V, MA, PYPL |
| Capital-hungry manufacturing | High capex/revenue ratio, cyclical | CAT, DE, GE |
| Capital-hungry retail | Inventory-heavy, store footprint | WMT, TGT, HD |
| Leverage-dependent | Profits from interest spread | JPM, BAC, BRK |

---

## Dimension 2: Competitive Advantage & Moat (D2)

> Maps to QY Factor 1 Module 3. See `references/framework_guide.md` for detailed moat definitions.

Analysis:
- Market structure: [monopoly / oligopoly / monopolistic competition / perfect competition]

**Two-tier moat framework (layered analysis)**:

**Layer 1: Business Barriers (Non-Technical Moat)**
Evaluate each (present/absent, strong/moderate/weak):
- Scale economies | Network effects | Switching costs | Intangible assets (brand/patents/licenses) | Cost advantage

**Layer 2: Technical Barriers (Data & Algorithm Moat)**
Evaluate each (present/absent, strong/moderate/weak):
- Data asset barriers: Proprietary datasets, data flywheel
- Core algorithm/model barriers: Long-iterated systems (recommendation/search/pricing/risk control)
- Fulfillment/supply chain system barriers: Highly customized real-time systems
- AI/frontier technology investment: Proprietary closed-loop data advantage

> Note: Not all companies have technical moats. Traditional manufacturing/consumer goods may
> have an empty Layer 2. The framework accommodates "Layer 2 not applicable."

**Cross-layer interaction assessment**:
- Does the technical layer reinforce the business layer?
- Does the business layer feed back into the technical layer?
- If a closed-loop flywheel forms: Label "compound moat"
- Technical moat durability dependency: R&D spending ratio stability

Additional checks:
- Pricing power verification: Track record of price increases? Customer churn?
- Supply chain position: Bargaining power vs. upstream/downstream
- Moat erosion risk: Narrowing signs over past 5 years? Competitor attack vectors
- Competitive threat from AI/technology disruption

Output: `[WIDE / NARROW / NONE]`, durability assessment
  Note: Moat type = [Business] xxx + [Technical] xxx (if Layer 2 N/A, mark "not applicable")
  Note: Compound moat flywheel = [YES / NO]

---

## Dimension 3: External Environment (D3)

> Maps to QY Factor 1 Modules 5, 8. See `references/market_rules_us.md` for US-specific rules.

### D3-A: Cyclicality

Analysis:
- Revenue and profit volatility amplitude over past 1-2 full economic cycles (quantify as %)
- External variable dependency (commodity prices / interest rates / FX) and transmission mechanism
- If strong-cycle: Current position in cycle = [bottom / mid-cycle / top]

Output: `[strong-cycle / weak-cycle / non-cycle]`

### D3-B: Regulatory & Policy Risk

Analysis (US-adapted):
- Antitrust risk: FTC/DOJ scrutiny or active investigations
- Sector-specific regulation: FDA (pharma/biotech), FCC (telecom), EPA (energy), SEC (finance)
- Tax policy risk: Exposure to corporate tax rate changes, international tax reform (OECD Pillar Two)
- Trade/tariff risk: Supply chain exposure to tariffs, export controls, geopolitical tensions

Output: `[Favorable / Neutral / Negative]`

---

## Dimension 4: Management & Governance (D4)

> Maps to QY Factor 1 Module 7.

Analysis:
- Current core management (CEO/Chairman/CFO) tenure in years
- Whether major management changes occurred in the past 5 years

**Capital allocation track record** (annotate by management tenure):
- Destination of retained earnings: organic expansion / acquisitions / financial investments / debt repayment / idle
- Ex-post returns: Any large goodwill impairments / investment losses / failed projects?
- If management changed: Has predecessor's capital misallocation drag been cleared?

**Observable signals for current management** (only when management changed):
- Positive: Proactively wrote down impairments / increased dividends / initiated buybacks
- Negative: Continued investing in predecessor's failed projects
- Neutral: Initiated new acquisitions (needs observation)

**Related-party transaction check** (regardless of management era):
- Are there frequent related-party transactions? Is pricing arm's-length?

Output decision logic:

```
No management change -> Choose one: [Excellent / Adequate / Destroying value]
  Destroying value -> VETO

Management changed AND current tenure < 2 years:
  Predecessor poor + Current signals positive -> [Observation period, no veto yet]
  Predecessor poor + Current signals unclear or continuing predecessor's path -> VETO
  Predecessor's legacy not cleared, still dragging financials -> VETO

Management changed AND current tenure >= 2 years -> Judge based on current track record:
  Choose one: [Excellent / Adequate / Destroying value]
```

---

## Dimension 5: MD&A Interpretation (D5)

> Maps to QY Factor 1 Module 9.

**Instruction**: From `data_pack.md` §7/§8 or annual report MD&A, focus on:

**(1) Operating review & attribution**
- Management's self-explanation for revenue/profit changes
- Performance breakdown by business segment
- Is management's narrative consistent with independent financial data analysis?

**(2) Forward guidance reliability**
- Management's outlook for next 1-2 years (revenue growth targets, margin expectations, capex plans)
- Quantified guidance vs. directional only
- Historical guidance track record: past 2-3 years guidance vs. actuals — credibility assessment

**(3) Capital allocation intent**
- Latest dividend policy statements
- Buyback program progress and authorization remaining
- Major investment/acquisition plans or divestiture intentions
- Debt management strategy

**(4) Risk factor self-disclosure**
- Management's self-disclosed major risk factors
- Any newly added risk items (vs. prior year)?
- Are mitigation measures specific and actionable?

**(5) Cross-validation**
- Is MD&A narrative consistent with D2 (moat), D3 (cyclicality), D4 (capital allocation)?
- If contradictions: financial data takes precedence, flag "whitewashing" or "excessive pessimism"

Output:
```
MD&A credibility: [HIGH / MEDIUM / LOW]
Key findings: [<= 3 most important information points]
Consistency with independent analysis: [Consistent / Partial divergence / Major contradiction]
Impact on investment judgment: [Positive / Neutral / Negative]
```

---

## Dimension 6: Complex Structure Analysis (D6, Conditional)

> Maps to QY Factor 1 Module 10. Execute ONLY when trigger conditions are met.

**Trigger conditions**: Execute when the subject meets ANY of:
- Company holds significant equity stakes (>= 10%) in one or more publicly listed subsidiaries
- Company describes itself as "investment holding" or "diversified holding" in filings
- Market broadly classifies it as a holding company / diversified conglomerate

If the subject does not meet any of the above: note "D6: Not applicable (simple structure)" and skip.

### (1) SOTP (Sum-of-the-Parts) vs. Market Cap

```
Step 1: List all publicly listed subsidiaries / associates held by parent
Step 2: Parent-level net cash / net debt
Step 3: SOTP = Sum(Subsidiary stake values) + Parent net cash
Step 4: Holding discount = (SOTP - Parent Market Cap) / SOTP
Step 5: Implied value of parent's own business
```

### (2) Discount Decomposition Analysis

| Discount Factor | Reasonable Range | This Stock | Basis |
|:----------------|:----------------:|:----------:|:------|
| Liquidity discount | 5-10% | {value}% | Parent/sub daily volume ratio |
| Governance discount | 5-15% | {value}% | Related-party transactions, management alignment |
| Complexity discount | 5-10% | {value}% | Holding layers, cross-holdings |
| Information asymmetry discount | 3-5% | {value}% | Parent standalone disclosure quality |
| **Reasonable total discount** | **18-40%** | **{value}%** | — |

### (3) SOTP Sensitivity Analysis

Bull/Base/Bear case scenarios with subsidiary market cap adjustments (1.2x / 1.0x / 0.7x).

Output:
```
Holding structure: [Applicable / Not applicable]
SOTP: [X] $M (base case)
Parent market cap: [Y] $M
Holding discount: [Z]%
Implied own-business value: [W] $M
Holding type: [Pure holding / Hybrid / Primarily operating]
Reasonable discount estimate: [V]%
Excess discount: [Z-V] pct
Sensitivity: Bear case discount [X]%, bear implied own-business [X] $M
```

---

## Cross-Validation & Deep Analysis

> After completing D1-D6, step back and check internal consistency. This section catches
> contradictions between dimensions that individual analyses miss.

### CV-1: Number vs Narrative Consistency

Check each pair for contradictions:

| Pair | Check | Red Flag |
|------|-------|----------|
| D1 (profit quality) vs D5 (MD&A) | Does management's growth narrative match core operating profit trend? | Management claims "strong growth" but core profit is flat/declining after stripping non-recurring items |
| D2 (moat) vs D1 (revenue quality) | Does pricing power claim match gross margin trend? | "WIDE moat" but gross margins declining or unable to raise prices |
| D4 (capital allocation) vs D1 (profit quality) | Do acquisitions generate returns matching management claims? | Heavy M&A spending but core revenue growth excluding acquisitions is flat |
| D3 (regulatory) vs D5 (MD&A) | Does management adequately disclose regulatory risks? | Material regulatory changes underway but MD&A downplays impact |

### CV-2: Core Contradictions

List the **top 1-3 contradictions** found (if any). For each:
- State the contradiction clearly
- Which dimension's conclusion should take precedence and why
- Impact on overall quality grade (upgrade/downgrade/no change)

### CV-3: Overlooked Signals

Scan for signals that don't fit neatly into D1-D6 but matter:
- Auditor changes or qualified opinions in recent 3 years
- Unusual related-party transaction patterns
- Insider selling patterns diverging from stated confidence
- Off-balance-sheet arrangements flagged in footnotes
- Concentration risk: single customer >20% of revenue, single supplier >30% of COGS

Output:
```
Cross-validation result: [Consistent / Minor divergences / Material contradictions]
Core contradictions: [list or "None"]
Overlooked signals: [list or "None"]
Quality grade adjustment: [None / Upgrade by 1 / Downgrade by 1], reason: [one sentence]
```

---

## Summary Output

> This summary produces the structured output consumed by downstream strategy agents.
> See `references/output_schema.md` for the complete typed schema.

```
═══ QUALITATIVE ASSESSMENT SUMMARY ═══

D1 — Business Model & Capital:
  Capital intensity: [capital-light / capital-hungry]
  Payment pattern: [prepaid / subscription / post-delivery / advance-funded]
  Business model type: [classification]
  Revenue quality: Core revenue share [X]%, core growth [X]% vs headline [Y]%
  Profit quality: [HIGH / MODERATE / LOW], non-operational contribution [X]%
  Debt concern: [None / Flag with details]
  Profit source concern: [None / Flag with details]

D2 — Competitive Advantage & Moat:
  Moat rating: [WIDE / NARROW / NONE]
  Moat type: [Business] xxx + [Technical] xxx
  Compound flywheel: [YES / NO]
  Pricing power: [Strong / Moderate / Weak / None]

D3 — External Environment:
  Cyclicality: [strong-cycle / weak-cycle / non-cycle]
  Cycle position: [bottom / mid-cycle / top / N/A]
  Regulatory risk: [Favorable / Neutral / Negative]

D4 — Management & Governance:
  Management rating: [Excellent / Adequate / Destroying value / Observation]
  Capital allocation: [one sentence summary]

D5 — MD&A Interpretation:
  MD&A credibility: [HIGH / MEDIUM / LOW]
  Key findings: [<= 3 items]
  Impact: [Positive / Neutral / Negative]

D6 — Complex Structure:
  Holding structure: [Applicable / Not applicable]
  Holding discount: [X]% or N/A
  Excess discount: [X] pct or N/A

Calibration Decisions:
  Anchored profit metric: [metric name] = §3 [line item]
  Cash definition: [narrow / broad]
  Anomalies: [<= 3 items]

Cross-Validation:
  Consistency: [Consistent / Minor divergences / Material contradictions]
  Core contradictions: [list or "None"]
  Overlooked signals: [list or "None"]
  Quality grade adjustment: [None / Upgrade by 1 / Downgrade by 1]

Competitors: [list of "Name (TICKER)" from D2]
Industry keywords: [list of monitoring search terms from D3]

Overall Business Quality: [A / B / C / D]
  A = High quality (light-asset, wide moat, excellent management)
  B = Good quality (moderate capex, narrow moat, adequate management)
  C = Acceptable (capital-hungry but profitable, or narrow moat with risks)
  D = Poor quality (VETO recommended)

Qualitative Conclusion: [PASS / VETO (reason)]
═══════════════════════════════════════════
```

---

*Shared Qualitative Assessment v1.0 | Business Analysis Framework*
