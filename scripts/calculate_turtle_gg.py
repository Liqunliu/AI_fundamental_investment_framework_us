#!/usr/bin/env python3
"""
US Equity Turtle GG (Penetration Return Rate) Calculator

Calculates GG from a Bloomberg/yFinance data pack:

    AA = OCF - Capex + Buybacks - Debt_Change - Dividends - SBC
    GG = AA / Market_Cap * 100
    Safety_Margin = GG - Threshold_II

The SBC (Stock-Based Compensation) deduction is US-specific: SBC dilutes
existing shareholders and is a real economic cost that Operating Cash Flow
does not capture.  Subtracting SBC from AA produces a more conservative
-- and more accurate -- penetration return for US equities, especially
in the technology sector.

Single-ticker usage:
    python3 scripts/calculate_turtle_gg.py \\
        --input output/AAPL/data_pack.md --code AAPL --threshold 0.073

Batch mode (reads tickers from a screening CSV):
    python3 scripts/calculate_turtle_gg.py \\
        --batch output/screen/tier2_shortlist.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Local project imports
# ---------------------------------------------------------------------------
# Allow running from project root  (python3 scripts/calculate_turtle_gg.py)
# or from the scripts/ directory   (python3 calculate_turtle_gg.py).
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG, get_output_dir  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("turtle_gg")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MISSING_SENTINELS = frozenset({"—", "N/A", "n/a", "-", ""})

# English label -> canonical key mapping.
# Accepts common variations from Bloomberg and yFinance data packs.
_MARKET_LABEL_MAP: Dict[str, str] = {
    "Market Cap": "market_cap",
    "Market Capitalization": "market_cap",
    "Last Price": "price",
    "Close Price": "price",
    "P/E Ratio": "pe_ratio",
    "PE Ratio": "pe_ratio",
    "P/B Ratio": "pb_ratio",
    "PB Ratio": "pb_ratio",
    "Dividend Yield": "dividend_yield",
    "Shares Outstanding": "shares_outstanding",
}

# Cash-flow / income / balance-sheet metric label -> canonical key.
_METRIC_LABEL_MAP: Dict[str, str] = {
    # Cash-flow statement
    "Operating Cash Flow": "ocf",
    "Cash from Operations": "ocf",
    "Cash Flow from Operations": "ocf",
    "Free Cash Flow": "fcf",
    "Capital Expenditure": "capex",
    "Capital Expenditures": "capex",
    "Capex": "capex",
    "Stock Buybacks": "buybacks",
    "Share Buybacks": "buybacks",
    "Stock Repurchases": "buybacks",
    "Share Repurchases": "buybacks",
    "Buybacks": "buybacks",
    "Dividends Paid": "dividends",
    "Dividends": "dividends",
    "Stock-Based Compensation": "sbc",
    "Stock Based Compensation": "sbc",
    "Share-Based Compensation": "sbc",
    "SBC": "sbc",
    # Income statement
    "Net Income": "net_income",
    "Revenue": "revenue",
    "Total Revenue": "revenue",
    "Gross Profit": "gross_profit",
    "Operating Income": "operating_income",
    "EBITDA": "ebitda",
    # Balance sheet
    "Total Debt": "total_debt",
    "Total Borrowings": "total_debt",
    "Long-Term Debt": "long_term_debt",
    "Short-Term Debt": "short_term_debt",
    "Current Debt": "short_term_debt",
    "Cash & Equivalents": "cash",
    "Cash and Equivalents": "cash",
    "Cash & Short-Term Investments": "cash",
    "Cash and Short-Term Investments": "cash",
    "Total Cash": "cash",
    "Shareholders Equity": "equity",
    "Shareholders' Equity": "equity",
    "Total Equity": "equity",
}


# ---------------------------------------------------------------------------
# Rating definitions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Rating:
    label: str
    recommendation: str


_RATING_EXCELLENT = _Rating("Excellent", "Strong buy -- GG far exceeds Threshold II")
_RATING_GOOD = _Rating("Good", "Attractive -- GG significantly above Threshold II")
_RATING_PASS = _Rating("Pass", "Acceptable -- GG clears Threshold II")
_RATING_FAIL = _Rating("Fail", "Skip -- GG below Threshold II")


# ===================================================================
# Markdown table / data-pack parsing
# ===================================================================

def _parse_numeric(raw: str) -> Optional[float]:
    """Convert a markdown cell value to float, returning None for sentinels."""
    raw = raw.strip()
    if raw in _MISSING_SENTINELS:
        return None
    # Strip leading $ and trailing M/B/%
    cleaned = raw.lstrip("$").rstrip("%MmBb").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        val = float(cleaned)
    except ValueError:
        return None
    # If the original value ended with 'B' (billions), convert to millions
    if raw.rstrip().upper().endswith("B"):
        val *= 1_000.0
    return val


def _parse_markdown_table(lines: List[str], start_idx: int) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """Parse a markdown table starting at *start_idx*.

    Returns (headers, rows_as_dicts, next_line_idx).
    """
    i = start_idx
    # Advance to the first pipe-delimited line.
    while i < len(lines) and not lines[i].strip().startswith("|"):
        i += 1
    if i >= len(lines):
        return [], [], i

    # Header row
    header_line = lines[i].strip()
    headers = [h.strip() for h in header_line.split("|")[1:-1]]
    i += 1

    # Separator row  (| --- | --- |)
    if i < len(lines) and re.match(r"\|\s*[-:]+", lines[i].strip()):
        i += 1

    # Data rows
    rows: List[Dict[str, Any]] = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
        row: Dict[str, Any] = {}
        for j, hdr in enumerate(headers):
            if j < len(cells):
                num = _parse_numeric(cells[j])
                row[hdr] = num if num is not None else cells[j]
            else:
                row[hdr] = None
        rows.append(row)
        i += 1

    return headers, rows, i


# ===================================================================
# Data extraction helpers
# ===================================================================

def _extract_market_data(content: str) -> Dict[str, float]:
    """Extract key/value bullet-point market data from ``## Market Data``."""
    result: Dict[str, float] = {}
    in_section = False

    for line in content.splitlines():
        if re.match(r"^##\s+Market\s+Data", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if not in_section:
            continue

        # Pattern: - **Market Cap**: 3,456,789.12
        m = re.match(r"-\s*\*\*(.+?)\*\*\s*:\s*(.+)", line)
        if not m:
            continue
        label, raw_val = m.group(1).strip(), m.group(2).strip()
        canonical = _MARKET_LABEL_MAP.get(label)
        if canonical is None:
            continue
        num = _parse_numeric(raw_val)
        if num is not None:
            result[canonical] = num

    return result


def _extract_sections(content: str) -> Dict[str, Dict[str, Any]]:
    """Extract financial-statement tables keyed by section name.

    Recognized sections (case-insensitive):
        ## Income Statement, ## Balance Sheet, ## Cash Flow,
        ## Share Buybacks
    """
    section_map = {
        "income statement": "income",
        "balance sheet": "balance",
        "cash flow": "cashflow",
        "share buybacks": "buybacks",
    }

    lines = content.splitlines()
    sections: Dict[str, Dict[str, Any]] = {}

    i = 0
    while i < len(lines):
        m = re.match(r"^##\s+(.+)", lines[i])
        if m:
            title = m.group(1).strip().lower()
            key = section_map.get(title)
            if key:
                headers, rows, i = _parse_markdown_table(lines, i + 1)
                sections[key] = {"headers": headers, "rows": rows}
                continue
        i += 1

    return sections


def _latest_value(rows: List[Dict[str, Any]], metric_key: str) -> float:
    """Return the most-recent numeric value for *metric_key* from table rows.

    The first column is assumed to be the metric label.  We resolve the
    label via ``_METRIC_LABEL_MAP`` and then return the last numeric
    cell in that row.
    """
    if not rows:
        return 0.0

    first_header = None
    for row in rows:
        for k in row:
            first_header = k
            break
        break

    for row in rows:
        if first_header is None:
            continue
        label_cell = row.get(first_header, "")
        if not isinstance(label_cell, str):
            continue
        canonical = _METRIC_LABEL_MAP.get(label_cell.strip())
        if canonical == metric_key:
            values = [
                v for k, v in row.items()
                if k != first_header and isinstance(v, (int, float))
            ]
            if values:
                return float(values[-1])
    return 0.0


def _latest_two_values(rows: List[Dict[str, Any]], metric_key: str) -> Tuple[float, float]:
    """Return (previous_period, latest_period) for *metric_key*.

    If only one period is available, previous defaults to 0.
    """
    if not rows:
        return 0.0, 0.0

    first_header = None
    for row in rows:
        for k in row:
            first_header = k
            break
        break

    for row in rows:
        if first_header is None:
            continue
        label_cell = row.get(first_header, "")
        if not isinstance(label_cell, str):
            continue
        canonical = _METRIC_LABEL_MAP.get(label_cell.strip())
        if canonical == metric_key:
            values = [
                v for k, v in row.items()
                if k != first_header and isinstance(v, (int, float))
            ]
            if len(values) >= 2:
                return float(values[-2]), float(values[-1])
            if len(values) == 1:
                return 0.0, float(values[-1])
    return 0.0, 0.0


# ===================================================================
# Core GG calculation
# ===================================================================

@dataclass
class GGResult:
    """Container for all GG calculation outputs."""

    stock_code: str

    # Inputs
    market_cap: float
    ocf: float
    fcf: float
    capex: float
    buybacks: float
    dividends: float
    sbc: float
    net_income: float
    revenue: float

    # Debt
    debt_current: float
    debt_previous: float
    debt_change: float
    cash_current: float
    cash_previous: float
    net_debt_change: float

    # Calculated
    aa_standard: float
    aa_net_debt: float
    gg_standard: float
    gg_net_debt: float
    fcf_yield: float

    # Threshold
    threshold_pct: float  # e.g. 7.30
    safety_margin: float  # GG - threshold (pct points)
    pass_threshold: bool

    # Quality
    ocf_ni_ratio: float  # OCF / Net Income (%)

    # Rating
    rating: _Rating

    @property
    def safety_margin_x(self) -> float:
        """Safety margin expressed as a multiplier of threshold."""
        return self.gg_standard / self.threshold_pct if self.threshold_pct else 0.0


def calculate_gg(
    input_file: Path,
    stock_code: str,
    threshold: float | None = None,
    rf: float | None = None,
) -> GGResult:
    """Calculate Turtle GG from a data-pack markdown file.

    Args:
        input_file: Path to data_pack.md.
        stock_code: Ticker symbol (e.g. ``AAPL``).
        threshold: GG hurdle rate as a decimal (e.g. 0.073).  When
            *None*, derived from ``Rf + 3%`` using the config default.
        rf: Risk-free rate override (decimal).

    Returns:
        Populated :class:`GGResult`.

    Raises:
        FileNotFoundError: If *input_file* does not exist.
        ValueError: If critical data (market cap) is missing.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Data pack not found: {input_file}")

    content = input_file.read_text(encoding="utf-8")

    # --- Resolve threshold ---
    if rf is None:
        rf = DEFAULT_CONFIG.risk_free_rate
    if threshold is None:
        threshold = rf + DEFAULT_CONFIG.threshold_premium

    threshold_pct = threshold * 100.0  # e.g. 7.30

    # --- Parse ---
    market_data = _extract_market_data(content)
    sections = _extract_sections(content)

    market_cap = market_data.get("market_cap", 0.0)
    if market_cap <= 0:
        raise ValueError(
            f"Market cap not found or zero in {input_file}. "
            "Ensure the data pack contains a '## Market Data' section "
            "with a '**Market Cap**' entry."
        )

    # --- Cash-flow metrics ---
    cf_rows = sections.get("cashflow", {}).get("rows", [])

    ocf = _latest_value(cf_rows, "ocf")
    fcf = _latest_value(cf_rows, "fcf")
    capex_raw = _latest_value(cf_rows, "capex")
    # Capex is typically reported as negative; we want a positive number.
    capex = abs(capex_raw) if capex_raw else (ocf - fcf if fcf else 0.0)

    sbc = _latest_value(cf_rows, "sbc")
    # SBC is sometimes reported as positive (non-cash add-back in OCF).
    sbc = abs(sbc)

    dividends_raw = _latest_value(cf_rows, "dividends")
    dividends = abs(dividends_raw)  # reported as negative outflow

    # --- Buybacks ---
    # May live in a dedicated section or in the cash-flow table.
    buybacks_section_rows = sections.get("buybacks", {}).get("rows", [])
    buybacks_raw = _latest_value(buybacks_section_rows, "buybacks")
    if buybacks_raw == 0.0:
        buybacks_raw = _latest_value(cf_rows, "buybacks")
    buybacks = abs(buybacks_raw)  # positive = shareholder return

    # --- Balance-sheet: debt & cash ---
    bs_rows = sections.get("balance", {}).get("rows", [])

    debt_prev, debt_curr = _latest_two_values(bs_rows, "total_debt")
    # Fallback: sum short-term + long-term if total_debt is missing.
    if debt_curr == 0.0:
        _, st = _latest_two_values(bs_rows, "short_term_debt")
        _, lt = _latest_two_values(bs_rows, "long_term_debt")
        prev_st, _ = _latest_two_values(bs_rows, "short_term_debt")
        prev_lt, _ = _latest_two_values(bs_rows, "long_term_debt")
        debt_curr = st + lt
        debt_prev = prev_st + prev_lt

    debt_change = debt_curr - debt_prev

    cash_prev, cash_curr = _latest_two_values(bs_rows, "cash")
    net_debt_curr = debt_curr - cash_curr
    net_debt_prev = debt_prev - cash_prev
    net_debt_change = net_debt_curr - net_debt_prev

    # --- Income statement ---
    inc_rows = sections.get("income", {}).get("rows", [])
    net_income = _latest_value(inc_rows, "net_income")
    revenue = _latest_value(inc_rows, "revenue")

    # --- AA and GG ---
    # Standard AA:  OCF - Capex + Buybacks - Debt_Change - Dividends - SBC
    aa_standard = ocf - capex + buybacks - debt_change - dividends - sbc

    # Net-debt-adjusted AA replaces raw debt change with net-debt change.
    aa_net_debt = ocf - capex + buybacks - net_debt_change - dividends - sbc

    gg_standard = (aa_standard / market_cap) * 100.0
    gg_net_debt = (aa_net_debt / market_cap) * 100.0
    fcf_yield = (fcf / market_cap) * 100.0 if fcf > 0 else 0.0

    safety_margin = gg_standard - threshold_pct
    pass_threshold = gg_standard >= threshold_pct

    # OCF / Net-Income quality ratio
    ocf_ni_ratio = (ocf / net_income * 100.0) if net_income != 0 else 0.0

    # Rating
    if gg_standard >= threshold_pct * 3:
        rating = _RATING_EXCELLENT
    elif gg_standard >= threshold_pct * 2:
        rating = _RATING_GOOD
    elif gg_standard >= threshold_pct:
        rating = _RATING_PASS
    else:
        rating = _RATING_FAIL

    return GGResult(
        stock_code=stock_code,
        market_cap=market_cap,
        ocf=ocf,
        fcf=fcf,
        capex=capex,
        buybacks=buybacks,
        dividends=dividends,
        sbc=sbc,
        net_income=net_income,
        revenue=revenue,
        debt_current=debt_curr,
        debt_previous=debt_prev,
        debt_change=debt_change,
        cash_current=cash_curr,
        cash_previous=cash_prev,
        net_debt_change=net_debt_change,
        aa_standard=aa_standard,
        aa_net_debt=aa_net_debt,
        gg_standard=gg_standard,
        gg_net_debt=gg_net_debt,
        fcf_yield=fcf_yield,
        threshold_pct=threshold_pct,
        safety_margin=safety_margin,
        pass_threshold=pass_threshold,
        ocf_ni_ratio=ocf_ni_ratio,
        rating=rating,
    )


# ===================================================================
# Report formatting
# ===================================================================

def _fmt(value: float, decimals: int = 2) -> str:
    """Format a number with commas and fixed decimals."""
    return f"{value:,.{decimals}f}"


def format_report(r: GGResult) -> str:
    """Render a full English markdown report for a single ticker."""
    L: List[str] = []  # noqa: N806 (short alias for readability)

    # Title
    L.append(f"# {r.stock_code} -- Turtle GG Penetration Return Analysis")
    L.append("")
    L.append(f"**Calculated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"**Threshold II**: {_fmt(r.threshold_pct)}%  (Rf + 3%)")
    L.append("")
    L.append("---")
    L.append("")

    # ------------------------------------------------------------------
    # 1. GG Calculation Results
    # ------------------------------------------------------------------
    L.append("## GG Calculation Results")
    L.append("")

    status = "PASS" if r.pass_threshold else "FAIL"
    L.append(f"**GG (Standard)**: **{_fmt(r.gg_standard)}%** -- {status}")
    L.append(f"**Safety Margin**: {_fmt(r.safety_margin)} pct points "
             f"({_fmt(r.safety_margin_x)}x threshold)")
    L.append("")

    L.append("| Method | GG (%) | vs Threshold |")
    L.append("|--------|-------:|:------------:|")
    _row = lambda name, val: f"| {name} | {_fmt(val)} | {'PASS' if val >= r.threshold_pct else 'FAIL'} |"
    L.append(_row("Standard Turtle GG", r.gg_standard))
    L.append(_row("Net-Debt-Adjusted GG", r.gg_net_debt))
    L.append(_row("FCF Yield", r.fcf_yield))
    L.append("")

    # ------------------------------------------------------------------
    # 2. Calculation Details
    # ------------------------------------------------------------------
    L.append("## Calculation Details")
    L.append("")
    L.append("### Standard GG Formula")
    L.append("```")
    L.append("AA = OCF - Capex + Buybacks - Debt_Change - Dividends - SBC")
    L.append(f"AA = {_fmt(r.ocf)} - {_fmt(r.capex)} + {_fmt(r.buybacks)} "
             f"- ({_fmt(r.debt_change)}) - {_fmt(r.dividends)} - {_fmt(r.sbc)}")
    L.append(f"AA = {_fmt(r.aa_standard)}")
    L.append("")
    L.append(f"GG = AA / Market_Cap * 100")
    L.append(f"GG = {_fmt(r.aa_standard)} / {_fmt(r.market_cap)} * 100")
    L.append(f"GG = {_fmt(r.gg_standard)}%")
    L.append("```")
    L.append("")

    L.append("### Net-Debt-Adjusted GG")
    L.append("```")
    L.append("AA = OCF - Capex + Buybacks - Net_Debt_Change - Dividends - SBC")
    L.append(f"AA = {_fmt(r.ocf)} - {_fmt(r.capex)} + {_fmt(r.buybacks)} "
             f"- ({_fmt(r.net_debt_change)}) - {_fmt(r.dividends)} - {_fmt(r.sbc)}")
    L.append(f"AA = {_fmt(r.aa_net_debt)}")
    L.append("")
    L.append(f"GG = {_fmt(r.aa_net_debt)} / {_fmt(r.market_cap)} * 100")
    L.append(f"GG = {_fmt(r.gg_net_debt)}%")
    L.append("```")
    L.append("")

    # ------------------------------------------------------------------
    # 3. Data Breakdown
    # ------------------------------------------------------------------
    L.append("## Data Breakdown")
    L.append("")

    L.append("### Market Data")
    L.append(f"- **Market Cap**: ${_fmt(r.market_cap)}M")
    L.append("")

    L.append("### Cash Flow (millions USD, TTM)")
    L.append(f"- **Operating Cash Flow (OCF)**: ${_fmt(r.ocf)}M")
    L.append(f"- **Free Cash Flow (FCF)**: ${_fmt(r.fcf)}M")
    L.append(f"- **Capital Expenditure**: ${_fmt(r.capex)}M")
    L.append(f"- **FCF Yield**: {_fmt(r.fcf_yield)}%")
    L.append("")

    L.append("### Debt (millions USD)")
    L.append(f"- **Current Total Debt**: ${_fmt(r.debt_current)}M")
    L.append(f"- **Prior Total Debt**: ${_fmt(r.debt_previous)}M")
    L.append(f"- **Debt Change**: ${_fmt(r.debt_change)}M")
    L.append(f"- **Current Cash**: ${_fmt(r.cash_current)}M")
    L.append(f"- **Net Debt Change**: ${_fmt(r.net_debt_change)}M")
    L.append("")

    L.append("### Shareholder Returns (millions USD)")
    L.append(f"- **Stock Buybacks**: ${_fmt(r.buybacks)}M")
    L.append(f"- **Dividends Paid**: ${_fmt(r.dividends)}M")
    L.append("")

    L.append("### Stock-Based Compensation (US-Specific Adjustment)")
    L.append(f"- **SBC**: ${_fmt(r.sbc)}M")
    if r.sbc > 0 and r.ocf > 0:
        sbc_pct_ocf = r.sbc / r.ocf * 100.0
        L.append(f"- **SBC as % of OCF**: {_fmt(sbc_pct_ocf)}%")
        if sbc_pct_ocf > 30:
            L.append("- **Warning**: SBC exceeds 30% of OCF -- significant dilution risk")
        elif sbc_pct_ocf > 15:
            L.append("- **Note**: SBC is a material portion of OCF")
        else:
            L.append("- SBC is a modest share of OCF")
    L.append("")

    # ------------------------------------------------------------------
    # 4. Cash Flow Quality
    # ------------------------------------------------------------------
    L.append("## Cash Flow Quality")
    L.append("")
    L.append(f"- **Net Income**: ${_fmt(r.net_income)}M")
    L.append(f"- **OCF / Net Income**: {_fmt(r.ocf_ni_ratio)}%")

    if r.ocf_ni_ratio > 120:
        assessment = "Excellent -- cash generation well above reported earnings"
    elif r.ocf_ni_ratio > 100:
        assessment = "Strong -- cash flow exceeds net income"
    elif r.ocf_ni_ratio > 80:
        assessment = "Good -- cash conversion within normal range"
    elif r.ocf_ni_ratio > 50:
        assessment = "Fair -- some gap between earnings and cash flow"
    elif r.ocf_ni_ratio > 0:
        assessment = "Weak -- poor cash conversion, investigate accruals"
    else:
        assessment = "N/A -- negative net income or OCF"

    L.append(f"- **Assessment**: {assessment}")
    L.append("")

    # ------------------------------------------------------------------
    # 5. Investment Conclusion
    # ------------------------------------------------------------------
    L.append("## Investment Conclusion")
    L.append("")
    L.append(f"**Rating**: {r.rating.label}")
    L.append(f"**Recommendation**: {r.rating.recommendation}")
    L.append("")

    # Qualitative checklist
    L.append("**Key considerations**:")
    L.append(f"- GG {'exceeds' if r.pass_threshold else 'falls below'} "
             f"Threshold II ({_fmt(r.threshold_pct)}%)")
    if r.sbc > 0:
        L.append(f"- SBC-adjusted AA is ${_fmt(r.aa_standard)}M "
                 f"(pre-SBC would be ${_fmt(r.aa_standard + r.sbc)}M)")
    if r.buybacks > 0:
        L.append(f"- Share buybacks of ${_fmt(r.buybacks)}M support per-share value")
    if r.dividends > 0:
        L.append(f"- Dividend payout of ${_fmt(r.dividends)}M")
    L.append("- Combine with qualitative analysis (moat, management, industry cycle)")
    L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by US Equity Turtle GG Calculator*")

    return "\n".join(L)


# ===================================================================
# Console summary
# ===================================================================

def _print_summary(r: GGResult) -> None:
    """Print a concise GG summary to stdout."""
    w = 70
    print(f"\n{'=' * w}")
    print("Turtle GG Calculator -- US Equity")
    print(f"{'=' * w}")
    print(f"  Ticker:       {r.stock_code}")
    print(f"  Market Cap:   ${_fmt(r.market_cap)}M")
    print(f"  Threshold II: {_fmt(r.threshold_pct)}%")
    print(f"{'=' * w}")

    print(f"\n  GG Calculation Results")
    print(f"  {'-' * (w - 4)}")
    print(f"  GG (Standard):         {r.gg_standard:>8.2f}%")
    print(f"  GG (Net-Debt-Adj):     {r.gg_net_debt:>8.2f}%")
    print(f"  FCF Yield:             {r.fcf_yield:>8.2f}%")
    print(f"  Safety Margin:         {r.safety_margin:>+8.2f} pct pts")
    print(f"  Safety Margin (x):     {r.safety_margin_x:>8.2f}x")
    print(f"  {'-' * (w - 4)}")

    status = "PASS" if r.pass_threshold else "FAIL"
    print(f"  Status: {status}  |  Rating: {r.rating.label}")
    print()


# ===================================================================
# Batch mode
# ===================================================================

def _load_tickers_from_csv(csv_path: Path) -> List[str]:
    """Read ticker symbols from a screening CSV.

    Expects either:
      - A column named ``Ticker`` (case-insensitive), or
      - The first column if no header match is found.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Batch CSV not found: {csv_path}")

    tickers: List[str] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        # Find the ticker column.
        fieldnames = reader.fieldnames or []
        ticker_col: Optional[str] = None
        for fn in fieldnames:
            if fn.strip().lower() in ("ticker", "symbol", "code", "stock"):
                ticker_col = fn
                break
        if ticker_col is None and fieldnames:
            ticker_col = fieldnames[0]  # fall back to first column
        if ticker_col is None:
            raise ValueError(f"Cannot determine ticker column in {csv_path}")

        for row in reader:
            val = row.get(ticker_col, "").strip().upper()
            if val and val not in tickers:
                tickers.append(val)

    return tickers


def run_batch(
    csv_path: Path,
    threshold: float | None = None,
    rf: float | None = None,
    output_dir_override: Path | None = None,
) -> List[Dict[str, Any]]:
    """Run GG calculation for every ticker in *csv_path*.

    For each ticker the expected data-pack path is
    ``output/<TICKER>/data_pack.md`` relative to the project root.

    Returns a list of summary dicts (one per ticker).
    """
    tickers = _load_tickers_from_csv(csv_path)
    if not tickers:
        logger.warning("No tickers found in %s", csv_path)
        return []

    project_root = _SCRIPTS_DIR.parent
    results: List[Dict[str, Any]] = []
    successes = 0
    failures = 0

    print(f"\nBatch mode: {len(tickers)} tickers from {csv_path}\n")

    for ticker in tickers:
        data_pack = project_root / "output" / ticker / "data_pack.md"
        if not data_pack.exists():
            logger.warning("  [SKIP] %s -- data_pack.md not found at %s", ticker, data_pack)
            failures += 1
            results.append({"ticker": ticker, "status": "SKIP", "reason": "no data pack"})
            continue

        try:
            r = calculate_gg(data_pack, ticker, threshold=threshold, rf=rf)

            # Determine output directory.
            if output_dir_override:
                out_dir = output_dir_override
            else:
                out_dir = Path(get_output_dir(ticker))
            out_dir.mkdir(parents=True, exist_ok=True)

            report_path = out_dir / f"{ticker}_GG.md"
            report_path.write_text(format_report(r), encoding="utf-8")

            status = "PASS" if r.pass_threshold else "FAIL"
            print(f"  [{status}] {ticker:>6s}  GG={r.gg_standard:6.2f}%  "
                  f"SM={r.safety_margin:+6.2f}  -> {report_path}")

            successes += 1
            results.append({
                "ticker": ticker,
                "status": status,
                "gg_standard": round(r.gg_standard, 2),
                "gg_net_debt": round(r.gg_net_debt, 2),
                "fcf_yield": round(r.fcf_yield, 2),
                "safety_margin": round(r.safety_margin, 2),
                "rating": r.rating.label,
                "report": str(report_path),
            })

        except Exception as exc:
            logger.error("  [ERR]  %s -- %s", ticker, exc)
            failures += 1
            results.append({"ticker": ticker, "status": "ERROR", "reason": str(exc)})

    # Batch summary
    print(f"\nBatch complete: {successes} processed, {failures} skipped/errored "
          f"out of {len(tickers)} tickers.\n")

    # Write batch summary CSV alongside the input.
    summary_csv = csv_path.parent / "gg_batch_results.csv"
    if results:
        keys = list(results[0].keys())
        # Gather all unique keys across results.
        all_keys: List[str] = []
        seen: set[str] = set()
        for row in results:
            for k in row:
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)

        with open(summary_csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print(f"  Batch summary written to {summary_csv}\n")

    return results


# ===================================================================
# CLI entry point
# ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="US Equity Turtle GG (Penetration Return Rate) Calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Single-ticker mode
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a Bloomberg/yFinance data pack (.md file)",
    )
    parser.add_argument(
        "--code",
        help="Stock ticker (e.g. AAPL, MSFT, GOOGL)",
    )

    # Batch mode
    parser.add_argument(
        "--batch",
        type=Path,
        help="Path to a CSV with tickers for batch processing "
             "(e.g. output/screen/tier2_shortlist.csv)",
    )

    # Common options
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="GG threshold as decimal (default: Rf+3%% = %(default)s). "
             "Example: 0.073 for 7.30%%",
    )
    parser.add_argument(
        "--rf",
        type=float,
        default=None,
        help=f"Risk-free rate override (default: {DEFAULT_CONFIG.risk_free_rate})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file or directory path (single mode: file; batch mode: directory)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # ----- Batch mode -----
    if args.batch:
        run_batch(
            csv_path=args.batch,
            threshold=args.threshold,
            rf=args.rf,
            output_dir_override=args.output,
        )
        return

    # ----- Single-ticker mode -----
    if not args.input or not args.code:
        parser.error("Single-ticker mode requires both --input and --code. "
                     "Alternatively, use --batch for batch processing.")

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        result = calculate_gg(
            input_file=args.input,
            stock_code=args.code,
            threshold=args.threshold,
            rf=args.rf,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)

    # Console output
    _print_summary(result)

    # Write report
    report = format_report(result)

    if args.output:
        output_file = args.output
    else:
        out_dir = Path(get_output_dir(args.code))
        out_dir.mkdir(parents=True, exist_ok=True)
        output_file = out_dir / f"{args.code}_GG.md"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding="utf-8")

    print(f"  Report saved to: {output_file}")
    print(f"  File size: {output_file.stat().st_size:,} bytes")
    print()


if __name__ == "__main__":
    main()
