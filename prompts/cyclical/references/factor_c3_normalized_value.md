# Factor C3: Normalized Valuation & Entry

> Uses mid-cycle (normalized) cash flows instead of TTM to value cyclical
> stocks fairly regardless of where they are in the cycle.

---

## Normalized GG Formula

```
Normalized_AA = Median(5yr OCF) - Median(5yr CapEx)
              + Avg(3yr Buybacks) - Avg(3yr Dividends) - Avg(3yr SBC)

Normalized_GG = Normalized_AA / Current_Market_Cap × 100
```

### Why Median Instead of Average?

- **Median** is robust to outlier years (a single boom or bust year won't
  distort the result).
- OCF and CapEx can swing wildly in cyclical industries. Median captures
  the "normal" operating level.
- Uses 5-year window for OCF/CapEx (captures at least one mini-cycle).
- Uses 3-year window for shareholder returns (more stable, policy-driven).

### SBC Adjustment

Same as US QY: SBC is subtracted because it dilutes shareholders.
Use the 3-year average to smooth any one-time equity grants.

---

## Entry Signal Requirements

**ALL four must be met** for a BUY signal:

| # | Requirement | Threshold |
|---|-------------|-----------|
| 1 | C1 Survival Gate | PASS |
| 2 | C2 Cycle Phase | Phase 1 (Deep Trough) or Phase 2 (Early Recovery) |
| 3 | Normalized GG | >= 7.30% (Threshold II) |
| 4 | Discount to Mid-Cycle | >= 15% below mid-cycle price |

### Discount to Mid-Cycle Calculation

```
Mid-Cycle Price Estimate:
  Mid_Cycle_EPS = Median(5yr EPS)    [or Median(5yr Net Income) / Current Shares]
  Mid_Cycle_PE  = Median(5yr PE)     [or sector average PE]
  Mid_Cycle_Price = Mid_Cycle_EPS × Mid_Cycle_PE

Discount = 1 - (Current_Price / Mid_Cycle_Price)
```

If Mid_Cycle_Price cannot be computed (missing data), use:
```
Alternative: Current price percentile in 5yr range <= 35%
```

---

## Position Sizing

Position size depends on the cycle phase and normalized GG quality.

### Phase 1: Deep Trough (Score >= 0.80)

| Tier | Normalized GG | Position % of Max |
|------|---------------|-------------------|
| Tier A | >= 3× Threshold (21.9%+) | 100% of max allocation |
| Tier B | >= 2× Threshold (14.6%+) | 80% of max allocation |
| Tier C | >= 1× Threshold (7.3%+) | 60% of max allocation |

### Phase 2: Early Recovery (Score 0.65-0.80)

| Tier | Normalized GG | Position % of Max |
|------|---------------|-------------------|
| Tier A | >= 3× Threshold | 70% of max allocation |
| Tier B | >= 2× Threshold | 50% of max allocation |
| Tier C | >= 1× Threshold | 35% of max allocation |

### Max Allocation

Max single position = **15%** of portfolio (vs QY's 25%).
This is lower because cyclical stocks carry higher inherent risk.

### Example

```
Max allocation = 15%
Phase 1, Tier B (GG = 16.5%):
  Position = 15% × 0.80 = 12.0% of portfolio
```

---

## Comparison: TTM GG vs Normalized GG

Always compute both and present side by side:

```
| Method | GG | vs Threshold | Status |
|--------|-----|-------------|--------|
| TTM GG (QY) | X.XX% | ±X.XX pct | PASS/FAIL |
| Normalized GG (Cyclical) | X.XX% | ±X.XX pct | PASS/FAIL |
| Gap (Normalized - TTM) | X.XX pct | — | [Cyclical premium / No premium] |
```

### Interpretation

| Gap | Meaning |
|-----|---------|
| > +5 pct | Stock is deeply cyclical and currently at trough |
| +2 to +5 pct | Moderately cyclical, trough impact visible |
| 0 to +2 pct | Mildly cyclical or near mid-cycle |
| < 0 pct | Stock may be at peak — TTM overstates earning power |

---

## Risk Management Rules

### Portfolio-Level Constraints

| Rule | Limit |
|------|-------|
| Max single position | 15% |
| Max sector exposure | 35% |
| Max same-commodity group | 30% |
| Min cash reserve | 20% |
| Portfolio stop-loss | -25% from peak triggers full review |

### Same-Commodity Groups

| Group | Examples |
|-------|---------|
| Oil & Gas | PBR, XOM, CVX, COP, OXY |
| Shipping | FRO, TRMD, HAFN, STNG |
| Semiconductors | QCOM, MU, AMAT, LRCX |
| Mining / Metals | FCX, VALE, BHP, RIO |
| Steel | X, NUE, CLF, STLD |
| Industrials | CAT, DE, CMI |

### Position Reduction Triggers

Reduce position when **any** of these occur:
1. Phase upgrades from 1/2 to 3 (Mid-Cycle) → reduce to 50% of position
2. Phase upgrades to 4 (Late Cycle) → reduce to 25% of position
3. Phase reaches 5 (Peak) → close position entirely
4. Portfolio stop-loss hit → review all positions
5. Company-specific negative event (fraud, covenant breach, etc.)

---

## Output Format

```
Factor C3 Normalized Valuation & Entry

Normalized GG: X.XX%
TTM GG (QY): X.XX%
Cyclical Premium: +X.XX pct

Entry Signal Check:
  ✓/✗ C1 Survival: PASS
  ✓/✗ C2 Phase: X — [Name] (Score X.XXXX)
  ✓/✗ Normalized GG >= 7.30%: X.XX%
  ✓/✗ Discount to Mid-Cycle >= 15%: XX.X%

Entry Decision: [BUY / HOLD / WAIT / AVOID]

Position Sizing:
  Phase: X
  GG Tier: [A/B/C]
  Max Allocation: 15%
  Recommended Position: XX.X%

Risk Limits Check:
  Single position: XX.X% [<= 15%: OK]
  Sector exposure: XX.X% [<= 35%: OK]
  Commodity group: XX.X% [<= 30%: OK]
  Cash reserve: XX.X% [>= 20%: OK]
```

---

*Cyclical Trough Strategy v1.0 | Factor C3 — Normalized Valuation & Entry*
