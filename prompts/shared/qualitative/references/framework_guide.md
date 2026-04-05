# Moat Framework Guide

> Detailed definitions and classification criteria for the two-tier moat framework
> used in Dimension 2 (Competitive Advantage & Moat) of the qualitative assessment.

---

## Layer 1: Business Barriers (Non-Technical Moat)

### Scale Economies
- **Definition**: Unit costs decrease as production volume increases, creating a cost advantage
  that new entrants cannot match without equivalent scale.
- **Strong**: >30% cost advantage at current scale vs. new entrant breakeven
- **Moderate**: 10-30% cost advantage
- **Weak/Absent**: <10% cost advantage or scale does not meaningfully reduce costs
- **Examples**: WMT (distribution density), COST (buying power), UPS (route density)

### Network Effects
- **Definition**: Product/service value increases as more users join, creating a self-reinforcing cycle.
- **Direct**: Same-side network effects (more users = more value for each user)
- **Indirect**: Cross-side effects (more buyers attract more sellers, and vice versa)
- **Strong**: Dominant market share with >50% of network value, high switching costs
- **Moderate**: Significant but not dominant, or network effects limited to specific segments
- **Weak/Absent**: No meaningful network benefit
- **Examples**: META (social graph), V/MA (merchant-cardholder two-sided), MSFT (enterprise ecosystem)

### Switching Costs
- **Definition**: Costs (financial, time, data migration, retraining) incurred by customers to change providers.
- **Strong**: Multi-year contracts, deep workflow integration, data lock-in, regulatory burden
- **Moderate**: Moderate integration, some data portability, retraining costs
- **Weak/Absent**: Easy to switch, standardized interfaces, minimal integration
- **Examples**: ORCL (database migration), ADBE (Creative Suite workflow), INTU (QuickBooks data)

### Intangible Assets
- **Brands**: Consumer trust, pricing premium, decades of investment
- **Patents**: Legal barriers to competition, typical 20-year life
- **Licenses/Permits**: Regulatory barriers (banking charters, spectrum licenses, FDA approvals)
- **Strong**: Brand commands >20% pricing premium, or patent portfolio blocks key competitors
- **Moderate**: Recognized brand with moderate premium, or narrow patent protection
- **Weak/Absent**: Commodity perception, expired/weak IP
- **Examples**: AAPL (brand premium), PFE (drug patents), JPM (banking charter)

### Cost Advantage
- **Definition**: Structural cost advantage not dependent on scale alone.
- **Process-based**: Proprietary processes, superior logistics, vertical integration
- **Resource-based**: Exclusive access to low-cost inputs, favorable locations
- **Strong**: >15% structural cost advantage vs. median competitor
- **Moderate**: 5-15% structural cost advantage
- **Weak/Absent**: No meaningful structural advantage
- **Examples**: COST (low-margin model + membership), SHW (store density + distribution)

---

## Layer 2: Technical Barriers (Data & Algorithm Moat)

### Data Asset Barriers
- **Definition**: Proprietary datasets that are difficult to replicate, forming a positive feedback loop.
- **Data Flywheel**: More users -> more data -> better product -> more users
- **Evaluation**: Volume, uniqueness, refresh rate, defensibility
- **Strong**: Proprietary closed-loop data, competitors cannot replicate within 3+ years
- **Moderate**: Significant data advantage, but partially replicable (2-3 year gap)
- **Weak/Absent**: Data is publicly available or easily collected
- **Examples**: GOOGL (search query data), AMZN (purchase + browsing data), SNOW (data sharing network)

### Core Algorithm/Model Barriers
- **Definition**: Long-iterated systems where replication + tuning takes >= 2 years even with equivalent data.
- **Domains**: Recommendation, search ranking, pricing optimization, risk control, fraud detection
- **Strong**: >5 years of iteration, significant accuracy advantage over competitors
- **Moderate**: 2-5 years of iteration, measurable but narrowing advantage
- **Weak/Absent**: Standard algorithms, easily replicated with available tools
- **Examples**: GOOGL (search ranking), NFLX (recommendation), SQ (risk modeling)

### Fulfillment/Supply Chain System Barriers
- **Definition**: Highly customized real-time systems proven under extreme scenarios.
- **Evaluation**: Custom-built vs. off-the-shelf, extreme scenario performance, rebuild cost
- **Strong**: Proprietary system with 5+ years development, proven at extreme scale
- **Moderate**: Significant customization, but core components available commercially
- **Weak/Absent**: Uses commodity logistics/fulfillment systems
- **Examples**: AMZN (fulfillment network), UPS (ORION routing), FDX (COSMOS)

### AI/Frontier Technology Investment
- **Definition**: AI capabilities trained on proprietary closed-loop business data.
- **Evaluation**: Proprietary training data quality, first-mover advantage durability
- **Strong**: Proprietary training data unavailable to competitors, deployed at scale
- **Moderate**: AI investment with some proprietary data, but competitors catching up
- **Weak/Absent**: Using publicly available AI tools, no proprietary training data
- **Examples**: TSLA (FSD driving data), GOOGL (search + assistant), META (social graph AI)

---

## Cross-Layer Interaction: Compound Moat Assessment

A **compound moat** exists when Layer 1 and Layer 2 create a self-reinforcing flywheel:

```
Layer 1 → Layer 2 reinforcement:
  Scale economies → More data → Stronger algorithms
  Network effects → Richer user data → Better personalization
  Switching costs → Longer user history → More training data

Layer 2 → Layer 1 reinforcement:
  Better algorithms → Superior product → Stronger network effects
  Data flywheel → Lower unit costs → Scale advantage
  AI capabilities → Higher switching costs (personalization lock-in)
```

**Compound moat scoring**:
- **YES**: Clear bidirectional reinforcement between at least one Layer 1 and one Layer 2 barrier
- **NO**: Barriers exist independently without meaningful cross-layer reinforcement

---

## Moat Rating Decision Rules

| Condition | Rating |
|-----------|--------|
| >= 2 Layer 1 barriers rated "Strong" + compound flywheel | **WIDE** |
| >= 2 Layer 1 barriers rated "Strong" (no compound) | **WIDE** |
| 1 Layer 1 barrier "Strong" + compound flywheel | **WIDE** |
| 1 Layer 1 barrier "Strong" OR >= 2 "Moderate" | **NARROW** |
| Only "Moderate" or "Weak" barriers, no compound flywheel | **NARROW** |
| No barriers rated "Moderate" or above | **NONE** |

**Override rules**:
- If pricing power is "None" despite barrier ratings → Downgrade by one level
- If moat erosion is actively occurring (measurable market share loss) → Downgrade by one level
- If management is "Destroying value" → Flag as moat at risk regardless of rating

---

*Shared Qualitative Assessment v1.0 | Moat Framework Guide*
