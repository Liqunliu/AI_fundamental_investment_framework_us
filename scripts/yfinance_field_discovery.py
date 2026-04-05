#!/usr/bin/env python3
"""yFinance Field Discovery Tool.

Analogous to Bloomberg's --field-check mode.  Fetches all available data from
yfinance for a given ticker and reports which fields the yfinance_collector
actually uses, which are merely available, and which come back empty.

Usage:
    python3 scripts/yfinance_field_discovery.py --ticker AAPL
    python3 scripts/yfinance_field_discovery.py --ticker AAPL --format json
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# SSL / curl_cffi patch (same pattern as yfinance_collector.py)
# ---------------------------------------------------------------------------
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["PYTHONHTTPSVERIFY"] = "0"

try:
    from curl_cffi import requests as curl_requests

    _orig_curl_request = curl_requests.Session.request

    def _patched_request(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        return _orig_curl_request(self, *args, **kwargs)

    curl_requests.Session.request = _patched_request
except Exception:
    pass

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance is not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Fields the collector actually uses
# ---------------------------------------------------------------------------

USED_INFO_FIELDS: set[str] = {
    "longName", "exchange", "currency", "country", "sector", "industry",
    "fullTimeEmployees", "website",
    "longBusinessSummary",
    "currentPrice", "regularMarketPrice", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "fiftyDayAverage", "twoHundredDayAverage",
    "marketCap", "enterpriseValue",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "enterpriseToEbitda", "enterpriseToRevenue",
    "dividendYield", "dividendRate", "payoutRatio", "beta",
    "returnOnEquity", "returnOnAssets",
    "grossMargins", "operatingMargins", "profitMargins",
    "currentRatio", "quickRatio", "debtToEquity",
    "revenueGrowth", "earningsGrowth",
    "bookValue", "sharesOutstanding", "floatShares",
}

USED_INCOME_ROWS: set[str] = {"Total Revenue", "Net Income", "Net Income Common Stockholders"}
USED_BALANCE_ROWS: set[str] = {"Goodwill"}
USED_CASHFLOW_ROWS: set[str] = {"Depreciation And Amortization", "Depreciation"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_empty(val) -> bool:
    """Return True if the value is None, NaN, or an empty string."""
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False


def _truncate(val, maxlen: int = 60) -> str:
    """Return a displayable string, truncated if needed."""
    s = str(val)
    if len(s) > maxlen:
        return s[:maxlen] + "..."
    return s


def _classify_info(info: dict) -> list[dict]:
    """Classify each key in the info dict."""
    results = []
    for key in sorted(info.keys()):
        val = info[key]
        used = key in USED_INFO_FIELDS
        empty = _is_empty(val)
        results.append({
            "field": key,
            "value": None if empty else val,
            "display": "None" if empty else _truncate(val),
            "used": used,
            "empty": empty,
        })
    return results


def _classify_statement(df: pd.DataFrame, used_rows: set[str], name: str) -> list[dict]:
    """Classify rows in a financial statement DataFrame."""
    results = []
    if df is None or df.empty:
        return results
    for row in df.index:
        used = row in used_rows
        # Check if all values in the row are NaN/None
        row_data = df.loc[row]
        all_empty = row_data.isna().all()
        sample = None if all_empty else _truncate(row_data.dropna().iloc[0]) if not row_data.dropna().empty else None
        results.append({
            "field": row,
            "sample": sample,
            "used": used,
            "empty": bool(all_empty),
        })
    return results


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------

def _print_text(ticker_str: str, info_items: list[dict], sections: dict):
    """Print human-readable field report."""
    print(f"\n=== {ticker_str} Field Discovery ===\n")

    # --- Info dict ---
    used_count = sum(1 for i in info_items if i["used"])
    empty_count = sum(1 for i in info_items if i["empty"])
    print(f"INFO DICT ({len(info_items)} fields, {used_count} used by collector, {empty_count} empty):")
    for item in info_items:
        if item["used"]:
            marker = "\u2713"
            tag = "[USED by collector]"
        elif item["empty"]:
            marker = "\u2717"
            tag = "[empty]"
        else:
            marker = "\u00b7"
            tag = "[available, not used]"
        print(f"  {marker} {item['field']:40s} = {item['display']:30s} {tag}")
    print()

    # --- Financial statements ---
    for label, (items, shape_str) in sections.items():
        used_count = sum(1 for i in items if i["used"])
        empty_count = sum(1 for i in items if i["empty"])
        print(f"{label} ({shape_str}, {used_count} used, {empty_count} empty):")
        if not items:
            print("  (no data available)")
        for item in items:
            if item["used"]:
                marker = "\u2713"
                tag = "[USED]"
            elif item["empty"]:
                marker = "\u2717"
                tag = "[empty]"
            else:
                marker = "\u00b7"
                tag = "[available, not used]"
            sample_str = f"  sample: {item['sample']}" if item.get("sample") else ""
            print(f"  {marker} {item['field']:45s} {tag}{sample_str}")
        print()


def _print_json(ticker_str: str, info_items: list[dict], sections: dict, dividends_info: dict):
    """Print JSON output."""

    def _serialisable(v):
        """Make a value JSON-safe."""
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v) if not np.isnan(v) else None
        if isinstance(v, (np.bool_,)):
            return bool(v)
        if isinstance(v, pd.Timestamp):
            return str(v)
        return v

    output: dict = {"ticker": ticker_str}

    output["info"] = [
        {
            "field": i["field"],
            "value": _serialisable(i["value"]),
            "used": i["used"],
            "empty": i["empty"],
        }
        for i in info_items
    ]

    for label, (items, shape_str) in sections.items():
        key = label.lower().replace(" ", "_")
        output[key] = {
            "shape": shape_str,
            "fields": [
                {
                    "field": i["field"],
                    "sample": _serialisable(i.get("sample")),
                    "used": i["used"],
                    "empty": i["empty"],
                }
                for i in items
            ],
        }

    output["dividends"] = {
        "count": dividends_info.get("count", 0),
        "latest_date": dividends_info.get("latest_date"),
        "latest_value": dividends_info.get("latest_value"),
        "earliest_date": dividends_info.get("earliest_date"),
    }

    print(json.dumps(output, indent=2, default=str))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="yFinance field discovery tool")
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g. AAPL)")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    ticker_str = args.ticker.upper().strip()
    print(f"Fetching data for {ticker_str} ...", file=sys.stderr)

    ticker = yf.Ticker(ticker_str)

    # --- Info dict ---
    try:
        info = ticker.info or {}
    except Exception as exc:
        print(f"WARNING: Could not fetch info: {exc}", file=sys.stderr)
        info = {}
    info_items = _classify_info(info)

    # --- Financial statements ---
    stmt_configs = [
        ("FINANCIALS (income statement)", ticker, "financials", USED_INCOME_ROWS),
        ("BALANCE SHEET", ticker, "balance_sheet", USED_BALANCE_ROWS),
        ("CASH FLOW", ticker, "cashflow", USED_CASHFLOW_ROWS),
    ]

    sections: dict[str, tuple[list[dict], str]] = {}
    for label, tkr, attr, used_set in stmt_configs:
        try:
            df = getattr(tkr, attr)
            if df is not None and not df.empty:
                shape_str = f"{df.shape[0]} rows x {df.shape[1]} cols"
                items = _classify_statement(df, used_set, label)
            else:
                shape_str = "no data"
                items = []
        except Exception as exc:
            print(f"WARNING: {label} fetch failed: {exc}", file=sys.stderr)
            shape_str = "fetch failed"
            items = []
        sections[label] = (items, shape_str)

    # --- Dividends ---
    dividends_info: dict = {}
    try:
        divs = ticker.dividends
        if divs is not None and len(divs) > 0:
            dividends_info["count"] = len(divs)
            dividends_info["latest_date"] = str(divs.index[-1].date())
            dividends_info["latest_value"] = round(float(divs.iloc[-1]), 4)
            dividends_info["earliest_date"] = str(divs.index[0].date())
        else:
            dividends_info["count"] = 0
    except Exception as exc:
        print(f"WARNING: Dividends fetch failed: {exc}", file=sys.stderr)
        dividends_info["count"] = 0

    # --- Output ---
    if args.format == "json":
        _print_json(ticker_str, info_items, sections, dividends_info)
    else:
        _print_text(ticker_str, info_items, sections)

        # Dividends summary at the end
        if dividends_info.get("count", 0) > 0:
            print(f"DIVIDENDS ({dividends_info['count']} entries):")
            print(f"  Latest:   {dividends_info['latest_date']}  ${dividends_info['latest_value']}")
            print(f"  Earliest: {dividends_info['earliest_date']}")
            print(f"  Count:    {dividends_info['count']} entries")
        else:
            print("DIVIDENDS: no dividend data available")
        print()


if __name__ == "__main__":
    main()
