# US Quality Yield Framework — TODO

## Low Priority (Nice to Have)

### 6. Data Pack Splitter for Parallel Agents
- **Current**: Each parallel agent reads the full `data_pack.md` (can be 8-15KB)
- **Target**: `split_data_pack.py` that partitions data pack into agent-specific slices (Agent A gets §1/§4/§7/§8/§12, Agent B gets §3/§4/§5/§14/§15)
- **Chinese reference**: `split_data_pack.py` with per-agent section routing
- **Why**: Reduces context window usage per agent, speeds up agent startup
- **Notes**: Low priority because current data packs are small enough that full reads don't cause issues; would matter more with Bloomberg's larger data packs

### 7. Shared Tables Consolidation
- **Current**: Payout ratio rules, dividend tax rates, threshold formulas are embedded inline in factor reference files (`factor2_coarse_return.md`, `factor3_refined_return.md`, `factor4_valuation.md`)
- **Target**: Single `prompts/shared/shared_tables.md` with unified lookup tables
- **Chinese reference**: `shared_tables.md` — payout ratio decision tree, dividend tax matrix (8 jurisdictions), threshold formula variants
- **Why**: Prevents inconsistencies when rules are duplicated across files; single source of truth for numerical parameters
- **Notes**: US framework only has 1 jurisdiction (15% qualified dividend tax) so the tax matrix is trivial; main value is payout ratio rules consolidation

### 8. HTML Report Enhancement
- **Current**: `report_to_html.py` + `templates/dashboard.html` — basic HTML conversion
- **Target**: Jinja2 templating with KPI cards, semantic color badges, interactive charts, dark mode
- **Chinese reference**: Full Jinja2 dashboard with color-coded factor pass/fail, sparkline trends, position sizing visualizations
- **Notes**: Cosmetic improvement; current HTML output is functional

### 9. Interim Report Handling Enhancement
- **Current**: Preflight detects Q1/H1/Q3 interim columns and sets annualization coefficients
- **Target**: Download BOTH annual + interim filings from EDGAR, process separately, prioritize H1 for P2/P3/P6 footnote data
- **Chinese reference**: Downloads annual + interim PDFs, processes both, merges with priority rules
- **Notes**: Would improve timeliness of footnote data mid-fiscal-year; depends on EDGAR pipeline (now implemented)

### 10. yfinance Field Discovery Tool
- **Current**: Bloomberg has `--field-check` mode to test which mnemonics return data; no equivalent for yfinance
- **Target**: `yfinance_field_discovery.py` that dumps all available DataFrame index labels for a given ticker
- **Chinese reference**: `generate_available_fields.py` for Tushare API
- **Notes**: Useful for debugging when yfinance changes field names across versions (happened with v0.2→v1.2 upgrade)

---

*Last updated: 2026-04-03*
