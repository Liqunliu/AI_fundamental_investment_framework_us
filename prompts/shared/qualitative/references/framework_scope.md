# Framework Applicability & Limitations

> This document declares the scope, known limitations, and scenarios requiring human review
> for the qualitative analysis framework. Analysis agents should proactively flag these
> scenarios rather than attempt to auto-correct.

---

## 1. Best-Fit Company Profiles

- Single core business or primary segment contributing > 70% of revenue
- Clear, describable business model (can be summarized in one sentence)
- At least 5 years of continuous, comparable financial data
- Relatively stable competitive landscape with identifiable peers

## 2. Scenarios Where Framework Effectiveness Degrades

| Scenario | Why It Degrades | Recommended Approach |
|----------|----------------|---------------------|
| **Large diversified conglomerates** (revenue from > 3 unrelated industries) | High heterogeneity; difficult to simultaneously analyze multiple industry dynamics | Flag "High-heterogeneity company", provide per-segment confidence levels, mark overall conclusion as directional only |
| **Investment-income-dependent** (investment income / pre-tax profit > 30%) | P/E depressed by non-operating income; P/B may be distorted by fair-value accounting | Flag P/E and P/B distortion risk; suggest stripping investment income to compute core P/E, or use SOTP |
| **Holding-platform companies** (multiple listed subsidiaries) | Consolidated financials mask subsidiary-level value distribution | Trigger D6 SOTP analysis, but flag that SOTP precision is limited by subsidiary disclosure quality |
| **Transitional companies** (business model undergoing major change) | Historical data extrapolation unreliable | Flag "Transitional company — historical data of limited reference value"; reduce weight on quantitative analysis |
| **< 3 years of financial data** (recent IPO / SPAC / reverse merger) | Trend analysis unreliable | Downgrade flag; shorten comparable period |
| **Strong-cycle peak or trough** | Current earnings do not represent normalized levels | Pair with D3 cycle assessment + normalized earnings estimate |

## 3. Judgments Requiring Human Review

The following assessments can be initiated by the framework but should be verified by the investor:

1. **Moat sustainability**: Framework judges from historical data, but non-linear disruptions (technology shifts, regulatory changes, new entrants) require human judgment
2. **Management integrity**: Framework can only analyze signals in public disclosures; internal governance failures are often invisible in filings until they surface
3. **SOTP valuation precision**: Non-listed subsidiary valuations depend heavily on assumptions
4. **Investment income sustainability**: JV/associate dividend capacity depends on their own operations, requiring case-by-case analysis
5. **Accounting policy impact**: Choices like equity method vs. fair value, capitalization vs. expensing — their effect on reported profit and book equity requires professional judgment

## 4. When NOT to Rely Solely on This Framework

- More than 50% of profit comes from investment income or fair-value changes
- Company operates in 4+ unrelated industries
- Company is undergoing major M&A, spin-off, or asset restructuring
- Complete management turnover in the past 2 years

In these cases, the framework's output should serve only as a **starting point** for deeper human analysis, not as a conclusion.

---

*Framework Scope Declaration v1.0*
