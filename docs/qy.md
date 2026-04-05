# Quality Yield (QY) Strategy Workflow

## Overview

The Quality Yield strategy evaluates US equities through a 4-factor framework adapted from the [Turtle Investment Framework](https://github.com/terancejiang/Turtle_investment_framework). It identifies stocks with high penetration return rates (GG) backed by durable business quality.

**Key terms**:
- **GG (Penetration Return Rate / 穿透回报率)** — Measures actual cash returned to shareholders (dividends + buybacks) as a percentage of market cap, after all capital maintenance costs. Pass threshold: GG > Threshold II.
- **SBC (Stock-Based Compensation)** — Deducted from cash flows to reflect real dilution cost, a key US-market adaptation.

## Operating Modes

| Mode | Trigger | Action |
|------|---------|--------|
| **Analyze** | `/us-qy AAPL MSFT` | Run full 4-factor analysis on given tickers |
| **Update** | `/us-qy` (portfolio exists) | Re-analyze all current holdings |
| **Screen** | `/us-qy screen` (or empty portfolio) | Finviz screen → GG scan → analyze top candidates |

## Sector Limitations

**The QY model is structurally misleading for banks and financial institutions.** The GG formula relies on Operating Cash Flow (OCF) as the starting point for shareholder cash returns. For non-financial companies, OCF reflects operating cash generation. For banks and lending companies, OCF is dominated by loan origination and deposit flows — a growing bank will always show deeply negative OCF regardless of profitability.

| QY Assumption | Reality for Banks/Fintechs |
|---------------|---------------------------|
| OCF reflects operating cash generation | OCF is dominated by loan origination/deposit flows |
| Negative OCF = cash-burning business | Negative OCF = growing loan book (can be healthy) |
| Revenue and Operating Income are distinct | yfinance reports Revenue = Operating Income for financials |
| Debt/Equity of 1-3x is normal | Debt/Equity of 10-20x is structural (deposits are liabilities) |
| Capex represents maintenance spending | Capex is minimal; the "investment" is in loan origination |
| Fair value marks are immaterial | 90%+ of assets may be carried at fair value (subjective) |

**Guidance**: When QY flags a bank/fintech with negative GG, verify whether the failure is structural (banking model artifact) or fundamental (genuine inability to return cash). Key differentiators:

- **Structural**: Growing loan book consuming cash, but the bank has positive net interest margin, improving credit quality, and a viable path to shareholder returns
- **Fundamental**: Negative GG *plus* massive equity dilution, zero shareholder returns, aggressive fair value accounting, management self-dealing

Banks that pass QY tend to be mature, slow-growth institutions with stable dividends and buybacks (e.g., JPM, WFC). High-growth fintechs (e.g., SOFI, UPST) will almost always fail QY during their growth phase. Consider using the Cyclical strategy for banks at trough valuations, or standalone business analysis for growth-stage fintechs.

## US Market Parameters

| Parameter | Value |
|-----------|-------|
| Risk-free rate (Rf) | US 10Y Treasury (~4.3%) |
| Threshold II | max(5%, Rf + 3%) = 7.3% |
| Dividend tax rate | 15% (qualified) |
| Currency / Units | USD / Millions |
| Benchmark | S&P 500 (SPY) |

## Pipeline Architecture

```
Phase 1: Data Collection
  ├── Task 1:  yfinance/Bloomberg → data_pack.md
  ├── Task 1E: SEC EDGAR download → filing HTML + meta JSON    (parallel)
  │
Phase 2: Calculation & Extraction
  ├── Task 2:  GG Calculator → {T}_GG.md
  ├── Task 2A: EDGAR Parser → filing_sections.json             (parallel)
  ├── Task 2B: Footnote Extraction → data_pack_footnotes.md    (parallel)
  └── Task 2C: Factor Inputs → {T}_factor_inputs.md            (parallel)
  │
Phase 3: Analysis
  ├── Task 3-Pre: Preflight Validation → phase3_preflight.md
  ├── Task 3-A:   Agent A (Qualitative) → phase3_qualitative.md  ─┐
  ├── Task 3-B:   Agent B (Quantitative) → phase3_quantitative.md ─┤ parallel
  │               ← gate: F1 + F2 + F3 must all PASS →            ─┘
  └── Task 3-C:   Agent C (Valuation) → {T}_analysis_report.md
  │
Phase 4: Portfolio
  └── Task 4:  Portfolio Construction → US_PORTFOLIO.md
```

## 4-Factor Model

### Factor 1: Asset Quality & Business Model (Agent A)

**Purpose**: Qualitative assessment of business durability and balance sheet health.

| Component | What It Evaluates |
|-----------|-------------------|
| F1A Quick Screen | Audit opinion, auditor changes, fraud, business model clarity, insider flags |
| D1 Business Model | Capital intensity, revenue model, payment patterns |
| D2 Moat | WIDE / NARROW / NONE — network effects, switching costs, brand, cost advantages |
| D3 Cyclicality | Strong-cycle / weak-cycle / counter-cycle + cycle position |
| D4 Management | Capital allocation track record, incentive alignment |
| D5 MD&A Credibility | Forward guidance accuracy, narrative vs. financial reality |
| D6 Complex Structure | Holding companies, cross-subsidization, related parties |
| M6 Human Capital | Revenue per employee, key-person risk |
| M11-M13 Working Capital | Receivables, inventory, fixed asset quality |
| M14 Goodwill | Goodwill/Equity ratio, impairment risk |
| M15 SBC | SBC/NI ratio, dilution rate, buyback offset |

**Output**: Asset Quality Score (A/B/C/D/F) + PASS/FAIL/VETO

### Factor 2: Coarse Return Rate (Agent B)

**Purpose**: Top-down estimate of shareholder return capacity.

```
Owner Earnings (OE) = Net Income + D&A - Maintenance Capex
OE (SBC-adj) = OE - SBC

Coarse Return Rate R = [OE × Payout_Ratio × (1 - Tax) + Avg_Buybacks] / Market_Cap

Gate: R >= Rf (4.3%) to proceed, R >= Threshold II (7.3%) to PASS
```

### Factor 3: Refined Return Rate / GG (Agent B)

**Purpose**: Bottom-up cash flow analysis producing the penetration return rate.

```
Cash Surplus = OCF - Capex
AA = Surplus - SBC - Debt Change + Buybacks - Dividends

GG = [AA × Payout_Ratio × (1 - Tax) + Avg_Buybacks] / Market_Cap

Evaluated across: revenue sensitivity, lambda (operating leverage),
extrapolation credibility, distribution willingness
```

**Key assessments**:
- Revenue sensitivity: GG at 0.7x-1.0x revenue scenarios
- Lambda: OCF change per unit revenue change
- Extrapolation credibility: HIGH/MEDIUM/LOW across 5 dimensions
- Distribution willingness: Strong/Moderate/Weak

### Factor 4: Valuation & Safety Margin (Agent C)

**Purpose**: Determine if the stock price offers sufficient margin of safety.

| Step | What |
|------|------|
| 1. Threshold | GG vs Threshold II, safety margin calculation |
| 2. Value Trap Screen | 5 traps: cash flow deterioration, moat narrowing, industry decline, weak distribution, value-destroying management |
| 3. Position Sizing | Matrix of safety margin × credibility × trap risk → Standard/Reduced/Minimal |
| 4. Price Assessment | Target buy price, historical percentile, performance decline sensitivity |
| 5. Relative/Absolute | PE/PB percentile, sector comparison, 11 absolute indicators |
| 6. Floor Price | 5-method composite: net liquid assets, BVPS, 10yr low, dividend/buyback capitalization, pessimistic FCF |

## Output Files per Ticker

```
output/{TICKER}/
├── data_pack.md               # Raw financial data
├── data_pack_footnotes.md     # SEC filing footnote extracts
├── filing_sections.json       # Parsed EDGAR sections
├── {T}_filing_meta.json       # EDGAR filing metadata
├── {T}_10K.htm                # Raw SEC filing (form varies)
├── {T}_GG.md                  # GG calculator result
├── {T}_factor_inputs.md       # Pre-computed factor metrics
├── warnings.json              # Auto-detected anomalies
├── phase3_preflight.md        # Data validation & calibration
├── phase3_qualitative.md      # Factor 1 (Agent A)
├── phase3_quantitative.md     # Factors 2+3 (Agent B)
└── {T}_analysis_report.md     # Factor 4 + synthesis (Agent C)
```

## Checkpoint & Resume

Each task writes output before completing. Files < 24 hours old are reused:

| Existing File | Skips To |
|---------------|----------|
| `data_pack.md` | Task 2 (GG calc) |
| `{T}_GG.md` | Task 3-Preflight |
| `phase3_preflight.md` | Task 3-A/B |
| `phase3_qualitative.md` + `phase3_quantitative.md` | Task 3-C |
| `{T}_analysis_report.md` | Task 4 |

## Scripts

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `yfinance_collector.py` | Fetch financial data | `--ticker T --output path` |
| `bloomberg_collector.py` | Bloomberg data fetch | `--security "T US Equity"` |
| `edgar_downloader.py` | Download SEC filings | `--ticker T [--include-interim]` |
| `edgar_parser.py` | Parse filing HTML | `--input path --ticker T` |
| `calculate_qy_gg.py` | Calculate GG | `--input data_pack.md --code T` |
| `calculate_factor_inputs.py` | Pre-compute metrics | `--input data_pack.md --code T` |
| `finviz_screener.py` | Tier 1 screen | `--with-gg --top-n N` |
| `screen_pipeline.py` | Full Tier 1+2 pipeline | `--top-n N [--with-edgar] [--no-cache]` |
| `portfolio_manager.py` | Portfolio CRUD | (used by agents) |
| `qy_backtest.py` | Historical backtest | `--start DATE --end DATE --top-n N` |
| `qy_alerts.py` | Daily price alerts | (standalone) |
| `qy_scheduler.py` | Scheduled execution | (cron-driven) |

## Prompts

| File | Used By | Purpose |
|------|---------|---------|
| `prompts/qy/coordinator.md` | Orchestrator | Mode detection & task dispatch |
| `prompts/qy/phase2_footnotes.md` | Footnote agent | SEC filing extraction rules |
| `prompts/qy/phase3_preflight.md` | Preflight | Data validation & calibration |
| `prompts/qy/phase3_quantitative.md` | Agent B | F2+F3 analysis instructions |
| `prompts/qy/phase3_valuation.md` | Agent C | F4 valuation instructions |
| `prompts/qy/references/factor1_asset_quality.md` | Agent A | F1 rules |
| `prompts/qy/references/factor2_coarse_return.md` | Agent B | F2 rules |
| `prompts/qy/references/factor3_refined_return.md` | Agent B | F3 rules |
| `prompts/qy/references/factor4_valuation.md` | Agent C | F4 rules |
| `prompts/qy/references/factor_interface.md` | All agents | Parameter handoff spec |
| `prompts/shared/qualitative/qualitative_assessment.md` | Agent A | Shared D1-D6 framework |

## Scheduling

| Frequency | What | Budget |
|-----------|------|--------|
| Daily | Price alerts, threshold proximity | ~30 sec |
| Weekly | GG refresh for all holdings | ~5 min |
| Monthly | Full Finviz screen + discovery | ~30 min |

## Error Handling

- yfinance failure → skip ticker, continue with remaining
- GG calculation failure → report error, skip ticker
- Agent A fails, Agent B succeeds → run Agent C with degraded qualitative data
- Agent B fails → cannot run Agent C (quantitative required), skip ticker
- All tickers fail → report error, suggest checking network/API access
