#!/usr/bin/env python3
"""Cyclical Stock Screener for Cyclical Trough Strategy.

Screens for cyclical stocks using Finviz sector filters, confirms
cyclicality via coefficient of variation, and runs quick normalized GG.

Pipeline:
  Tier 1: Finviz screen for cyclical sectors/industries
  Tier 2: Cyclicality confirmation (CV check via yfinance)
  Tier 3: Quick normalized GG estimate

Output: output/cycle/screen/cyclical_candidates.csv

Usage:
    python3 scripts/cycle_screener.py
    python3 scripts/cycle_screener.py --with-normalized-gg
    python3 scripts/cycle_screener.py --with-normalized-gg --top-n 15
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
from cycle_config import CYCLE_CONFIG  # noqa: E402

_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
_OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "output", "cycle", "screen")

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


# Column name normalization
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
# Tier 1: Finviz Cyclical Sector Screen
# ---------------------------------------------------------------------------

def fetch_cyclical_from_finviz(
    custom_filter: Optional[str] = None,
) -> pd.DataFrame:
    """Screen Finviz for cyclical sector stocks.

    Default filters: Energy + Basic Materials + relevant Industrials,
    market cap > $500M.
    """
    fscreen = FinvizScreener()

    if custom_filter:
        # Parse custom filter string into filters_dict
        # e.g. "Sector=Energy,Market Cap.=+Mid (over $2bln)"
        pairs = [p.strip() for p in custom_filter.split(",") if "=" in p]
        fd = {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in pairs)}
        fscreen.set_filter(filters_dict=fd)
    else:
        # Use sector-based filter for cyclicals — mid cap and over ($2B+)
        fscreen.set_filter(
            filters_dict={"Sector": "Energy", "Market Cap.": "+Mid (over $2bln)"},
        )

    print(f"[{_now_stamp()}] Fetching Energy sector from Finviz...")
    try:
        df_energy = fscreen.screener_view(verbose=0)
    except Exception as e:
        print(f"  Warning: Energy fetch failed: {e}")
        df_energy = pd.DataFrame()

    # Basic Materials
    fscreen2 = FinvizScreener()
    fscreen2.set_filter(filters_dict={"Sector": "Basic Materials", "Market Cap.": "+Mid (over $2bln)"})
    print(f"[{_now_stamp()}] Fetching Basic Materials sector...")
    try:
        df_materials = fscreen2.screener_view(verbose=0)
    except Exception as e:
        print(f"  Warning: Basic Materials fetch failed: {e}")
        df_materials = pd.DataFrame()

    # Industrials (selected cyclical industries)
    fscreen3 = FinvizScreener()
    fscreen3.set_filter(filters_dict={"Sector": "Industrials", "Market Cap.": "+Mid (over $2bln)"})
    print(f"[{_now_stamp()}] Fetching Industrials sector...")
    try:
        df_industrials = fscreen3.screener_view(verbose=0)
    except Exception as e:
        print(f"  Warning: Industrials fetch failed: {e}")
        df_industrials = pd.DataFrame()

    # Combine
    frames = [df for df in [df_energy, df_materials, df_industrials] if not df.empty]
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

    print(f"  Total cyclical candidates: {len(df)}")
    return df


def filter_cyclical_industries(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to known cyclical industries."""
    if "industry" not in df.columns or df.empty:
        return df

    cyclical_kws = [kw.lower() for kw in CYCLE_CONFIG.cyclical_industries]

    mask = df["industry"].str.lower().apply(
        lambda x: any(kw in str(x) for kw in cyclical_kws) if pd.notna(x) else False
    )

    filtered = df[mask].copy()
    print(f"  After cyclical industry filter: {len(filtered)} (from {len(df)})")
    return filtered


def apply_basic_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply basic quality filters (less strict than QY)."""
    if df.empty:
        return df

    initial = len(df)

    # Market cap >= $500M (lower than QY's $1B — cyclicals include mid-caps)
    if "market_cap_b" in df.columns:
        df = df[df["market_cap_b"] >= 0.5]
        print(f"  Market cap >= $500M: {len(df)}")

    # No extreme PE (negative OK for cyclicals at trough, but filter out > 100)
    if "pe" in df.columns:
        df = df[(df["pe"].isna()) | (df["pe"] <= 100)]
        print(f"  PE <= 100 (or N/A): {len(df)}")

    print(f"  Basic filters: {len(df)} remain (from {initial})")
    return df.copy()


# ---------------------------------------------------------------------------
# Tier 2: Cyclicality Confirmation (CV Check)
# ---------------------------------------------------------------------------

def _compute_cv_for_ticker(ticker: str) -> Dict[str, Any]:
    """Compute coefficient of variation for revenue and EBITDA."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)

        # Get income statement (annual)
        inc = t.financials
        if inc is None or inc.empty:
            return {"ticker": ticker, "error": "No financials"}

        # Revenue CV
        rev_row = None
        for label in ["Total Revenue", "Revenue"]:
            if label in inc.index:
                rev_row = inc.loc[label].dropna()
                break

        cv_rev = np.nan
        if rev_row is not None and len(rev_row) >= 3:
            values = rev_row.values.astype(float)
            mean = np.mean(values)
            if mean != 0:
                cv_rev = np.std(values) / abs(mean)

        # EBITDA CV
        ebitda_row = None
        for label in ["EBITDA", "Normalized EBITDA"]:
            if label in inc.index:
                ebitda_row = inc.loc[label].dropna()
                break

        cv_ebitda = np.nan
        if ebitda_row is not None and len(ebitda_row) >= 3:
            values = ebitda_row.values.astype(float)
            mean = np.mean(values)
            if mean != 0:
                cv_ebitda = np.std(values) / abs(mean)

        # Quick normalized GG estimate
        cf = t.cashflow
        info = t.info
        quick_norm_gg = np.nan

        if cf is not None and not cf.empty:
            ocf_row = None
            for label in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                if label in cf.index:
                    ocf_row = cf.loc[label].dropna()
                    break

            capex_row = None
            for label in ["Capital Expenditure", "Capital Expenditures"]:
                if label in cf.index:
                    capex_row = cf.loc[label].dropna()
                    break

            market_cap = info.get("marketCap", 0) if info else 0

            if ocf_row is not None and capex_row is not None and market_cap > 0:
                ocf_vals = ocf_row.values.astype(float)
                capex_vals = np.abs(capex_row.values.astype(float))

                # Use available overlapping years
                n = min(len(ocf_vals), len(capex_vals))
                if n >= 2:
                    med_ocf = np.median(ocf_vals[:n])
                    med_capex = np.median(capex_vals[:n])
                    norm_aa = med_ocf - med_capex
                    quick_norm_gg = (norm_aa / market_cap) * 100

        is_cyclical = (
            (not np.isnan(cv_rev) and cv_rev >= CYCLE_CONFIG.min_revenue_cv)
            or (not np.isnan(cv_ebitda) and cv_ebitda >= CYCLE_CONFIG.min_ebitda_cv)
        )

        return {
            "ticker": ticker,
            "cv_revenue": round(cv_rev, 4) if not np.isnan(cv_rev) else None,
            "cv_ebitda": round(cv_ebitda, 4) if not np.isnan(cv_ebitda) else None,
            "is_cyclical": is_cyclical,
            "quick_norm_gg": round(quick_norm_gg, 2) if not np.isnan(quick_norm_gg) else None,
            "error": None,
        }

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def run_cv_check(
    df: pd.DataFrame,
    batch_size: int = 20,
    inter_batch_pause: float = 5.0,
    inter_ticker_pause: float = 0.6,
) -> pd.DataFrame:
    """Run CV check and quick normalized GG for all tickers."""
    if df.empty or "ticker" not in df.columns:
        return df

    tickers = df["ticker"].tolist()
    results = []

    print(f"\n[{_now_stamp()}] Running CV check for {len(tickers)} tickers...")

    for batch_start in range(0, len(tickers), batch_size):
        batch = tickers[batch_start:batch_start + batch_size]
        if batch_start > 0:
            print(f"  Pausing {inter_batch_pause}s between batches...")
            time.sleep(inter_batch_pause)

        for ticker in batch:
            result = _compute_cv_for_ticker(ticker)
            results.append(result)
            if result.get("error"):
                print(f"    {ticker}: ERROR - {result['error']}")
            else:
                cv_r = result.get("cv_revenue", "N/A")
                cv_e = result.get("cv_ebitda", "N/A")
                cyc = "YES" if result.get("is_cyclical") else "NO"
                print(f"    {ticker}: CV(Rev)={cv_r}, CV(EBITDA)={cv_e}, Cyclical={cyc}")
            time.sleep(inter_ticker_pause)

    # Merge results
    results_df = pd.DataFrame(results)
    df = df.merge(results_df, on="ticker", how="left")

    # Filter to confirmed cyclicals
    if "is_cyclical" in df.columns:
        before = len(df)
        df = df[df["is_cyclical"] == True].copy()
        print(f"\n  Confirmed cyclical: {len(df)} (from {before})")

    return df


# ---------------------------------------------------------------------------
# Scoring and ranking
# ---------------------------------------------------------------------------

def compute_cyclical_score(df: pd.DataFrame) -> pd.DataFrame:
    """Score cyclical candidates for ranking."""
    if df.empty:
        return df

    df = df.copy()

    # Components: CV (cyclicality strength) + quick normalized GG + low PE + div yield
    scores = pd.Series(0.0, index=df.index)

    # CV score (higher CV = more cyclical = potentially more upside at trough)
    if "cv_revenue" in df.columns:
        cv_r = df["cv_revenue"].fillna(0)
        cv_r_norm = (cv_r - cv_r.min()) / (cv_r.max() - cv_r.min() + 1e-9)
        scores += 0.20 * cv_r_norm

    if "cv_ebitda" in df.columns:
        cv_e = df["cv_ebitda"].fillna(0)
        cv_e_norm = (cv_e - cv_e.min()) / (cv_e.max() - cv_e.min() + 1e-9)
        scores += 0.15 * cv_e_norm

    # Quick normalized GG (higher = better value)
    if "quick_norm_gg" in df.columns:
        gg = df["quick_norm_gg"].fillna(0)
        gg_norm = (gg - gg.min()) / (gg.max() - gg.min() + 1e-9)
        scores += 0.35 * gg_norm

    # Low PE (inverse — lower PE = higher score, handle negatives)
    if "pe" in df.columns:
        pe = df["pe"].fillna(50)
        pe_inv = 1.0 / pe.clip(lower=1)
        pe_inv_norm = (pe_inv - pe_inv.min()) / (pe_inv.max() - pe_inv.min() + 1e-9)
        scores += 0.15 * pe_inv_norm

    # Dividend yield (cyclicals often have decent dividends)
    if "div_yield" in df.columns:
        div = df["div_yield"].fillna(0)
        div_norm = (div - div.min()) / (div.max() - div.min() + 1e-9)
        scores += 0.15 * div_norm

    df["cycle_score"] = scores.round(4)
    df = df.sort_values("cycle_score", ascending=False).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

_SAVE_COLS = [
    "ticker", "name", "sector", "industry", "market_cap_b",
    "pe", "pb", "roe", "div_yield", "debt_equity", "beta",
    "cv_revenue", "cv_ebitda", "is_cyclical", "quick_norm_gg",
    "cycle_score",
]


def save_candidates(df: pd.DataFrame, filename: str = "cyclical_candidates.csv") -> str:
    """Save candidates to CSV."""
    out_dir = _ensure_output_dir()
    path = os.path.join(out_dir, filename)

    cols = [c for c in _SAVE_COLS if c in df.columns]
    df[cols].to_csv(path, index=False, float_format="%.4f")

    print(f"\n  Saved {len(df)} candidates to {path}")
    return path


def display_results(df: pd.DataFrame, title: str, limit: int = 30) -> None:
    """Pretty-print results to console."""
    print(f"\n{'=' * 100}")
    print(f"  {title}")
    print(f"{'=' * 100}")

    display_cols = ["ticker", "sector", "industry", "market_cap_b", "pe",
                    "cv_revenue", "cv_ebitda", "quick_norm_gg", "cycle_score"]
    cols = [c for c in display_cols if c in df.columns]

    for i, row in df.head(limit).iterrows():
        rank = i + 1
        ticker = str(row.get("ticker", "")).ljust(6)
        sector = str(row.get("sector", ""))[:15].ljust(15)
        industry = str(row.get("industry", ""))[:20].ljust(20)
        mktcap = f"${row.get('market_cap_b', 0):.1f}B".rjust(8) if pd.notna(row.get("market_cap_b")) else "     N/A"
        pe = f"{row.get('pe', 0):.1f}".rjust(6) if pd.notna(row.get("pe")) else "   N/A"
        cv_r = f"{row.get('cv_revenue', 0):.3f}".rjust(6) if pd.notna(row.get("cv_revenue")) else "   N/A"
        cv_e = f"{row.get('cv_ebitda', 0):.3f}".rjust(6) if pd.notna(row.get("cv_ebitda")) else "   N/A"
        ngg = f"{row.get('quick_norm_gg', 0):.1f}%".rjust(7) if pd.notna(row.get("quick_norm_gg")) else "    N/A"
        score = f"{row.get('cycle_score', 0):.3f}".rjust(6) if pd.notna(row.get("cycle_score")) else "   N/A"

        print(f"  {rank:>3}. {ticker} {sector} {industry} {mktcap}  PE={pe}  "
              f"CV(R)={cv_r}  CV(E)={cv_e}  NormGG={ngg}  Score={score}")

    print(f"{'=' * 100}\n")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_screen(
    custom_filter: Optional[str] = None,
    with_cv: bool = True,
    with_normalized_gg: bool = False,
    top_n: int = 15,
    limit: int = 40,
) -> pd.DataFrame:
    """Run full cyclical screening pipeline."""
    print(f"\n[{_now_stamp()}] Starting Cyclical Trough Screener")
    print(f"  Settings: top_n={top_n}, limit={limit}")

    # Tier 1: Finviz cyclical sectors
    df = fetch_cyclical_from_finviz(custom_filter)
    if df.empty:
        print("No candidates found.")
        return df

    # Filter to cyclical industries
    df = filter_cyclical_industries(df)
    if df.empty:
        print("No cyclical industry matches found.")
        return df

    # Basic quality filters
    df = apply_basic_filters(df)

    # Limit before expensive API calls
    df = df.head(limit)

    # Tier 2: CV check + quick normalized GG
    if with_cv or with_normalized_gg:
        df = run_cv_check(df)

    # Score and rank
    df = compute_cyclical_score(df)

    # Select top N
    if top_n and len(df) > top_n:
        df = df.head(top_n).copy()

    # Display
    display_results(df, f"Top {len(df)} Cyclical Candidates")

    # Save
    save_candidates(df)

    print(f"[{_now_stamp()}] Screening complete: {len(df)} candidates")
    return df


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cyclical Stock Screener (Cyclical Trough Strategy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--with-normalized-gg", action="store_true",
                        help="Include quick normalized GG estimate")
    parser.add_argument("--top-n", type=int, default=CYCLE_CONFIG.screener_top_n,
                        help=f"Select top N candidates (default {CYCLE_CONFIG.screener_top_n})")
    parser.add_argument("--limit", type=int, default=CYCLE_CONFIG.screener_limit,
                        help=f"Max candidates before CV check (default {CYCLE_CONFIG.screener_limit})")
    parser.add_argument("--custom-filter", help="Custom Finviz filter string")
    parser.add_argument("--no-cv", action="store_true",
                        help="Skip CV check (faster, less accurate)")

    args = parser.parse_args()

    run_screen(
        custom_filter=args.custom_filter,
        with_cv=not args.no_cv,
        with_normalized_gg=args.with_normalized_gg,
        top_n=args.top_n,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
