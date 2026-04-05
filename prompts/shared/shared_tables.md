# Shared Lookup Tables — Canonical Constants

> Single source of truth for payout rules, tax rates, thresholds, veto gates,
> and the GG formula. All factor references point here.

---

## §T1: Payout Ratio Anchor Decision Tree

| # | Condition | Anchor |
|---|-----------|--------|
| 1 | Company has a committed/stated dividend policy | Use committed payout ratio |
| 2 | No commitment but stable history | Use 3-year trailing average (M) |
| 3 | No commitment and volatile history | Use 3-year trailing average (M) with caution |

Source: manually calculated from §5 dividends paid / §3 net income.
**Do NOT use the yfinance `payoutRatio` field.**

---

## §T2: Dividend Tax Rate

| Market | Rate | Condition |
|--------|------|-----------|
| US | **Q = 15%** | Qualified dividends, long-term holding |

---

## §T3: Threshold Formula

```
Rf = data_pack §13 (US 10-Year Treasury, default 4.30%)

Threshold II = max(5%, Rf + 3%)
  Current: max(5%, 4.30% + 3%) = 7.30%
```

---

## §T4: Veto Gate Tiers (Coarse Return)

| Tier | Condition | Action |
|------|-----------|--------|
| ① | R < Rf | IMMEDIATE VETO — can't beat risk-free rate |
| ② | Rf ≤ R < Threshold_II × 0.5 | IMMEDIATE VETO — gap too large for F3 corrections |
| ③ | Threshold_II × 0.5 ≤ R < Threshold_II | Marginal — proceed to Factor 3 |
| ④ | R ≥ Threshold_II | NORMAL PASS |

---

## §T5: GG Formula Template

```
GG = [AA × M × (1 − Q) + O] / Market_Cap × 100

Where:
  AA      = Real disposable cash surplus baseline ($M)
  M       = Payout ratio anchor (§T1)
  Q       = Dividend tax rate (§T2, US: 15%)
  O       = Average annual cancellation-type buybacks ($M, 3-year)
  Market_Cap = Current market capitalisation ($M)
```

Sensitivity variant (Factor 4):
```
Return_scenario = (AA_new × M × (1 − Q) + O) / Market_Cap × 100
Threshold_price = (AA_new × M × (1 − Q) + O) / (II% × Total_Shares)
```

---

*US Equity Quality Yield Strategy v2.0 | Shared Lookup Tables*
