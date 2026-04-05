#!/usr/bin/env python3
"""Cycle Indicator Collector for Cyclical Trough Strategy.

Fetches sector-level indicators (commodities, indices) and macro data
via yfinance, then appends them to a ticker's data pack as a
``cycle_data_pack.md`` file.

Indicators collected:
  - Oil (CL=F): Crude oil futures
  - Semiconductors (^SOX): Philadelphia Semiconductor Index
  - Shipping: Baltic Dry Index proxy (BDRY ETF)
  - Copper (HG=F): Copper futures
  - Macro: 10Y yield (^TNX), 2Y yield, credit spreads (HYG vs LQD)

Usage:
    python3 scripts/cycle_indicator_collector.py --ticker PBR
    python3 scripts/cycle_indicator_collector.py --ticker QCOM --years 5
    python3 scripts/cycle_indicator_collector.py --all-indicators
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from cycle_config import CYCLE_CONFIG, get_cycle_output_dir  # noqa: E402
from format_utils import format_table  # noqa: E402

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: yfinance, pandas, numpy required. pip install yfinance pandas numpy",
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Sector indicator definitions
# ---------------------------------------------------------------------------
SECTOR_INDICATORS = {
    "oil": {
        "symbol": "CL=F",
        "name": "WTI Crude Oil Futures",
        "unit": "$/barrel",
        "sectors": ["Energy"],
        "industries": ["Oil & Gas", "Exploration", "Refining", "Integrated", "Midstream"],
    },
    "semis": {
        "symbol": "^SOX",
        "name": "Philadelphia Semiconductor Index",
        "unit": "index",
        "sectors": ["Technology"],
        "industries": ["Semiconductor"],
    },
    "shipping": {
        "symbol": "BDRY",
        "name": "Breakwave Dry Bulk Shipping ETF (BDI proxy)",
        "unit": "$/share",
        "sectors": ["Industrials"],
        "industries": ["Shipping", "Marine"],
    },
    "copper": {
        "symbol": "HG=F",
        "name": "Copper Futures",
        "unit": "$/lb",
        "sectors": ["Basic Materials"],
        "industries": ["Copper", "Mining", "Industrial Metals"],
    },
    "steel": {
        "symbol": "SLX",
        "name": "VanEck Steel ETF",
        "unit": "$/share",
        "sectors": ["Basic Materials"],
        "industries": ["Steel"],
    },
}

MACRO_INDICATORS = {
    "yield_10y": {
        "symbol": "^TNX",
        "name": "US 10-Year Treasury Yield",
        "unit": "%",
    },
    "yield_2y": {
        "symbol": "^IRX",
        "name": "US 13-Week Treasury Bill Rate",
        "unit": "%",
    },
    "credit_ig": {
        "symbol": "LQD",
        "name": "iShares Investment Grade Bond ETF",
        "unit": "$/share",
    },
    "credit_hy": {
        "symbol": "HYG",
        "name": "iShares High Yield Bond ETF",
        "unit": "$/share",
    },
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_indicator_history(
    symbol: str,
    years: int = 5,
) -> Optional[pd.DataFrame]:
    """Fetch weekly price history for an indicator symbol."""
    try:
        ticker = yf.Ticker(symbol)
        end = datetime.now()
        start = end - timedelta(days=years * 365)
        hist = ticker.history(start=start, end=end, interval="1wk")
        if hist.empty:
            return None
        return hist
    except Exception as e:
        print(f"  Warning: Failed to fetch {symbol}: {e}", file=sys.stderr)
        return None


def compute_percentile(hist: pd.DataFrame, column: str = "Close") -> Dict[str, float]:
    """Compute current price percentile within historical range."""
    if hist is None or hist.empty:
        return {}

    closes = hist[column].dropna()
    if closes.empty:
        return {}

    current = closes.iloc[-1]
    low = closes.min()
    high = closes.max()
    rng = high - low

    percentile = ((current - low) / rng * 100.0) if rng > 0 else 50.0

    return {
        "current": float(current),
        "low_5y": float(low),
        "high_5y": float(high),
        "percentile": float(percentile),
        "median": float(closes.median()),
        "mean": float(closes.mean()),
    }


def compute_trend(hist: pd.DataFrame, column: str = "Close") -> Dict[str, Any]:
    """Compute trend metrics: 3M change, 6M change, 12M change."""
    if hist is None or hist.empty:
        return {}

    closes = hist[column].dropna()
    if len(closes) < 2:
        return {}

    current = closes.iloc[-1]
    result = {"current": float(current)}

    for label, weeks in [("3m", 13), ("6m", 26), ("12m", 52)]:
        if len(closes) > weeks:
            past = closes.iloc[-weeks - 1]
            change_pct = ((current - past) / past) * 100.0
            result[f"change_{label}"] = round(change_pct, 2)

    return result


def detect_sector_for_ticker(ticker_symbol: str) -> Optional[str]:
    """Auto-detect which sector indicator is relevant for a stock."""
    try:
        info = yf.Ticker(ticker_symbol).info
        sector = info.get("sector", "")
        industry = info.get("industry", "")
    except Exception:
        return None

    for key, ind_def in SECTOR_INDICATORS.items():
        if sector in ind_def["sectors"]:
            for kw in ind_def["industries"]:
                if kw.lower() in industry.lower():
                    return key
        # Also check if sector matches directly
        if sector in ind_def["sectors"]:
            return key

    return None


# ---------------------------------------------------------------------------
# Collect all indicators for a ticker
# ---------------------------------------------------------------------------

def collect_cycle_indicators(
    ticker_symbol: str,
    years: int = 5,
) -> Dict[str, Any]:
    """Collect sector + macro indicators relevant to a stock.

    Returns a dict with:
      - ticker: str
      - detected_sector: str
      - sector_indicator: dict (percentile, trend)
      - macro_indicators: dict
      - all_sector_indicators: dict (for cross-comparison)
    """
    result: Dict[str, Any] = {
        "ticker": ticker_symbol,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Detect relevant sector
    detected = detect_sector_for_ticker(ticker_symbol)
    result["detected_sector"] = detected

    # Fetch stock price percentile
    stock_hist = fetch_indicator_history(ticker_symbol, years)
    if stock_hist is not None:
        result["stock_price"] = compute_percentile(stock_hist)
        result["stock_trend"] = compute_trend(stock_hist)

    # Fetch primary sector indicator
    if detected and detected in SECTOR_INDICATORS:
        ind = SECTOR_INDICATORS[detected]
        hist = fetch_indicator_history(ind["symbol"], years)
        if hist is not None:
            result["sector_indicator"] = {
                "name": ind["name"],
                "symbol": ind["symbol"],
                "percentile": compute_percentile(hist),
                "trend": compute_trend(hist),
            }

    # Fetch all sector indicators for cross-comparison
    result["all_sector_indicators"] = {}
    for key, ind in SECTOR_INDICATORS.items():
        hist = fetch_indicator_history(ind["symbol"], years)
        if hist is not None:
            result["all_sector_indicators"][key] = {
                "name": ind["name"],
                "percentile": compute_percentile(hist),
                "trend": compute_trend(hist),
            }

    # Fetch macro indicators
    result["macro_indicators"] = {}
    for key, ind in MACRO_INDICATORS.items():
        hist = fetch_indicator_history(ind["symbol"], years)
        if hist is not None:
            result["macro_indicators"][key] = {
                "name": ind["name"],
                "percentile": compute_percentile(hist),
                "trend": compute_trend(hist),
            }

    # Compute yield curve spread (10Y - 2Y proxy)
    macro = result["macro_indicators"]
    if "yield_10y" in macro and "yield_2y" in macro:
        y10 = macro["yield_10y"]["percentile"].get("current", 0)
        y2 = macro["yield_2y"]["percentile"].get("current", 0)
        result["yield_curve_spread"] = round(y10 - y2, 4)

    # Credit spread proxy: HYG vs LQD ratio
    if "credit_hy" in macro and "credit_ig" in macro:
        hy = macro["credit_hy"]["percentile"].get("current", 1)
        ig = macro["credit_ig"]["percentile"].get("current", 1)
        if ig > 0:
            result["credit_spread_ratio"] = round(hy / ig, 4)

    return result


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

def format_cycle_data_pack(data: Dict[str, Any]) -> str:
    """Generate markdown report of cycle indicators."""
    L: List[str] = []

    ticker = data.get("ticker", "UNKNOWN")
    L.append(f"# {ticker} -- Cycle Indicator Data Pack")
    L.append("")
    L.append(f"**Generated**: {data.get('timestamp', 'N/A')}")
    L.append(f"**Detected Sector**: {data.get('detected_sector', 'Unknown')}")
    L.append("")
    L.append("---")
    L.append("")

    # Stock price position
    if "stock_price" in data:
        sp = data["stock_price"]
        L.append("## Stock Price Position")
        L.append("")
        L.append(f"- **Current Price**: ${sp.get('current', 0):.2f}")
        L.append(f"- **5Y Low**: ${sp.get('low_5y', 0):.2f}")
        L.append(f"- **5Y High**: ${sp.get('high_5y', 0):.2f}")
        L.append(f"- **5Y Percentile**: {sp.get('percentile', 0):.1f}%")
        L.append(f"- **5Y Median**: ${sp.get('median', 0):.2f}")
        L.append("")

    if "stock_trend" in data:
        st = data["stock_trend"]
        L.append("### Price Trend")
        L.append("")
        for period in ["3m", "6m", "12m"]:
            key = f"change_{period}"
            if key in st:
                L.append(f"- **{period.upper()} Change**: {st[key]:+.2f}%")
        L.append("")

    # Primary sector indicator
    if "sector_indicator" in data:
        si = data["sector_indicator"]
        L.append("## Primary Sector Indicator")
        L.append("")
        L.append(f"**{si['name']}** ({si['symbol']})")
        L.append("")
        pct = si.get("percentile", {})
        L.append(f"- **Current**: {pct.get('current', 0):.2f}")
        L.append(f"- **5Y Low**: {pct.get('low_5y', 0):.2f}")
        L.append(f"- **5Y High**: {pct.get('high_5y', 0):.2f}")
        L.append(f"- **5Y Percentile**: {pct.get('percentile', 0):.1f}%")
        L.append("")

        trend = si.get("trend", {})
        for period in ["3m", "6m", "12m"]:
            key = f"change_{period}"
            if key in trend:
                L.append(f"- **{period.upper()} Change**: {trend[key]:+.2f}%")
        L.append("")

    # All sector indicators comparison
    all_si = data.get("all_sector_indicators", {})
    if all_si:
        L.append("## Sector Indicators Comparison")
        L.append("")
        L.append("| Indicator | Current | 5Y Low | 5Y High | Percentile | 3M Chg | 12M Chg |")
        L.append("|-----------|--------:|-------:|--------:|-----------:|-------:|--------:|")
        for key, si in all_si.items():
            name = SECTOR_INDICATORS.get(key, {}).get("name", key)
            short_name = name[:25]
            pct = si.get("percentile", {})
            trend = si.get("trend", {})
            L.append(
                f"| {short_name} "
                f"| {pct.get('current', 0):.2f} "
                f"| {pct.get('low_5y', 0):.2f} "
                f"| {pct.get('high_5y', 0):.2f} "
                f"| {pct.get('percentile', 0):.1f}% "
                f"| {trend.get('change_3m', 0):+.1f}% "
                f"| {trend.get('change_12m', 0):+.1f}% |"
            )
        L.append("")

    # Macro indicators
    macro = data.get("macro_indicators", {})
    if macro:
        L.append("## Macro Indicators")
        L.append("")
        L.append("| Indicator | Current | 5Y Percentile | 3M Change | 12M Change |")
        L.append("|-----------|--------:|--------------:|----------:|-----------:|")
        for key, mi in macro.items():
            name = MACRO_INDICATORS.get(key, {}).get("name", key)
            short_name = name[:30]
            pct = mi.get("percentile", {})
            trend = mi.get("trend", {})
            L.append(
                f"| {short_name} "
                f"| {pct.get('current', 0):.2f} "
                f"| {pct.get('percentile', 0):.1f}% "
                f"| {trend.get('change_3m', 0):+.1f}% "
                f"| {trend.get('change_12m', 0):+.1f}% |"
            )
        L.append("")

    # Yield curve
    if "yield_curve_spread" in data:
        spread = data["yield_curve_spread"]
        L.append("## Yield Curve")
        L.append("")
        L.append(f"- **10Y-2Y Spread**: {spread:.2f}%")
        if spread < 0:
            L.append("- **Signal**: Inverted yield curve -- recession risk elevated")
        elif spread < 0.5:
            L.append("- **Signal**: Flat yield curve -- late cycle / caution")
        else:
            L.append("- **Signal**: Normal yield curve -- expansion phase")
        L.append("")

    # Credit spread
    if "credit_spread_ratio" in data:
        L.append(f"- **HYG/LQD Ratio**: {data['credit_spread_ratio']:.4f}")
        L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by Cyclical Trough Strategy — Cycle Indicator Collector*")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cycle Indicator Collector (Cyclical Trough Strategy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--ticker", help="Stock ticker to collect indicators for")
    parser.add_argument("--years", type=int, default=5, help="Years of history (default 5)")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--all-indicators", action="store_true",
                        help="Fetch all sector/macro indicators without a specific ticker")

    args = parser.parse_args()

    if args.all_indicators:
        # Fetch all indicators without stock-specific context
        data = {
            "ticker": "ALL",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "detected_sector": None,
            "all_sector_indicators": {},
            "macro_indicators": {},
        }

        print("Fetching all sector indicators...")
        for key, ind in SECTOR_INDICATORS.items():
            hist = fetch_indicator_history(ind["symbol"], args.years)
            if hist is not None:
                data["all_sector_indicators"][key] = {
                    "name": ind["name"],
                    "percentile": compute_percentile(hist),
                    "trend": compute_trend(hist),
                }
                print(f"  {ind['name']}: OK")

        print("Fetching macro indicators...")
        for key, ind in MACRO_INDICATORS.items():
            hist = fetch_indicator_history(ind["symbol"], args.years)
            if hist is not None:
                data["macro_indicators"][key] = {
                    "name": ind["name"],
                    "percentile": compute_percentile(hist),
                    "trend": compute_trend(hist),
                }
                print(f"  {ind['name']}: OK")

        report = format_cycle_data_pack(data)
        output_path = args.output or os.path.join(
            os.path.dirname(__file__), "..", "output", "cycle", "all_indicators.md"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nReport saved to: {output_path}")
        return

    if not args.ticker:
        parser.error("--ticker required (or use --all-indicators)")

    ticker = args.ticker.strip().upper()
    print(f"\nCollecting cycle indicators for {ticker}...")

    data = collect_cycle_indicators(ticker, args.years)
    report = format_cycle_data_pack(data)

    if args.output:
        output_path = args.output
    else:
        out_dir = get_cycle_output_dir(ticker)
        output_path = os.path.join(out_dir, "cycle_data_pack.md")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")
    print(f"  Detected sector: {data.get('detected_sector', 'Unknown')}")
    if "stock_price" in data:
        sp = data["stock_price"]
        print(f"  Price percentile: {sp.get('percentile', 0):.1f}% "
              f"(${sp.get('current', 0):.2f})")


if __name__ == "__main__":
    main()
