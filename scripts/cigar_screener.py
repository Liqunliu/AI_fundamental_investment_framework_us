#!/usr/bin/env python3
"""Cigar Butt Deep Value Screener.

Screens for stocks trading below net asset value using Finviz sector
filters, then enriches with yfinance balance sheet data for quick NAV.

Pipeline:
  Tier 1: Finviz screen for P/B < 0.6 across value sectors
  Tier 2: yfinance balance sheet enrichment (quick T0/T1/T2 NAV)
  Tier 3: Score (NAV discount 35% + div yield 25% + FCF 20% + P/B 20%)

Output: output/cigar/screen/cigar_candidates.csv

Usage:
    python3 scripts/cigar_screener.py
    python3 scripts/cigar_screener.py --with-nav
    python3 scripts/cigar_screener.py --no-nav --top-n 20
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from config import DEFAULT_CONFIG  # noqa: E402
from cigar_config import CIGAR_CONFIG  # noqa: E402

_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
_OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "output", "cigar", "screen")

try:
    from finvizfinance.screener.overview import Overview as FinvizScreener
except ImportError:
    print("ERROR: finvizfinance not installed. pip install finvizfinance", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_output_dir() -> str:
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    return _OUTPUT_DIR


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_number(val: Any) -> float:
    """Parse Finviz number strings."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    val = str(val).strip().replace(",", "")
    if not val or val == "-":
        return np.nan
    if val.endswith("%"):
        try:
            return float(val[:-1])
        except ValueError:
            return np.nan
    multipliers = {"B": 1e9, "M": 1e6, "K": 1e3}
    for suffix, mult in multipliers.items():
        if val.endswith(suffix):
            try:
                return float(val[:-1]) * mult
            except ValueError:
                return np.nan
    try:
        return float(val)
    except ValueError:
        return np.nan


# Column name normalization (same as cycle_screener)
_COL_MAP = {
    "Market Cap": "market_cap",
    "P/E": "pe",
    "Price/Book": "pb",
    "P/B": "pb",
    "ROE": "roe",
    "ROA": "roa",
    "Gross Margin": "gross_margin",
    "Operating Margin": "op_margin",
    "Profit Margin": "net_margin",
    "Debt/Equity": "debt_equity",
    "Debt/Eq": "debt_equity",
    "Dividend Yield": "div_yield",
    "Dividend": "div_yield",
    "Beta": "beta",
    "Volume": "volume",
    "Price": "price",
    "Perf YTD": "ytd_perf",
    "Perf Year": "ytd_perf",
}

_TEXT_COLS = {
    "Ticker": "ticker",
    "Company": "name",
    "Sector": "sector",
    "Industry": "industry",
    "Country": "country",
}


# ---------------------------------------------------------------------------
# Tier 1: Finviz Deep Value Screen
# ---------------------------------------------------------------------------

def fetch_deep_value_from_finviz(
    custom_filter: Optional[str] = None,
) -> pd.DataFrame:
    """Screen Finviz for deep value stocks (P/B < 0.6).

    Default: screens value sectors with P/B under Book, market cap > $300M.
    """
    frames: List[pd.DataFrame] = []

    if custom_filter:
        fscreen = FinvizScreener()
        pairs = [p.strip() for p in custom_filter.split(",") if "=" in p]
        fd = {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in pairs)}
        fscreen.set_filter(filters_dict=fd)
        print(f"[{_now_stamp()}] Fetching custom filter from Finviz...")
        try:
            df = fscreen.screener_view(verbose=0)
            frames.append(df)
        except Exception as e:
            print(f"  Warning: Custom filter fetch failed: {e}")
    else:
        # Screen each value sector for P/B < Book (Under 1)
        for sector in CIGAR_CONFIG.value_sectors:
            fscreen = FinvizScreener()
            fscreen.set_filter(filters_dict={
                "Sector": sector,
                "P/B": "Under 1",
                "Market Cap.": "+Small (over $300mln)",
            })
            print(f"[{_now_stamp()}] Fetching {sector} sector (P/B < 1)...")
            try:
                df = fscreen.screener_view(verbose=0)
                if not df.empty:
                    frames.append(df)
                    print(f"  Found {len(df)} candidates in {sector}")
            except Exception as e:
                print(f"  Warning: {sector} fetch failed: {e}")
            time.sleep(1.0)  # Respect Finviz rate limits

    if not frames:
        print("ERROR: No data fetched from Finviz")
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    # Normalize columns
    rename_map = {}
    for old_name in df.columns:
        clean = old_name.strip()
        if clean in _TEXT_COLS:
            rename_map[old_name] = _TEXT_COLS[clean]
        elif clean in _COL_MAP:
            rename_map[old_name] = _COL_MAP[clean]

    df = df.rename(columns=rename_map)

    # Parse numeric columns
    for col in ["market_cap", "pe", "pb", "roe", "gross_margin", "op_margin",
                 "net_margin", "debt_equity", "div_yield", "beta", "volume", "price"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_number)

    if "market_cap" in df.columns:
        df["market_cap_b"] = df["market_cap"] / 1e9

    # Drop duplicates
    if "ticker" in df.columns:
        df = df.drop_duplicates(subset=["ticker"])

    # Filter P/B < 0.6 (our target zone)
    if "pb" in df.columns:
        before = len(df)
        df = df[df["pb"] <= CIGAR_CONFIG.pb_screen_max].copy()
        print(f"  P/B <= {CIGAR_CONFIG.pb_screen_max}: {len(df)} (from {before})")

    print(f"  Total deep value candidates: {len(df)}")
    return df


def apply_basic_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply basic quality filters for cigar butt screening."""
    if df.empty:
        return df

    initial = len(df)

    # Market cap >= $300M
    if "market_cap_b" in df.columns:
        df = df[df["market_cap_b"] >= CIGAR_CONFIG.screener_min_market_cap_m / 1000]
        print(f"  Market cap >= ${CIGAR_CONFIG.screener_min_market_cap_m:.0f}M: {len(df)}")

    # US-listed only
    if "country" in df.columns:
        df = df[df["country"].str.contains("USA", na=True)]
        print(f"  US-listed: {len(df)}")

    print(f"  Basic filters: {len(df)} remain (from {initial})")
    return df.copy()


# ---------------------------------------------------------------------------
# Tier 2: yfinance NAV Enrichment
# ---------------------------------------------------------------------------

def _compute_quick_nav_for_ticker(ticker: str) -> Dict[str, Any]:
    """Compute quick T0/T1/T2 NAV from yfinance balance sheet."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        bs = t.balance_sheet
        if bs is None or bs.empty:
            return {"ticker": ticker, "error": "No balance sheet"}

        info = t.info or {}
        price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        market_cap = info.get("marketCap", 0)
        shares = info.get("sharesOutstanding", 0)
        div_yield = info.get("dividendYield", 0) or 0

        if shares <= 0 or price <= 0:
            return {"ticker": ticker, "error": "No price/shares data"}

        shares_m = shares / 1e6  # Convert to millions

        # Extract balance sheet items (latest column = first column)
        def _get_bs(labels: List[str]) -> float:
            for label in labels:
                if label in bs.index:
                    val = bs.loc[label].dropna()
                    if not val.empty:
                        return float(val.iloc[0]) / 1e6  # Convert to millions
            return 0.0

        cash = _get_bs(["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments",
                        "Cash Equivalents", "Cash And Short Term Investments"])
        current_assets = _get_bs(["Current Assets", "Total Current Assets"])
        ar = _get_bs(["Accounts Receivable", "Net Receivables", "Receivables"])
        inventory = _get_bs(["Inventory", "Inventories"])
        total_liab = _get_bs(["Total Liabilities Net Minority Interest", "Total Liab",
                              "Total Liabilities"])
        total_debt = _get_bs(["Total Debt", "Long Term Debt And Capital Lease Obligation"])
        equity = _get_bs(["Stockholders Equity", "Total Stockholders Equity",
                          "Common Stock Equity"])
        total_assets = _get_bs(["Total Assets"])
        goodwill = _get_bs(["Goodwill", "Goodwill And Other Intangible Assets"])

        # IBD fallback
        if total_debt <= 0:
            lt_debt = _get_bs(["Long Term Debt"])
            st_debt = _get_bs(["Current Debt", "Current Debt And Capital Lease Obligation"])
            total_debt = lt_debt + st_debt

        # T0/T1/T2 NAV per share
        t0_nav = (cash - total_liab) / shares_m if shares_m > 0 else 0
        t1_nav = (cash - total_debt) / shares_m if shares_m > 0 else 0
        t2_nav = (cash + ar * 0.85 + inventory * 0.65 - total_liab) / shares_m if shares_m > 0 else 0

        # P/B
        bvps = equity / shares_m if shares_m > 0 and equity > 0 else 0
        pb = price / bvps if bvps > 0 else 0

        # FCF
        cf = t.cashflow
        fcf = 0.0
        if cf is not None and not cf.empty:
            if "Free Cash Flow" in cf.index:
                fcf_vals = cf.loc["Free Cash Flow"].dropna()
                if not fcf_vals.empty:
                    fcf = float(fcf_vals.iloc[0]) / 1e6

        fcf_yield = fcf / (market_cap / 1e6) if market_cap > 0 else 0

        # NAV discount (best qualifying tier)
        nav_discount = 0.0
        tier = "NONE"
        cfg = CIGAR_CONFIG
        if t0_nav > 0 and price < t0_nav * (1 - cfg.t0_entry_discount):
            tier = "T0"
            nav_discount = (t0_nav - price) / t0_nav
        elif t1_nav > 0 and price < t1_nav * (1 - cfg.t1_entry_discount):
            tier = "T1"
            nav_discount = (t1_nav - price) / t1_nav
        elif t2_nav > 0 and price < t2_nav * (1 - cfg.t2_entry_discount):
            tier = "T2"
            nav_discount = (t2_nav - price) / t2_nav

        # Goodwill ratio
        gw_ratio = goodwill / total_assets if total_assets > 0 else 0

        return {
            "ticker": ticker,
            "t0_nav": round(t0_nav, 2),
            "t1_nav": round(t1_nav, 2),
            "t2_nav": round(t2_nav, 2),
            "tier": tier,
            "nav_discount": round(nav_discount * 100, 1),
            "pb_calc": round(pb, 2),
            "fcf_m": round(fcf, 1),
            "fcf_yield": round(fcf_yield * 100, 1),
            "div_yield_yf": round(div_yield * 100, 1),
            "goodwill_ratio": round(gw_ratio * 100, 1),
            "error": None,
        }

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def run_nav_enrichment(
    df: pd.DataFrame,
    batch_size: int = 15,
    inter_batch_pause: float = 5.0,
    inter_ticker_pause: float = 0.8,
) -> pd.DataFrame:
    """Run quick NAV enrichment for all tickers via yfinance."""
    if df.empty or "ticker" not in df.columns:
        return df

    tickers = df["ticker"].tolist()
    results = []

    print(f"\n[{_now_stamp()}] Running NAV enrichment for {len(tickers)} tickers...")

    for batch_start in range(0, len(tickers), batch_size):
        batch = tickers[batch_start:batch_start + batch_size]
        if batch_start > 0:
            print(f"  Pausing {inter_batch_pause}s between batches...")
            time.sleep(inter_batch_pause)

        for ticker in batch:
            result = _compute_quick_nav_for_ticker(ticker)
            results.append(result)
            if result.get("error"):
                print(f"    {ticker}: ERROR - {result['error']}")
            else:
                tier = result.get("tier", "NONE")
                disc = result.get("nav_discount", 0)
                pb = result.get("pb_calc", 0)
                print(f"    {ticker}: Tier={tier}, Discount={disc:.1f}%, P/B={pb:.2f}")
            time.sleep(inter_ticker_pause)

    # Merge results
    results_df = pd.DataFrame(results)
    df = df.merge(results_df, on="ticker", how="left")

    return df


# ---------------------------------------------------------------------------
# Scoring and ranking
# ---------------------------------------------------------------------------

def compute_cigar_score(df: pd.DataFrame) -> pd.DataFrame:
    """Score cigar butt candidates for ranking.

    Weights: NAV discount 35% + div yield 25% + FCF yield 20% + low P/B 20%
    """
    if df.empty:
        return df

    df = df.copy()
    scores = pd.Series(0.0, index=df.index)

    # NAV discount (higher = better, 35%)
    if "nav_discount" in df.columns:
        nd = df["nav_discount"].fillna(0)
        nd_norm = (nd - nd.min()) / (nd.max() - nd.min() + 1e-9)
        scores += 0.35 * nd_norm

    # Dividend yield (higher = better, 25%)
    div_col = "div_yield_yf" if "div_yield_yf" in df.columns else "div_yield"
    if div_col in df.columns:
        div = df[div_col].fillna(0)
        div_norm = (div - div.min()) / (div.max() - div.min() + 1e-9)
        scores += 0.25 * div_norm

    # FCF yield (higher = better, 20%)
    if "fcf_yield" in df.columns:
        fcf = df["fcf_yield"].fillna(0)
        fcf_norm = (fcf - fcf.min()) / (fcf.max() - fcf.min() + 1e-9)
        scores += 0.20 * fcf_norm

    # Low P/B (lower = better, inverse, 20%)
    pb_col = "pb_calc" if "pb_calc" in df.columns else "pb"
    if pb_col in df.columns:
        pb = df[pb_col].fillna(1.0)
        pb = pb.clip(lower=0.01)
        pb_inv = 1.0 / pb
        pb_inv_norm = (pb_inv - pb_inv.min()) / (pb_inv.max() - pb_inv.min() + 1e-9)
        scores += 0.20 * pb_inv_norm

    df["cigar_score"] = scores.round(4)
    df = df.sort_values("cigar_score", ascending=False).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

_SAVE_COLS = [
    "ticker", "name", "sector", "industry", "market_cap_b",
    "pe", "pb", "roe", "div_yield", "debt_equity",
    "t0_nav", "t1_nav", "t2_nav", "tier", "nav_discount",
    "pb_calc", "fcf_m", "fcf_yield", "div_yield_yf",
    "goodwill_ratio", "cigar_score",
]


def save_candidates(df: pd.DataFrame, filename: str = "cigar_candidates.csv") -> str:
    """Save candidates to CSV."""
    out_dir = _ensure_output_dir()
    path = os.path.join(out_dir, filename)

    cols = [c for c in _SAVE_COLS if c in df.columns]
    df[cols].to_csv(path, index=False, float_format="%.4f")

    print(f"\n  Saved {len(df)} candidates to {path}")
    return path


def display_results(df: pd.DataFrame, title: str, limit: int = 30) -> None:
    """Pretty-print results to console."""
    print(f"\n{'=' * 110}")
    print(f"  {title}")
    print(f"{'=' * 110}")

    for i, row in df.head(limit).iterrows():
        rank = i + 1
        ticker = str(row.get("ticker", "")).ljust(6)
        sector = str(row.get("sector", ""))[:15].ljust(15)
        industry = str(row.get("industry", ""))[:20].ljust(20)
        mktcap = f"${row.get('market_cap_b', 0):.1f}B".rjust(8) if pd.notna(row.get("market_cap_b")) else "     N/A"
        pb = f"{row.get('pb', 0):.2f}".rjust(5) if pd.notna(row.get("pb")) else "  N/A"
        tier = str(row.get("tier", "—")).rjust(4) if pd.notna(row.get("tier")) else "   —"
        disc = f"{row.get('nav_discount', 0):.0f}%".rjust(5) if pd.notna(row.get("nav_discount")) else "  N/A"
        div_y = f"{row.get('div_yield', 0):.1f}%".rjust(5) if pd.notna(row.get("div_yield")) else "  N/A"
        score = f"{row.get('cigar_score', 0):.3f}".rjust(6) if pd.notna(row.get("cigar_score")) else "   N/A"

        print(f"  {rank:>3}. {ticker} {sector} {industry} {mktcap}  P/B={pb}  "
              f"Tier={tier}  Disc={disc}  Div={div_y}  Score={score}")

    print(f"{'=' * 110}\n")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_screen(
    custom_filter: Optional[str] = None,
    with_nav: bool = True,
    top_n: int = 20,
    limit: int = 50,
) -> pd.DataFrame:
    """Run full cigar butt screening pipeline."""
    print(f"\n[{_now_stamp()}] Starting Cigar Butt Deep Value Screener")
    print(f"  Settings: top_n={top_n}, limit={limit}, with_nav={with_nav}")

    # Tier 1: Finviz deep value sectors
    df = fetch_deep_value_from_finviz(custom_filter)
    if df.empty:
        print("No candidates found.")
        return df

    # Basic quality filters
    df = apply_basic_filters(df)

    # Limit before expensive API calls
    df = df.head(limit)

    # Tier 2: yfinance NAV enrichment
    if with_nav:
        df = run_nav_enrichment(df)

    # Score and rank
    df = compute_cigar_score(df)

    # Select top N
    if top_n and len(df) > top_n:
        df = df.head(top_n).copy()

    # Display
    display_results(df, f"Top {len(df)} Cigar Butt Candidates")

    # Save
    save_candidates(df)

    print(f"[{_now_stamp()}] Screening complete: {len(df)} candidates")
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cigar Butt Deep Value Screener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--with-nav", action="store_true", default=False,
                        help="Include yfinance NAV enrichment (slower)")
    parser.add_argument("--no-nav", action="store_true",
                        help="Skip NAV enrichment (Finviz only, fast)")
    parser.add_argument("--top-n", type=int, default=CIGAR_CONFIG.screener_top_n,
                        help=f"Select top N candidates (default {CIGAR_CONFIG.screener_top_n})")
    parser.add_argument("--limit", type=int, default=CIGAR_CONFIG.screener_limit,
                        help=f"Max candidates before enrichment (default {CIGAR_CONFIG.screener_limit})")
    parser.add_argument("--custom-filter", help="Custom Finviz filter string")

    args = parser.parse_args()

    with_nav = args.with_nav and not args.no_nav

    run_screen(
        custom_filter=args.custom_filter,
        with_nav=with_nav,
        top_n=args.top_n,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
