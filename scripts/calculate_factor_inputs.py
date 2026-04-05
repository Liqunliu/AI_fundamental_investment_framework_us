#!/usr/bin/env python3
"""
US Equity Quality Yield — Factor Inputs Calculator

Pre-computes 7 subsections of derived metrics from data_pack.md:

  §16.1  Financial Trends     — CAGR, multi-year trend indicators
  §16.2  Factor 2 Inputs      — Owner Earnings, payout ratio stats
  §16.3  True Cash Revenue    — Revenue − ΔAR, collection ratio
  §16.4  Operating Outflows   — COGS + Tax + Interest − ΔAP breakdown
  §16.5  Base Surplus          — OCF − Capex, AA average, λ (operating leverage)
  §16.6  Price Position        — 10/25/50/75/90 percentiles from §10
  §16.7  Valuation Dashboard   — EV/EBITDA, Net Debt/EBITDA, Shareholder Yield, FCF Yield

Usage:
    python3 scripts/calculate_factor_inputs.py \\
        --input output/AAPL/data_pack.md --code AAPL

Output: output/{TICKER}/{TICKER}_factor_inputs.md
"""

from __future__ import annotations

import argparse
import logging
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Project imports — reuse parsing infrastructure from calculate_qy_gg.py
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG, get_output_dir  # noqa: E402

logger = logging.getLogger("factor_inputs")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MISSING = frozenset({"—", "N/A", "n/a", "-", ""})


# ===================================================================
# Markdown parsing (self-contained — mirrors calculate_qy_gg.py)
# ===================================================================

def _parse_numeric(raw: str) -> Optional[float]:
    """Convert a markdown cell value to float."""
    raw = raw.strip()
    if raw in _MISSING:
        return None
    cleaned = raw.lstrip("$").rstrip("%MmBb").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        val = float(cleaned)
    except ValueError:
        return None
    if raw.rstrip().upper().endswith("B"):
        val *= 1_000.0
    return val


def _parse_markdown_table(lines: List[str], start_idx: int) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """Parse a markdown table starting at *start_idx*."""
    i = start_idx
    while i < len(lines) and not lines[i].strip().startswith("|"):
        i += 1
    if i >= len(lines):
        return [], [], i

    header_line = lines[i].strip()
    headers = [h.strip() for h in header_line.split("|")[1:-1]]
    i += 1

    if i < len(lines) and re.match(r"\|\s*[-:]+", lines[i].strip()):
        i += 1

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


def _extract_sections(content: str) -> Dict[str, Dict[str, Any]]:
    """Extract financial-statement tables keyed by section name."""
    section_map = {
        "income statement": "income",
        "balance sheet": "balance",
        "cash flow": "cashflow",
        "cash flow statement": "cashflow",
        "share buybacks": "buybacks",
        "financial ratios": "ratios",
        "derived metrics": "derived",
    }

    lines = content.splitlines()
    sections: Dict[str, Dict[str, Any]] = {}

    i = 0
    while i < len(lines):
        m = re.match(r"^##\s+(?:\d+\.\s+)?(.+)", lines[i])
        if m:
            title = m.group(1).strip().lower()
            key = section_map.get(title)
            if key:
                headers, rows, i = _parse_markdown_table(lines, i + 1)
                sections[key] = {"headers": headers, "rows": rows}
                continue
        i += 1

    return sections


def _extract_market_data(content: str) -> Dict[str, float]:
    """Extract bullet-point market data from ## Market Data."""
    _LABEL_MAP = {
        "Market Cap": "market_cap",
        "Market Capitalization": "market_cap",
        "Last Price": "price",
        "Close Price": "price",
        "Current Price": "price",
        "P/E Ratio": "pe_ratio",
        "PE Ratio": "pe_ratio",
        "PE (TTM)": "pe_ratio",
        "P/B Ratio": "pb_ratio",
        "PB Ratio": "pb_ratio",
        "PB": "pb_ratio",
        "Dividend Yield": "dividend_yield",
        "Shares Outstanding": "shares_outstanding",
    }
    result: Dict[str, float] = {}
    in_section = False
    for line in content.splitlines():
        if re.match(r"^##\s+(?:\d+\.\s+)?Market\s+Data", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section and line.startswith("##"):
            break
        if not in_section:
            continue
        m = re.match(r"-\s*\*\*(.+?)\*\*\s*:\s*(.+)", line)
        if not m:
            continue
        label, raw_val = m.group(1).strip(), m.group(2).strip()
        canonical = _LABEL_MAP.get(label)
        if canonical is None:
            continue
        num = _parse_numeric(raw_val)
        if num is not None:
            result[canonical] = num
    return result


def _extract_price_summary(content: str) -> List[Dict[str, Any]]:
    """Extract Annual Price Summary table from §10 Historical Prices."""
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if "Annual Price Summary" in lines[i]:
            _, rows, _ = _parse_markdown_table(lines, i + 1)
            return rows
        i += 1
    return []


# ===================================================================
# Row-level helpers
# ===================================================================

_METRIC_LABEL_MAP: Dict[str, str] = {
    # Income
    "Revenue": "revenue", "Total Revenue": "revenue",
    "Cost of Revenue": "cost_of_revenue", "COGS": "cost_of_revenue",
    "Gross Profit": "gross_profit",
    "Operating Income": "operating_income",
    "EBITDA": "ebitda",
    "Net Income": "net_income",
    "Pretax Income": "pretax_income",
    "Income Tax": "income_tax", "Income Tax Expense": "income_tax",
    "Interest Expense": "interest_expense",
    # Balance Sheet
    "Total Assets": "total_assets",
    "Current Assets": "current_assets",
    "Cash & Equivalents": "cash", "Cash and Equivalents": "cash",
    "Cash & Short-Term Investments": "cash",
    "Accounts Receivable": "accounts_receivable",
    "Inventory": "inventory",
    "Accounts Payable": "accounts_payable",
    "Deferred Revenue": "deferred_revenue",
    "Deferred Tax Assets": "deferred_tax_assets",
    "Deferred Tax Liabilities": "deferred_tax_liabilities",
    "Non-Current Assets": "non_current_assets",
    "Net PP&E": "net_ppe",
    "Goodwill": "goodwill",
    "Intangible Assets": "intangible_assets",
    "Total Liabilities": "total_liabilities",
    "Current Liabilities": "current_liabilities",
    "Current Debt": "short_term_debt", "Short-Term Debt": "short_term_debt",
    "Long-Term Debt": "long_term_debt",
    "Stockholders' Equity": "equity", "Shareholders' Equity": "equity",
    "Shareholders Equity": "equity", "Total Equity": "equity",
    # Cash Flow
    "Operating Cash Flow": "ocf", "Cash from Operations": "ocf",
    "Capital Expenditure": "capex", "Capital Expenditures": "capex",
    "Free Cash Flow": "fcf",
    "Depreciation & Amortization": "depreciation",
    "Depreciation And Amortization": "depreciation",
    "Stock-Based Compensation": "sbc", "Stock Based Compensation": "sbc",
    "Share Buybacks": "buybacks", "Share Repurchases": "buybacks",
    "Stock Buybacks": "buybacks", "Stock Repurchases": "buybacks",
    "Dividends Paid": "dividends", "Dividends": "dividends",
}


def _columns_are_descending(rows: List[Dict[str, Any]]) -> bool:
    """Detect if table columns are newest-first."""
    if not rows:
        return False
    years = []
    for key in rows[0]:
        m = re.match(r"(\d{4})", str(key))
        if m:
            years.append(int(m.group(1)))
    if len(years) >= 2:
        return years[0] > years[-1]
    return False


def _year_columns(rows: List[Dict[str, Any]]) -> List[str]:
    """Return year column headers in chronological order."""
    if not rows:
        return []
    first_header = None
    year_cols = []
    for key in rows[0]:
        if first_header is None:
            first_header = key
            continue
        if re.match(r"\d{4}", str(key)):
            year_cols.append(key)
    desc = _columns_are_descending(rows)
    if desc:
        year_cols = list(reversed(year_cols))
    return year_cols


def _get_series(rows: List[Dict[str, Any]], metric_key: str) -> List[Tuple[str, Optional[float]]]:
    """Return [(year, value), ...] in chronological order for *metric_key*."""
    if not rows:
        return []

    first_header = None
    for key in rows[0]:
        first_header = key
        break

    year_cols = _year_columns(rows)
    desc = _columns_are_descending(rows)

    for row in rows:
        if first_header is None:
            continue
        label_cell = row.get(first_header, "")
        if not isinstance(label_cell, str):
            continue
        canonical = _METRIC_LABEL_MAP.get(label_cell.strip())
        if canonical == metric_key:
            # Build series in chronological order
            result = []
            for col in year_cols:
                val = row.get(col)
                if isinstance(val, (int, float)):
                    result.append((str(col), float(val)))
                else:
                    result.append((str(col), None))
            return result
    return []


def _values_only(series: List[Tuple[str, Optional[float]]]) -> List[float]:
    """Extract non-None values from a series."""
    return [v for _, v in series if v is not None]


def _latest(series: List[Tuple[str, Optional[float]]]) -> Optional[float]:
    """Latest non-None value from chronological series."""
    for _, v in reversed(series):
        if v is not None:
            return v
    return None


# ===================================================================
# Subsection builders
# ===================================================================

def _fmt_val(v: Optional[float], suffix: str = "") -> str:
    """Format a value for markdown output."""
    if v is None:
        return "—"
    if suffix == "%":
        return f"{v:.2f}%"
    return f"{v:,.2f}{suffix}"


def _cagr(oldest: float, newest: float, n: int) -> Optional[float]:
    """CAGR as a percentage. Returns None if inputs invalid."""
    if oldest <= 0 or newest <= 0 or n <= 0:
        return None
    return ((newest / oldest) ** (1.0 / n) - 1) * 100


def _section_16_1(sections: Dict) -> str:
    """§16.1 Financial Trends — CAGR and multi-year trend indicators."""
    income_rows = sections.get("income", {}).get("rows", [])
    cf_rows = sections.get("cashflow", {}).get("rows", [])
    bs_rows = sections.get("balance", {}).get("rows", [])

    metrics = [
        ("Revenue", "revenue", income_rows),
        ("Gross Profit", "gross_profit", income_rows),
        ("Operating Income", "operating_income", income_rows),
        ("Net Income", "net_income", income_rows),
        ("EBITDA", "ebitda", income_rows),
        ("Operating Cash Flow", "ocf", cf_rows),
        ("Free Cash Flow", "fcf", cf_rows),
        ("Total Assets", "total_assets", bs_rows),
        ("Stockholders' Equity", "equity", bs_rows),
    ]

    lines = ["### §16.1 Financial Trends", ""]
    headers = ["Metric", "Oldest", "Latest", "Years", "CAGR", "Trend"]
    rows_out = []

    for label, key, source_rows in metrics:
        series = _get_series(source_rows, key)
        vals = _values_only(series)
        if len(vals) < 2:
            rows_out.append([label, "—", "—", "—", "—", "—"])
            continue

        oldest_val = vals[0]
        newest_val = vals[-1]
        n = len(vals) - 1
        cagr_val = _cagr(abs(oldest_val), abs(newest_val), n) if oldest_val > 0 and newest_val > 0 else None

        # Trend: count consecutive improvements from most recent
        trend_dir = "→"
        if len(vals) >= 3:
            ups = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
            downs = sum(1 for i in range(1, len(vals)) if vals[i] < vals[i - 1])
            if ups >= len(vals) - 1:
                trend_dir = "↑↑"
            elif ups > downs:
                trend_dir = "↑"
            elif downs >= len(vals) - 1:
                trend_dir = "↓↓"
            elif downs > ups:
                trend_dir = "↓"

        rows_out.append([
            label,
            _fmt_val(oldest_val),
            _fmt_val(newest_val),
            str(n),
            _fmt_val(cagr_val, "%") if cagr_val is not None else "—",
            trend_dir,
        ])

    alignments = ["l", "r", "r", "r", "r", "c"]
    lines.append(_build_table(headers, rows_out, alignments))
    return "\n".join(lines)


def _section_16_2(sections: Dict) -> str:
    """§16.2 Factor 2 Inputs — Owner Earnings, payout ratio stats."""
    income_rows = sections.get("income", {}).get("rows", [])
    cf_rows = sections.get("cashflow", {}).get("rows", [])

    ni_series = _get_series(income_rows, "net_income")
    da_series = _get_series(cf_rows, "depreciation")
    capex_series = _get_series(cf_rows, "capex")
    sbc_series = _get_series(cf_rows, "sbc")
    div_series = _get_series(cf_rows, "dividends")

    lines = ["### §16.2 Factor 2 Inputs", ""]

    # Owner Earnings per year
    year_cols = [yr for yr, _ in ni_series] if ni_series else []
    oe_data = []

    lines.append("**Owner Earnings by Year**:")
    lines.append("")
    oe_headers = ["Year", "Net Income", "D&A", "Capex", "OE", "OE (ex-SBC)", "SBC"]
    oe_rows = []

    for yr in year_cols:
        ni = next((v for y, v in ni_series if y == yr), None)
        da = next((v for y, v in da_series if y == yr), None)
        cx = next((v for y, v in capex_series if y == yr), None)
        sbc = next((v for y, v in sbc_series if y == yr), None)

        if ni is not None and da is not None and cx is not None:
            cx_abs = abs(cx)
            da_abs = abs(da) if da else 0
            oe = ni + da_abs - cx_abs
            sbc_abs = abs(sbc) if sbc else 0
            oe_adj = oe - sbc_abs
            oe_data.append({"year": yr, "oe": oe, "oe_adj": oe_adj})
            oe_rows.append([yr, _fmt_val(ni), _fmt_val(da_abs), _fmt_val(cx_abs),
                            _fmt_val(oe), _fmt_val(oe_adj), _fmt_val(sbc_abs)])
        else:
            oe_rows.append([yr, _fmt_val(ni), _fmt_val(da), _fmt_val(cx), "—", "—", "—"])

    if oe_rows:
        lines.append(_build_table(oe_headers, oe_rows, ["l"] + ["r"] * 6))
    lines.append("")

    # Payout ratio by year
    lines.append("**Payout Ratio by Year**:")
    lines.append("")
    pr_headers = ["Year", "Dividends", "Net Income", "Payout Ratio"]
    pr_rows = []
    pr_values = []

    for yr in year_cols:
        ni = next((v for y, v in ni_series if y == yr), None)
        div = next((v for y, v in div_series if y == yr), None)

        if ni is not None and ni > 0 and div is not None:
            div_abs = abs(div)
            pr = (div_abs / ni) * 100
            pr_values.append(pr)
            pr_rows.append([yr, _fmt_val(div_abs), _fmt_val(ni), _fmt_val(pr, "%")])
        else:
            pr_rows.append([yr, _fmt_val(div if div else None), _fmt_val(ni), "—"])

    if pr_rows:
        lines.append(_build_table(pr_headers, pr_rows, ["l", "r", "r", "r"]))
    lines.append("")

    # Summary stats
    if pr_values:
        pr_mean = statistics.mean(pr_values)
        pr_std = statistics.stdev(pr_values) if len(pr_values) > 1 else 0
        lines.append(f"- **Payout Ratio Mean (recent {len(pr_values)}yr)**: {pr_mean:.2f}%")
        lines.append(f"- **Payout Ratio Std Dev**: {pr_std:.2f}%")
        lines.append(f"- **Payout Ratio Range**: {min(pr_values):.2f}% — {max(pr_values):.2f}%")
    else:
        lines.append("- **Payout Ratio**: Data unavailable")

    if oe_data:
        oe_vals = [d["oe"] for d in oe_data]
        oe_adj_vals = [d["oe_adj"] for d in oe_data]
        lines.append(f"- **Latest OE**: {_fmt_val(oe_vals[-1])}")
        lines.append(f"- **Latest OE (ex-SBC)**: {_fmt_val(oe_adj_vals[-1])}")

    return "\n".join(lines)


def _section_16_3(sections: Dict) -> str:
    """§16.3 True Cash Revenue — Revenue − ΔAR, collection ratio."""
    income_rows = sections.get("income", {}).get("rows", [])
    bs_rows = sections.get("balance", {}).get("rows", [])

    rev_series = _get_series(income_rows, "revenue")
    ar_series = _get_series(bs_rows, "accounts_receivable")

    lines = ["### §16.3 True Cash Revenue", ""]

    headers = ["Year", "Revenue", "AR", "ΔAR", "True Cash Rev", "Collection Ratio"]
    rows_out = []

    year_cols = [yr for yr, _ in rev_series] if rev_series else []

    prev_ar = None
    for yr in year_cols:
        rev = next((v for y, v in rev_series if y == yr), None)
        ar = next((v for y, v in ar_series if y == yr), None)

        if rev is not None and ar is not None and prev_ar is not None:
            delta_ar = ar - prev_ar
            # True Cash Revenue = Revenue − max(0, ΔAR)
            tcr = rev - max(0, delta_ar)
            cr = tcr / rev if rev != 0 else None
            rows_out.append([yr, _fmt_val(rev), _fmt_val(ar), _fmt_val(delta_ar),
                             _fmt_val(tcr), _fmt_val(cr * 100, "%") if cr is not None else "—"])
        elif rev is not None:
            rows_out.append([yr, _fmt_val(rev), _fmt_val(ar), "—", "—", "—"])

        prev_ar = ar

    if rows_out:
        lines.append(_build_table(headers, rows_out, ["l"] + ["r"] * 5))
    else:
        lines.append("Insufficient data for True Cash Revenue calculation.")

    return "\n".join(lines)


def _section_16_4(sections: Dict) -> str:
    """§16.4 Operating Outflows Reconstruction — COGS + Tax + Interest − ΔAP."""
    income_rows = sections.get("income", {}).get("rows", [])
    bs_rows = sections.get("balance", {}).get("rows", [])

    cogs_series = _get_series(income_rows, "cost_of_revenue")
    tax_series = _get_series(income_rows, "income_tax")
    int_series = _get_series(income_rows, "interest_expense")
    ap_series = _get_series(bs_rows, "accounts_payable")
    dta_series = _get_series(bs_rows, "deferred_tax_assets")
    dtl_series = _get_series(bs_rows, "deferred_tax_liabilities")

    lines = ["### §16.4 Operating Outflows Reconstruction", ""]

    headers = ["Year", "COGS", "Tax Paid", "Interest", "ΔAP Adj", "Total W"]
    rows_out = []

    year_cols = [yr for yr, _ in cogs_series] if cogs_series else [yr for yr, _ in tax_series]

    prev_ap = None
    prev_dta = None
    prev_dtl = None

    for yr in year_cols:
        cogs = next((v for y, v in cogs_series if y == yr), None)
        tax = next((v for y, v in tax_series if y == yr), None)
        interest = next((v for y, v in int_series if y == yr), None)
        ap = next((v for y, v in ap_series if y == yr), None)
        dta = next((v for y, v in dta_series if y == yr), None)
        dtl = next((v for y, v in dtl_series if y == yr), None)

        # Cash tax adjustment: reported tax − Δ(DTL − DTA)
        cash_tax = tax
        if tax is not None and prev_dta is not None and prev_dtl is not None and dta is not None and dtl is not None:
            delta_net_dtl = (dtl - dta) - (prev_dtl - prev_dta)
            cash_tax = abs(tax) - delta_net_dtl
        elif tax is not None:
            cash_tax = abs(tax)

        # ΔAP adjustment
        delta_ap_adj = 0
        if ap is not None and prev_ap is not None:
            delta_ap_adj = ap - prev_ap  # Positive ΔAP reduces outflow

        cogs_abs = abs(cogs) if cogs is not None else None
        int_abs = abs(interest) if interest is not None else 0
        cash_tax_abs = abs(cash_tax) if cash_tax is not None else 0

        if cogs_abs is not None:
            total_w = cogs_abs + cash_tax_abs + int_abs - delta_ap_adj
            rows_out.append([yr, _fmt_val(cogs_abs), _fmt_val(cash_tax_abs),
                             _fmt_val(int_abs), _fmt_val(delta_ap_adj), _fmt_val(total_w)])
        else:
            rows_out.append([yr, "—", _fmt_val(cash_tax_abs), _fmt_val(int_abs),
                             _fmt_val(delta_ap_adj), "—"])

        prev_ap = ap
        prev_dta = dta
        prev_dtl = dtl

    if rows_out:
        lines.append(_build_table(headers, rows_out, ["l"] + ["r"] * 5))
    else:
        lines.append("Insufficient data for operating outflow reconstruction.")

    return "\n".join(lines)


def _section_16_5(sections: Dict) -> str:
    """§16.5 Base Surplus — OCF − Capex, AA average, Revenue CV, λ."""
    income_rows = sections.get("income", {}).get("rows", [])
    cf_rows = sections.get("cashflow", {}).get("rows", [])

    rev_series = _get_series(income_rows, "revenue")
    ocf_series = _get_series(cf_rows, "ocf")
    capex_series = _get_series(cf_rows, "capex")
    sbc_series = _get_series(cf_rows, "sbc")
    buyback_series = _get_series(cf_rows, "buybacks")
    div_series = _get_series(cf_rows, "dividends")

    lines = ["### §16.5 Base Surplus & AA", ""]

    headers = ["Year", "OCF", "Capex", "Surplus", "Buybacks", "Dividends", "SBC", "AA"]
    rows_out = []
    surplus_vals = []
    aa_vals = []
    rev_vals = []

    year_cols = [yr for yr, _ in ocf_series] if ocf_series else []

    for yr in year_cols:
        ocf = next((v for y, v in ocf_series if y == yr), None)
        cx = next((v for y, v in capex_series if y == yr), None)
        sbc = next((v for y, v in sbc_series if y == yr), None)
        bb = next((v for y, v in buyback_series if y == yr), None)
        div = next((v for y, v in div_series if y == yr), None)
        rev = next((v for y, v in rev_series if y == yr), None)

        if ocf is not None and cx is not None:
            cx_abs = abs(cx)
            surplus = ocf - cx_abs
            surplus_vals.append(surplus)

            sbc_abs = abs(sbc) if sbc else 0
            bb_abs = abs(bb) if bb else 0
            div_abs = abs(div) if div else 0

            # AA = OCF - Capex + Buybacks - Dividends - SBC
            aa = surplus + bb_abs - div_abs - sbc_abs
            aa_vals.append(aa)

            if rev is not None:
                rev_vals.append(rev)

            rows_out.append([yr, _fmt_val(ocf), _fmt_val(cx_abs), _fmt_val(surplus),
                             _fmt_val(bb_abs), _fmt_val(div_abs), _fmt_val(sbc_abs),
                             _fmt_val(aa)])
        else:
            rows_out.append([yr, _fmt_val(ocf), _fmt_val(cx), "—", "—", "—", "—", "—"])

    if rows_out:
        lines.append(_build_table(headers, rows_out, ["l"] + ["r"] * 7))
    lines.append("")

    # Summary stats
    if surplus_vals:
        lines.append(f"- **Average Surplus (OCF − Capex)**: {_fmt_val(statistics.mean(surplus_vals))}")
    if aa_vals:
        lines.append(f"- **Average AA**: {_fmt_val(statistics.mean(aa_vals))}")
        if len(aa_vals) >= 2:
            lines.append(f"- **AA Std Dev**: {_fmt_val(statistics.stdev(aa_vals))}")
    if rev_vals and len(rev_vals) >= 2:
        rev_mean = statistics.mean(rev_vals)
        rev_std = statistics.stdev(rev_vals)
        cv = (rev_std / rev_mean * 100) if rev_mean != 0 else None
        lines.append(f"- **Revenue CV**: {_fmt_val(cv, '%') if cv is not None else '—'}")

    # λ (operating leverage) = ΔSurplus / ΔRevenue
    if len(surplus_vals) >= 2 and len(rev_vals) >= 2:
        delta_surplus = surplus_vals[-1] - surplus_vals[0]
        delta_rev = rev_vals[-1] - rev_vals[0]
        if delta_rev != 0:
            lam = delta_surplus / delta_rev
            lines.append(f"- **λ (Operating Leverage)**: {lam:.4f}")
            lines.append(f"  - Interpretation: ${lam:.2f} surplus change per $1 revenue change")

    return "\n".join(lines)


def _section_16_6(content: str) -> str:
    """§16.6 Price Position — percentiles from §10 Annual Price Summary."""
    price_rows = _extract_price_summary(content)

    lines = ["### §16.6 Price Position", ""]

    if not price_rows:
        lines.append("No Annual Price Summary data available in §10.")
        return "\n".join(lines)

    # Collect all High/Low values
    highs = []
    lows = []
    for row in price_rows:
        h = row.get("High")
        lo = row.get("Low")
        if isinstance(h, (int, float)):
            highs.append(h)
        if isinstance(lo, (int, float)):
            lows.append(lo)

    if not highs or not lows:
        lines.append("Could not parse price data from Annual Price Summary.")
        return "\n".join(lines)

    # Build combined price range for percentile calculation
    all_prices = sorted(highs + lows)

    def _percentile(data: list, p: float) -> float:
        """Simple linear percentile."""
        n = len(data)
        if n == 0:
            return 0
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= n:
            return data[-1]
        return data[f] + (k - f) * (data[c] - data[f])

    p10 = _percentile(all_prices, 10)
    p25 = _percentile(all_prices, 25)
    p50 = _percentile(all_prices, 50)
    p75 = _percentile(all_prices, 75)
    p90 = _percentile(all_prices, 90)

    lines.append(f"Based on {len(price_rows)} years of annual High/Low data:")
    lines.append("")
    lines.append("| Percentile | Price |")
    lines.append("|:----------:|------:|")
    lines.append(f"| P10 | ${p10:.2f} |")
    lines.append(f"| P25 | ${p25:.2f} |")
    lines.append(f"| P50 (Median) | ${p50:.2f} |")
    lines.append(f"| P75 | ${p75:.2f} |")
    lines.append(f"| P90 | ${p90:.2f} |")
    lines.append("")
    lines.append(f"- **10-Year High**: ${max(highs):.2f}")
    lines.append(f"- **10-Year Low**: ${min(lows):.2f}")

    # Current price position (if available from latest close)
    closes = []
    for row in price_rows:
        c = row.get("Close")
        if isinstance(c, (int, float)):
            closes.append(c)
    if closes:
        latest_close = closes[-1]
        # Calculate what percentile the latest close falls at
        below = sum(1 for p in all_prices if p <= latest_close)
        pct_rank = (below / len(all_prices)) * 100
        lines.append(f"- **Latest Annual Close**: ${latest_close:.2f} (≈P{pct_rank:.0f})")

    return "\n".join(lines)


def _section_16_7(sections: Dict, market_data: Dict[str, float]) -> str:
    """§16.7 Valuation Dashboard — EV/EBITDA, Net Debt/EBITDA, yields."""
    income_rows = sections.get("income", {}).get("rows", [])
    bs_rows = sections.get("balance", {}).get("rows", [])
    cf_rows = sections.get("cashflow", {}).get("rows", [])

    lines = ["### §16.7 Valuation Dashboard", ""]

    mcap = market_data.get("market_cap")
    price = market_data.get("price")

    # Latest values
    ebitda_s = _get_series(income_rows, "ebitda")
    ebitda = _latest(ebitda_s)

    ni_s = _get_series(income_rows, "net_income")
    rev_s = _get_series(income_rows, "revenue")

    fcf_s = _get_series(cf_rows, "fcf")
    fcf = _latest(fcf_s)
    ocf_s = _get_series(cf_rows, "ocf")
    capex_s = _get_series(cf_rows, "capex")

    # Compute FCF from OCF - Capex if direct FCF unavailable
    if fcf is None:
        ocf_val = _latest(ocf_s)
        capex_val = _latest(capex_s)
        if ocf_val is not None and capex_val is not None:
            fcf = ocf_val - abs(capex_val)

    bb_s = _get_series(cf_rows, "buybacks")
    div_s = _get_series(cf_rows, "dividends")

    # Debt
    lt_debt_s = _get_series(bs_rows, "long_term_debt")
    st_debt_s = _get_series(bs_rows, "short_term_debt")
    cash_s = _get_series(bs_rows, "cash")
    equity_s = _get_series(bs_rows, "equity")
    goodwill_s = _get_series(bs_rows, "goodwill")

    lt_debt = _latest(lt_debt_s) or 0
    st_debt = _latest(st_debt_s) or 0
    total_debt = lt_debt + st_debt
    cash = _latest(cash_s) or 0
    net_debt = total_debt - cash
    equity = _latest(equity_s)
    goodwill = _latest(goodwill_s) or 0

    # Enterprise Value
    ev = None
    if mcap is not None:
        ev = mcap + net_debt

    # Metrics table
    metrics = []

    if mcap is not None:
        metrics.append(("Market Cap", f"${mcap:,.0f}M"))
    metrics.append(("Total Debt", f"${total_debt:,.0f}M"))
    metrics.append(("Cash & Equivalents", f"${cash:,.0f}M"))
    metrics.append(("Net Debt", f"${net_debt:,.0f}M"))
    if ev is not None:
        metrics.append(("Enterprise Value (EV)", f"${ev:,.0f}M"))

    # EV/EBITDA
    if ev is not None and ebitda is not None and ebitda > 0:
        metrics.append(("EV/EBITDA", f"{ev / ebitda:.2f}x"))
    else:
        metrics.append(("EV/EBITDA", "—"))

    # Net Debt / EBITDA
    if ebitda is not None and ebitda > 0:
        metrics.append(("Net Debt/EBITDA", f"{net_debt / ebitda:.2f}x"))
    else:
        metrics.append(("Net Debt/EBITDA", "—"))

    # P/E from market data
    pe = market_data.get("pe_ratio")
    if pe is not None:
        metrics.append(("P/E Ratio", f"{pe:.2f}x"))

    # P/B from market data
    pb = market_data.get("pb_ratio")
    if pb is not None:
        metrics.append(("P/B Ratio", f"{pb:.2f}x"))

    # FCF Yield
    if mcap and fcf is not None and mcap > 0:
        fcf_yield = (fcf / mcap) * 100
        metrics.append(("FCF Yield", f"{fcf_yield:.2f}%"))
    else:
        metrics.append(("FCF Yield", "—"))

    # Shareholder Yield = (Dividends + Buybacks) / Market Cap
    div_val = _latest(div_s)
    bb_val = _latest(bb_s)
    if mcap and mcap > 0:
        div_abs = abs(div_val) if div_val else 0
        bb_abs = abs(bb_val) if bb_val else 0
        sh_yield = ((div_abs + bb_abs) / mcap) * 100
        metrics.append(("Shareholder Yield", f"{sh_yield:.2f}%"))
        metrics.append(("  - Dividend Component", f"{(div_abs / mcap) * 100:.2f}%"))
        metrics.append(("  - Buyback Component", f"{(bb_abs / mcap) * 100:.2f}%"))
    else:
        metrics.append(("Shareholder Yield", "—"))

    # Goodwill / Equity
    if equity is not None and equity > 0:
        gw_eq = (goodwill / equity) * 100
        metrics.append(("Goodwill / Equity", f"{gw_eq:.2f}%"))

    lines.append("| Metric | Value |")
    lines.append("|:-------|------:|")
    for label, val in metrics:
        lines.append(f"| {label} | {val} |")

    return "\n".join(lines)


# ===================================================================
# Table formatter
# ===================================================================

def _build_table(headers: List[str], rows: List[List[str]], alignments: List[str]) -> str:
    """Build a simple markdown table."""
    align_map = {"l": ":---", "r": "---:", "c": ":---:"}
    sep = [align_map.get(a, "---") for a in alignments]

    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(sep) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


# ===================================================================
# Main
# ===================================================================

def calculate_factor_inputs(input_file: Path, stock_code: str) -> str:
    """Calculate all factor inputs and return markdown string."""
    if not input_file.exists():
        raise FileNotFoundError(f"Data pack not found: {input_file}")

    content = input_file.read_text(encoding="utf-8")
    sections = _extract_sections(content)
    market_data = _extract_market_data(content)

    parts = []
    parts.append(f"# {stock_code} — Factor Inputs (Pre-Computed)")
    parts.append("")
    parts.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    parts.append(f"**Source**: {input_file.name}")
    parts.append(f"**Currency**: {DEFAULT_CONFIG.currency}")
    parts.append(f"**Unit**: {DEFAULT_CONFIG.amount_unit} {DEFAULT_CONFIG.currency}")
    parts.append("")
    parts.append("---")
    parts.append("")

    # Build each subsection
    parts.append(_section_16_1(sections))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(_section_16_2(sections))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(_section_16_3(sections))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(_section_16_4(sections))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(_section_16_5(sections))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(_section_16_6(content))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(_section_16_7(sections, market_data))
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("*US Equity Quality Yield Strategy | Factor Inputs Calculator*")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="US Equity Quality Yield — Factor Inputs Calculator"
    )
    parser.add_argument("--input", required=True, help="Path to data_pack.md")
    parser.add_argument("--code", required=True, help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--output", default=None, help="Output file path (default: output/{CODE}/{CODE}_factor_inputs.md)")
    args = parser.parse_args()

    input_file = Path(args.input)
    code = args.code.upper()

    if args.output:
        output_file = Path(args.output)
    else:
        output_dir = Path(get_output_dir(code))
        output_file = output_dir / f"{code}_factor_inputs.md"

    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = calculate_factor_inputs(input_file, code)
        output_file.write_text(result, encoding="utf-8")
        print(f"Factor inputs written to: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
