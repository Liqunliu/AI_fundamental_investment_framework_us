# Plan: Medium Priority Enhancements — Warnings + Cache + Two-Tier Screener

## Context

**Pre-requisite fix**: The existing EDGAR pipeline hardcodes `{T}_10K.html` filenames, but ADR stocks (BABA, PDD, TSM, etc.) file on form **20-F** — producing `{T}_20F.htm` instead. The MDA parser patterns also only match 10-K's "Item 7", not 20-F's "Item 5". This must be fixed before building the screening pipeline.

Three medium-priority items from `docs/TODO.md` (#3, #4, #5) address operational pain points:

1. **Structured Warnings** (#5): The existing `_section_12_risk_warnings()` in `yfinance_collector.py` (lines 596-675) generates ad-hoc markdown warnings that aren't machine-parseable. The preflight agent can't programmatically consume them. We need a typed JSON schema.

2. **Caching Layer** (#4): Every collector run re-fetches all data from scratch. yfinance rate-limits aggressively after ~50 tickers in screening workflows. `qy_backtest.py` already has an in-memory cache pattern (`_PRICE_CACHE`, `_FINANCIAL_CACHE` at line 315-316) but it's session-only. We need persistent disk cache with TTL.

3. **Two-Tier Screener** (#3): `finviz_screener.py` already has Tier 1 (Finviz) → Tier 1.5 (quick GG), but the "Tier 2" is just a CSV shortlist — it doesn't run full data collection + GG calculation. We need a pipeline that automatically runs `yfinance_collector.py` + `calculate_qy_gg.py` + `calculate_factor_inputs.py` for shortlisted tickers.

**Implementation order**: E5 → E4 → E3 (each builds on the previous).

---

## Step 0: Fix EDGAR Pipeline for ADR / 20-F Filings

### Problem

| Issue | Location | Impact |
|-------|----------|--------|
| Hardcoded `{T}_10K.html` filename | `coordinator.md` (lines 106, 114-115, 220), `skill.md` (lines 45, 56, 146) | ADR stocks produce `{T}_20F.htm` — coordinator can't find the file |
| MDA patterns only match "Item 7" | `edgar_parser.py` line 99 | 20-F uses "Item 5: Operating and Financial Review" — MDA extraction fails |

### Fix 1: Use `filing_meta.json` for dynamic filename resolution

Instead of hardcoding `{T}_10K.html`, the coordinator/skill/pipeline should:
1. Read `{T}_filing_meta.json` (already saved by `edgar_downloader.py`)
2. Derive the filename from `form_type` + `primary_document` extension

**Changes**:
- `coordinator.md`: Replace `{T}_10K.html` with dynamic pattern: "find the filing HTML via `{T}_filing_meta.json` → construct path from form_type"
- `skill.md`: Same dynamic pattern
- `screen_pipeline.py` (new, E3): Will use `filing_meta.json` directly to find the HTML file

### Fix 2: Add 20-F MDA patterns to `edgar_parser.py`

In `SECTION_DEFS` MDA entry (line 97-101), add 20-F patterns:

```python
(
    "MDA",
    "Management's Discussion & Analysis",
    [r"management.s\s+discussion", r"item\s+7[^a]", r"item\s*7\.",
     r"item\s+5[^a]", r"operating\s+and\s+financial\s+review"],  # 20-F
    False,
),
```

---

## Enhancement 5: Structured Warnings Auto-Detection

### New File: `scripts/warning_schema.py` (~80 lines)

Warning type definitions and detection logic. Consolidates into one file since the schema is simple.

```python
@dataclass
class Warning:
    type: str          # "data-missing", "audit-risk", "goodwill-high", etc.
    category: str      # "Data Gap", "Solvency", "Anomaly", "Cash Flow", "Asset Quality"
    severity: str      # "HIGH", "MEDIUM", "LOW"
    message: str       # Human-readable description
    metadata: dict     # Structured data (e.g., {"years": [2023, 2024], "field": "equity"})

def to_dict(self) -> dict: ...
```

**6 warning types** (matching Chinese reference):

| Type | Severity | Trigger | Detection Source |
|------|----------|---------|-----------------|
| `data-missing` | HIGH | Critical financial data absent | `_income`/`_balance`/`_cashflow` emptiness |
| `audit-risk` | HIGH | Negative equity, qualified audit | Balance sheet equity < 0 |
| `goodwill-high` | MEDIUM | Goodwill > 50% of equity | Balance sheet fields |
| `cash-quality` | MEDIUM | OCF < Net Income for 3+ years | Income + cashflow comparison |
| `anomaly` | MEDIUM | Revenue/NI change > 100% YoY | Income statement YoY |
| `concentration-risk` | LOW | Revenue concentration signals | Info dict segment data |

**Key function**: `detect_warnings(income_df, balance_df, cashflow_df, info_dict) -> List[Warning]`

### Modify: `scripts/yfinance_collector.py`

- Import `warning_schema.detect_warnings`
- In `_section_12_risk_warnings()`: call `detect_warnings()`, render result as both:
  - Existing markdown table in §12 (backward compatible)
  - New `warnings.json` file alongside `data_pack.md`
- Add `_save_warnings_json(warnings, output_dir)` method (~10 lines)

### Modify: `prompts/qy/phase3_preflight.md`

- Add `warnings.json` to Input Files table (non-blocking)
- Add rule: "If any HIGH severity warning exists, flag in dispatch notes"

### Modify: `scripts/bloomberg_collector.py`

- Same pattern: import `detect_warnings()`, call in risk warnings section, save `warnings.json`

---

## Enhancement 4: Caching Layer for Data Collection

### New File: `scripts/cache.py` (~200 lines)

TTL-based disk cache using JSON files in `output/.cache/`.

```python
class DataCache:
    def __init__(self, cache_dir: str = "output/.cache"):
        self.cache_dir = Path(cache_dir)

    def get(self, ticker: str, data_type: str) -> Optional[Any]:
        """Return cached data if fresh, None if stale/missing."""

    def put(self, ticker: str, data_type: str, data: Any) -> None:
        """Store data with timestamp."""

    def invalidate(self, ticker: str, data_type: str = None) -> None:
        """Remove cached data for a ticker (optionally specific type)."""

    def stats(self) -> dict:
        """Return cache hit/miss stats for current session."""
```

**Cache key format**: `output/.cache/{TICKER}/{data_type}.json`

**TTL configuration** (added to `scripts/config.py` `USMarketConfig`):

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| `financials` | 7 days | Quarterly statements don't change often |
| `info` | 7 days | Company profile data is stable |
| `prices` | 1 day | Market data changes daily |
| `history` | 1 day | Historical prices update daily |

**DataFrame serialization**: Reuse the pattern from `qy_backtest.py` — `{"index": [...], "columns": [...], "data": [...]}` for DataFrames, plain JSON for dicts.

**Config additions** to `scripts/config.py`:

```python
# Cache TTLs (seconds)
cache_ttl_financials: int = 7 * 86400   # 7 days
cache_ttl_info: int = 7 * 86400         # 7 days
cache_ttl_prices: int = 86400           # 1 day
cache_ttl_history: int = 86400          # 1 day
```

### Modify: `scripts/yfinance_collector.py`

Wrap the 3 data-fetching methods with cache:

- `_get_info()` (line 100): check cache → hit? return → miss? fetch, store, return
- `_get_financials()` (line 110): cache each of income/balance/cashflow separately
- `_get_history()` (line 135): cache price history

Add `--no-cache` CLI flag to force fresh fetch.

**Integration pattern** (minimal change to existing methods):

```python
def _get_info(self) -> dict:
    if self._info is None:
        if self.cache and not self.no_cache:
            cached = self.cache.get(self.symbol, "info")
            if cached is not None:
                self._info = cached
                return self._info
        # ... existing fetch logic ...
        if self.cache:
            self.cache.put(self.symbol, "info", self._info)
    return self._info
```

### Modify: `scripts/finviz_screener.py`

- In `_fetch_gg_for_ticker()` (line 352): use cache for `yf.Ticker(ticker).info` and `.cashflow` lookups
- This is the biggest rate-limiting bottleneck (50+ sequential yfinance calls)

---

## Enhancement 3: Two-Tier Screener Pipeline

### New File: `scripts/screen_pipeline.py` (~300 lines)

Orchestrates the full pipeline: Tier 1 (Finviz) → Tier 1.5 (quick GG) → Tier 2 (deep analysis).

```python
def run_pipeline(
    top_n: int = 10,
    skip_tier1: bool = False,     # Resume from existing tier2_shortlist.csv
    with_edgar: bool = True,      # Include EDGAR footnotes
    no_cache: bool = False,
    output_dir: str = "output/screen/"
) -> dict:
    """
    Full screening pipeline:
    1. Run finviz_screener.py --with-gg --top-n {top_n}  (if not skip_tier1)
    2. For each ticker in shortlist:
       a. yfinance_collector.py → data_pack.md
       b. calculate_qy_gg.py → {T}_GG.md
       c. calculate_factor_inputs.py → {T}_factor_inputs.md
       d. (optional) edgar_downloader.py + edgar_parser.py → filing_sections.json
    3. Rank by full GG, output final_candidates.csv + summary.md
    """
```

**Key design decisions**:
- Uses `subprocess.run()` to invoke existing scripts (avoids import coupling)
- Each ticker's output goes to standard `output/{TICKER}/` directory
- Cache layer (E4) handles rate limiting automatically
- Checkpoint after each ticker: `output/screen/pipeline_checkpoint.json` tracks completed tickers
- Resume capability: if checkpoint exists, skip already-processed tickers

**Pipeline steps per ticker**:

| Step | Script | Output | Time (cached) |
|------|--------|--------|---------------|
| Data collection | `yfinance_collector.py` | `data_pack.md` | ~5s cached / ~15s fresh |
| GG calculation | `calculate_qy_gg.py` | `{T}_GG.md` | <1s |
| Factor inputs | `calculate_factor_inputs.py` | `{T}_factor_inputs.md` | <1s |
| EDGAR download | `edgar_downloader.py` | `{T}_10K.html` or `{T}_20F.htm` | ~3s |
| EDGAR parse | `edgar_parser.py` | `filing_sections.json` | ~2s |

**Final output**: `output/screen/final_candidates.csv` with columns:
`ticker, name, sector, market_cap, quick_gg, full_gg, gg_vs_threshold, pe, pb, fcf_yield, shareholder_yield, warnings_count, warnings_high`

### Modify: `scripts/config.py`

Add pipeline settings:

```python
# Pipeline settings
pipeline_top_n: int = 10
pipeline_with_edgar: bool = True
pipeline_parallel_tickers: int = 1  # Sequential for rate limiting
```

### Modify: `prompts/qy/coordinator.md`

Update Mode 3 (Screening) to reference `screen_pipeline.py`:

```
Mode 3: python3 scripts/screen_pipeline.py --top-n 10 --with-edgar
```

### Modify: `.claude/skills/us-qy/skill.md`

Add screening pipeline command block in the Commands section.

---

## Files Summary

### New Files (3)

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/warning_schema.py` | ~80 | Warning types + `detect_warnings()` |
| `scripts/cache.py` | ~200 | TTL disk cache with DataFrame serialization |
| `scripts/screen_pipeline.py` | ~300 | Full Tier 1→2 screening orchestrator |

### Modified Files (8)

| File | Changes |
|------|---------|
| `scripts/edgar_parser.py` | Add 20-F MDA patterns ("Item 5", "Operating and Financial Review") |
| `scripts/yfinance_collector.py` | Import warnings, refactor §12, add `--no-cache`, cache integration |
| `scripts/bloomberg_collector.py` | Import warnings, save `warnings.json` |
| `scripts/finviz_screener.py` | Cache integration in `_fetch_gg_for_ticker()` |
| `scripts/config.py` | Add cache TTLs, pipeline settings |
| `prompts/qy/phase3_preflight.md` | Add `warnings.json` input |
| `prompts/qy/coordinator.md` | Dynamic filing filename via `filing_meta.json`, update Mode 3 |
| `.claude/skills/us-qy/skill.md` | Dynamic filing filename, add pipeline command |

---

## Implementation Order

| Step | Enhancement | Est. Lines | Dependencies |
|------|-------------|-----------|--------------|
| 0a | Fix: Add 20-F patterns to `edgar_parser.py` | ~5 changed | None |
| 0b | Fix: Dynamic filename in `coordinator.md` + `skill.md` | ~20 changed | None |
| 1 | E5: `warning_schema.py` | ~80 | None |
| 2 | E5: Patch `yfinance_collector.py` §12 | ~30 changed | Step 1 |
| 3 | E5: Patch `bloomberg_collector.py` | ~20 changed | Step 1 |
| 4 | E5: Patch `phase3_preflight.md` | ~10 changed | Step 1 |
| 5 | E4: `cache.py` | ~200 | None |
| 6 | E4: Add config TTLs | ~10 | Step 5 |
| 7 | E4: Integrate cache into `yfinance_collector.py` | ~40 changed | Steps 5-6 |
| 8 | E4: Integrate cache into `finviz_screener.py` | ~20 changed | Steps 5-6 |
| 9 | E3: `screen_pipeline.py` | ~300 | Steps 5-8 (cache) |
| 10 | E3: Update coordinator + skill (Mode 3) | ~30 changed | Step 9 |

---

## Verification

1. **20-F fix**: Run `edgar_parser.py` against a 20-F filing (e.g. BABA) — MDA section should be found
2. **Warning schema**: Run `yfinance_collector.py --ticker AAPL`, verify `output/AAPL/warnings.json` exists with typed entries
3. **Cache**: Run collector twice for same ticker — second run should show "cache hit" messages and complete in <3s
4. **Cache --no-cache**: Run with `--no-cache` flag — should re-fetch everything
5. **Pipeline**: Run `python3 scripts/screen_pipeline.py --top-n 3` — should produce `output/screen/final_candidates.csv` with 3 fully-analyzed tickers
6. **Pipeline resume**: Kill mid-run, re-run — should skip completed tickers via checkpoint
7. **ADR end-to-end**: Run pipeline with an ADR ticker (e.g. BABA) — should correctly download 20-F, parse it, and find MDA via Item 5
