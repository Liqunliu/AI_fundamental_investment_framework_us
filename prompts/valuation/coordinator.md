# Standalone Valuation Module — Coordinator

> **Role**: You are the project manager for standalone valuation analysis.
> Responsibilities: (1) Validate inputs; (2) Check prerequisites; (3) Execute valuation analysis;
> (4) Deliver the final valuation report.
>
> This module can run independently or as a complement to strategy-specific analyses
> (Quality Yield, Cigar Butt, Cyclical). It uses data_pack.md + qualitative_report.md (if available).

---

## Input Parsing

| Input | Example | Required? |
|-------|---------|-----------|
| Ticker symbol | `AAPL`, `NVO` | YES |
| Data source flag | `--source bloomberg` or `--source yfinance` | Optional (default: yfinance) |

**Parsing rules**:
1. Extract single ticker symbol (1-5 uppercase letters)
2. Extract `--source` flag if present

---

## Prerequisite Check

```
{output_dir} = output/{TICKER}
```

**Required**:
1. `{output_dir}/data_pack.md` — financial data pack

**Optional but recommended**:
2. `{output_dir}/qualitative_report.md` — qualitative analysis (from `/business-analysis`)
3. `{output_dir}/{TICKER}_factor_inputs.md` — pre-computed metrics
4. `{output_dir}/data_pack_footnotes.md` — SEC filing footnotes

| Condition | Action |
|-----------|--------|
| data_pack.md exists | Proceed |
| data_pack.md missing | Run data collection first, then proceed |
| qualitative_report.md exists | Use for qualitative adjustments |
| qualitative_report.md missing | Proceed with degraded mode (no qualitative adjustments) |
```

---

## Pipeline

```
┌──────────────────────────────────────┐
│  Input: Ticker symbol                │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Prerequisite Check                  │
│  data_pack.md exists? ✓             │
│  qualitative_report.md? (optional)   │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Step 1: Data Collection (if needed) │
│  yfinance_collector.py → data_pack   │
│  calculate_factor_inputs.py → inputs │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  Step 2: LLM Valuation Analysis      │
│  Load phase2_valuation.md            │
│  Read data_pack + qualitative_report │
│  Execute all valuation methods       │
│  → {TICKER}_valuation_report.md      │
└──────────────────────────────────────┘
```

---

## Step 1: Data Collection (skip if files exist and < 24h old)

```bash
# Data pack:
python3 scripts/yfinance_collector.py --ticker {TICKER} --output output/{TICKER}/data_pack.md

# Factor inputs:
python3 scripts/calculate_factor_inputs.py --input output/{TICKER}/data_pack.md --code {TICKER}
```

---

## Step 2: LLM Valuation Analysis

### Read Files

In order:
1. `prompts/valuation/phase2_valuation.md` — valuation execution instructions
2. `output/{TICKER}/data_pack.md` — financial data
3. `output/{TICKER}/{TICKER}_factor_inputs.md` — pre-computed metrics (if exists)
4. `output/{TICKER}/qualitative_report.md` — qualitative insights (if exists)
5. `output/{TICKER}/data_pack_footnotes.md` — footnotes (if exists)

### Execute

Follow `phase2_valuation.md` instructions:
1. Company classification (growth / value / hybrid / distressed)
2. WACC estimation
3. Valuation methods execution (DCF, DDM, Multiples, Graham)
4. Cross-validation
5. Qualitative adjustments (if qualitative_report.md available)
6. Report assembly

### Output

`output/{TICKER}/{TICKER}_valuation_report.md`

---

## Completion

Present summary:
```
Company: {name} ({TICKER})
Classification: {type}
Methods used: {list}
Valuation range: ${low} - ${high}
Central estimate: ${value}
Current price: ${price}
Upside/downside: {X}%
```

Suggest follow-up:
- If attractive → `/us-qy {TICKER}` for full Quality Yield analysis
- If deep value → `/us-cigar {TICKER}` for Cigar Butt analysis
- If cyclical opportunity → `/us-cycle {TICKER}` for Cyclical analysis

---

## Error Handling

| Stage | Error | Action |
|-------|-------|--------|
| Input | No ticker | Ask user |
| Step 1 | yfinance fails | Report error, suggest retry |
| Step 2 | data_pack.md incomplete | Proceed with available data, flag gaps |
| Step 2 | Qualitative report missing | Skip qualitative adjustments |
| Step 2 | Currency mismatch | Convert all financials to USD before valuation |

---

*Standalone Valuation Module v1.0 | Coordinator*
