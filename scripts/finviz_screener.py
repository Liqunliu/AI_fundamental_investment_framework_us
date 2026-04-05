#!/usr/bin/env python3
"""US Equity Quality Yield Strategy — Finviz Screener + Quick GG Scanner.

Two-pass screening pipeline:
  Tier 1   : Finviz bulk screen -> ~50 candidates   (~2 min)
  Tier 1.5 : Quick GG scan via yfinance             (~5-8 min)
  Selection: Top N for deep analysis

Output files (written to output/screen/):
  tier1_candidates.csv  — Finviz results
  tier1_with_gg.csv     — Same + quick_gg column
  tier2_shortlist.csv   — Top N tickers

Usage:
    python3 scripts/finviz_screener.py                           # Tier 1 only
    python3 scripts/finviz_screener.py --with-gg                 # Tier 1 + GG scan
    python3 scripts/finviz_screener.py --with-gg --top-n 10      # Full pipeline
    python3 scripts/finviz_screener.py --custom-filter "cap_largeover,fa_pe_u20"
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

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
# Resolve the scripts/ directory so we can import sibling modules regardless
# of the working directory the script is invoked from.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from config import DEFAULT_CONFIG, validate_us_ticker  # noqa: E402
from cache import DataCache  # noqa: E402

# Project root (one level above scripts/)
_PROJECT_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, ".."))
_OUTPUT_SCREEN_DIR = os.path.join(_PROJECT_ROOT, "output", "screen")

# ---------------------------------------------------------------------------
# Third-party imports with helpful error messages
# ---------------------------------------------------------------------------
try:
    from finvizfinance.screener.financial import Financial
except ImportError:
    print(
        "ERROR: finvizfinance not installed.  Run:  pip install finvizfinance",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================================
#  Helpers
# ============================================================================

def _ensure_output_dir() -> str:
    """Create and return the output/screen/ directory path."""
    os.makedirs(_OUTPUT_SCREEN_DIR, exist_ok=True)
    return _OUTPUT_SCREEN_DIR


def _now_stamp() -> str:
    """Return an ISO-style timestamp string for logging."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_finviz_number(val: Any) -> float:
    """Parse Finviz number strings like '123.45B', '1.23K', '45.67%', '-'."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    val = str(val).strip().replace(",", "")
    if not val or val == "-":
        return np.nan

    # Percentage
    if val.endswith("%"):
        try:
            return float(val[:-1])
        except ValueError:
            return np.nan

    # Multiplier suffixes
    multipliers = {"B": 1e9, "M": 1e6, "K": 1e3}
    for suffix, mult in multipliers.items():
        if val.endswith(suffix):
            try:
                return float(val[:-1]) * mult
            except ValueError:
                return np.nan

    # Plain number
    try:
        return float(val)
    except ValueError:
        return np.nan


# ============================================================================
#  Tier 1 — Finviz Screening
# ============================================================================

# Column mapping: Finviz column name -> internal normalised name.
# Covers both Financial-view and Overview-view naming conventions.
_FINVIZ_NUMERIC_MAP: Dict[str, str] = {
    "Market Cap": "market_cap",
    "P/E": "pe",
    "P/B": "pb",
    "P/S": "ps",
    "Price": "price",
    "Change": "change_pct",
    "Volume": "volume",
    "ROE": "roe",
    "ROA": "roa",
    "ROIC": "roic",
    "Gross M": "gross_margin",
    "Gross Margin": "gross_margin",
    "Oper M": "op_margin",
    "Oper. Margin": "op_margin",
    "Profit M": "net_margin",
    "Profit Margin": "net_margin",
    "Dividend": "div_yield",
    "Debt/Eq": "debt_equity",
    "LTDebt/Eq": "lt_debt_equity",
    "Curr R": "current_ratio",
    "Current Ratio": "current_ratio",
    "Quick R": "quick_ratio",
    "Quick Ratio": "quick_ratio",
    "EPS (ttm)": "eps",
    "EPS next Y": "eps_growth",
    "Sales": "revenue",
    "Perf YTD": "perf_ytd",
    "Perf Year": "perf_year",
    "Beta": "beta",
}

_FINVIZ_TEXT_MAP: Dict[str, str] = {
    "Ticker": "ticker",
    "Company": "name",
    "Sector": "sector",
    "Industry": "industry",
    "Country": "country",
}


def fetch_from_finviz(
    filters: Optional[Dict[str, str]] = None,
    custom_filter: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch stocks from Finviz Financial screener.

    Args:
        filters: Dict of filter criteria for finvizfinance set_filter().
        custom_filter: Raw Finviz filter string (e.g. "cap_largeover,fa_pe_u20").

    Returns:
        DataFrame with normalised columns ready for Quality Yield filtering.
    """
    print(f"\n{'='*80}")
    print("TIER 1 — Finviz Screening")
    print(f"{'='*80}")
    t0 = time.time()

    try:
        fviz = Financial()

        if custom_filter:
            print(f"  Custom filter: {custom_filter}")
            fviz.set_filter(filters_dict={})
            df = fviz.screener_view(custom=custom_filter)
        elif filters:
            print(f"  Applying {len(filters)} filter(s):")
            for k, v in filters.items():
                print(f"    {k}: {v}")
            fviz.set_filter(filters_dict=filters)
            df = fviz.screener_view()
        else:
            print("  No filters — fetching full universe")
            df = fviz.screener_view()

        if df is None or df.empty:
            print("  WARNING: Finviz returned 0 stocks", file=sys.stderr)
            return pd.DataFrame()

        print(f"  Retrieved {len(df)} stocks in {time.time()-t0:.1f}s")

    except Exception as exc:
        print(f"  ERROR: Finviz fetch failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ---- Normalise columns ----
    df.columns = df.columns.str.strip()

    for fviz_col, norm_col in _FINVIZ_NUMERIC_MAP.items():
        if fviz_col in df.columns:
            df[norm_col] = df[fviz_col].apply(parse_finviz_number)

    for fviz_col, norm_col in _FINVIZ_TEXT_MAP.items():
        if fviz_col in df.columns:
            df[norm_col] = df[fviz_col]

    if "market_cap" in df.columns:
        df["market_cap_b"] = df["market_cap"] / 1e9

    return df


def apply_qy_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply QY-style value/quality filters using DEFAULT_CONFIG thresholds."""
    cfg = DEFAULT_CONFIG
    print(f"\n  Applying Quality Yield filters (universe={len(df)})")
    n0 = len(df)

    def _step(mask, label):
        nonlocal df
        prev = len(df)
        df = df[mask]
        dropped = prev - len(df)
        print(f"    {label}: {len(df)} ({'-' if dropped else '+'}{abs(dropped)})")

    # Market cap
    if "market_cap_b" in df.columns:
        _step(df["market_cap_b"] >= cfg.min_market_cap_b,
              f"Market cap >= ${cfg.min_market_cap_b}B")

    # PE
    if "pe" in df.columns:
        _step((df["pe"] > 0) & (df["pe"] <= cfg.max_pe),
              f"0 < PE <= {cfg.max_pe}")

    # PB
    if "pb" in df.columns:
        _step((df["pb"] > 0) & (df["pb"] <= cfg.max_pb),
              f"0 < PB <= {cfg.max_pb}")

    # ROE — handle both % and decimal representations
    if "roe" in df.columns:
        median_roe = df["roe"].median()
        min_roe_val = cfg.min_roe * 100 if median_roe > 1.0 else cfg.min_roe
        _step(df["roe"] >= min_roe_val,
              f"ROE >= {cfg.min_roe*100:.0f}%")

    # Gross margin
    if "gross_margin" in df.columns:
        median_gm = df["gross_margin"].median()
        min_gm_val = cfg.min_gross_margin if median_gm > 1.0 else cfg.min_gross_margin / 100.0
        _step(df["gross_margin"] >= min_gm_val,
              f"Gross margin >= {cfg.min_gross_margin}%")

    # Debt / Equity (allow NaN — could mean zero debt)
    if "debt_equity" in df.columns:
        _step(df["debt_equity"].isna() | (df["debt_equity"] <= cfg.max_debt_equity),
              f"D/E <= {cfg.max_debt_equity}")

    print(f"  Passed filters: {len(df)} / {n0}")
    return df


def compute_composite_score(df: pd.DataFrame) -> pd.DataFrame:
    """Score and rank candidates using a multi-factor composite."""
    df = df.copy()

    def _norm(series: pd.Series) -> pd.Series:
        """Min-max normalise, returning 0 for constant/empty series."""
        s = series.fillna(0)
        smax = s.max()
        if smax == 0:
            return pd.Series(0.0, index=df.index)
        return s / smax

    roe_n = _norm(df.get("roe", pd.Series(dtype=float)))
    pe_inv_n = _norm(1 / df["pe"]) if "pe" in df.columns and (df["pe"] > 0).any() else pd.Series(0.0, index=df.index)
    pb_inv_n = _norm(1 / df["pb"]) if "pb" in df.columns and (df["pb"] > 0).any() else pd.Series(0.0, index=df.index)
    div_n = _norm(df.get("div_yield", pd.Series(dtype=float)))

    # YTD perf — shift to positive range before normalising
    if "perf_ytd" in df.columns:
        shifted = df["perf_ytd"] - df["perf_ytd"].min()
        perf_n = _norm(shifted)
    else:
        perf_n = pd.Series(0.0, index=df.index)

    vol_n = _norm(df.get("volume", pd.Series(dtype=float)))

    df["score"] = (
        0.25 * roe_n
        + 0.20 * pe_inv_n
        + 0.15 * pb_inv_n
        + 0.15 * div_n
        + 0.15 * perf_n
        + 0.10 * vol_n
    )

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    print(f"  Composite score range: {df['score'].min():.4f} .. {df['score'].max():.4f}")
    if len(df) > 0:
        top = df.iloc[0]
        label = top.get("name", top["ticker"])
        print(f"  Top candidate: {top['ticker']} ({label})  score={top['score']:.4f}")

    return df


def run_tier1(
    custom_filter: Optional[str] = None,
    limit: int = 50,
) -> pd.DataFrame:
    """Execute Tier 1: Finviz screen -> filter -> score -> top N.

    Returns:
        DataFrame of up to *limit* ranked candidates.
    """
    finviz_filters = {
        "Market Cap.": "+Mid (over $2bln)",
    }

    df_raw = fetch_from_finviz(
        filters=None if custom_filter else finviz_filters,
        custom_filter=custom_filter,
    )
    if df_raw.empty:
        return df_raw

    df_filt = apply_qy_filters(df_raw)
    if df_filt.empty:
        print("  No stocks survived Quality Yield filters — try relaxing criteria.")
        return df_filt

    df_scored = compute_composite_score(df_filt)
    df_top = df_scored.head(limit).copy()
    print(f"  Tier 1 result: {len(df_top)} candidates (capped at {limit})")
    return df_top


# ============================================================================
#  Tier 1.5 — Quick GG Scan
# ============================================================================

def _fetch_gg_for_ticker(ticker: str, cache: DataCache | None = None) -> Dict[str, Any]:
    """Fetch basic financials from yfinance and compute quick GG.

    Quick GG = (Operating Cash Flow - Capital Expenditure) / Market Cap
    This is an *approximation*: it omits SBC add-back, debt changes, etc.

    Args:
        ticker: US stock ticker.
        cache: Optional DataCache for persistent caching of info/cashflow data.

    Returns:
        dict with keys: ticker, ocf, capex, fcf, market_cap_yf, quick_gg,
        and an 'error' key (None on success, message on failure).
    """
    import yfinance as yf  # imported here to keep Tier 1 fast if yfinance not installed

    result: Dict[str, Any] = {
        "ticker": ticker,
        "ocf": np.nan,
        "capex": np.nan,
        "fcf": np.nan,
        "market_cap_yf": np.nan,
        "quick_gg": np.nan,
        "error": None,
    }

    try:
        stock = yf.Ticker(ticker)

        # --- Info (with cache) ---
        info = None
        if cache:
            info = cache.get(ticker, "info")
        if info is None:
            info = stock.info or {}
            if cache:
                cache.put(ticker, "info", info)

        # Market cap from yfinance
        mktcap = info.get("marketCap")
        if not mktcap or mktcap <= 0:
            result["error"] = "no market cap"
            return result
        result["market_cap_yf"] = mktcap

        # --- Cash flow (with cache) ---
        cf = None
        if cache:
            cf = cache.get(ticker, "cashflow")
        if cf is None:
            try:
                cf = stock.cashflow
                if cache and cf is not None:
                    cache.put(ticker, "cashflow", cf)
            except Exception:
                pass

        if cf is not None and not cf.empty:
            # cashflow is a DataFrame with dates as columns, items as rows
            # Take the most recent annual column
            latest = cf.iloc[:, 0]

            # Operating Cash Flow — try several label variants
            ocf = None
            for label in [
                "Total Cash From Operating Activities",
                "Operating Cash Flow",
                "Cash Flow From Continuing Operating Activities",
            ]:
                if label in latest.index:
                    ocf = latest[label]
                    break

            # Capital Expenditure (usually negative in statements)
            capex = None
            for label in [
                "Capital Expenditure",
                "Capital Expenditures",
            ]:
                if label in latest.index:
                    capex = latest[label]
                    break

            if ocf is not None and not np.isnan(ocf):
                result["ocf"] = float(ocf)
            if capex is not None and not np.isnan(capex):
                result["capex"] = float(capex)

        # Fallback: use info dict if cash flow statement was empty
        if np.isnan(result["ocf"]):
            ocf_info = info.get("operatingCashflow")
            if ocf_info:
                result["ocf"] = float(ocf_info)

        if np.isnan(result["capex"]):
            # yfinance info often has freeCashflow but not raw capex
            fcf_info = info.get("freeCashflow")
            if fcf_info and not np.isnan(result["ocf"]):
                # Derive capex = OCF - FCF
                result["capex"] = result["ocf"] - float(fcf_info)
            elif fcf_info:
                # No OCF either — just use FCF directly
                result["fcf"] = float(fcf_info)

        # Compute FCF if we have both components
        if not np.isnan(result["ocf"]) and not np.isnan(result["capex"]):
            # capex is typically negative; FCF = OCF + capex (where capex < 0)
            result["fcf"] = result["ocf"] + result["capex"]
        elif np.isnan(result["fcf"]):
            # Last resort: info.freeCashflow
            fcf_info = info.get("freeCashflow")
            if fcf_info:
                result["fcf"] = float(fcf_info)

        # Quick GG = FCF / Market Cap
        if not np.isnan(result["fcf"]) and mktcap > 0:
            result["quick_gg"] = result["fcf"] / mktcap
        else:
            result["error"] = "insufficient cash flow data"

    except Exception as exc:
        result["error"] = str(exc)[:80]

    return result


def run_tier15(
    df_tier1: pd.DataFrame,
    batch_size: int = 25,
    inter_batch_pause: float = 5.0,
    inter_ticker_pause: float = 0.6,
) -> pd.DataFrame:
    """Execute Tier 1.5: Quick GG scan for every Tier 1 candidate.

    Fetches OCF, capex, FCF from yfinance and computes:
        quick_gg = FCF / MarketCap   (approximate Greenblatt Gauge)

    Args:
        df_tier1: Tier 1 candidates (must have a 'ticker' column).
        batch_size: How many tickers to process before pausing.
        inter_batch_pause: Seconds to sleep between batches.
        inter_ticker_pause: Seconds to sleep between individual API calls.

    Returns:
        df_tier1 augmented with quick_gg and supporting columns, sorted by
        quick_gg descending.
    """
    try:
        import yfinance  # noqa: F401 — verify availability early
    except ImportError:
        print(
            "  ERROR: yfinance is required for --with-gg.  "
            "Run:  pip install yfinance",
            file=sys.stderr,
        )
        return df_tier1

    print(f"\n{'='*80}")
    print("TIER 1.5 — Quick GG Scan")
    print(f"{'='*80}")

    tickers = df_tier1["ticker"].tolist()
    total = len(tickers)
    print(f"  Scanning {total} tickers  (batch_size={batch_size})")
    t0 = time.time()

    # Use disk cache to avoid redundant yfinance calls
    _cache = DataCache()

    gg_records: List[Dict[str, Any]] = []
    errors = 0

    for i, ticker in enumerate(tickers, start=1):
        # Progress
        pct = i / total * 100
        elapsed = time.time() - t0
        eta = (elapsed / i) * (total - i) if i > 0 else 0
        print(
            f"  [{i:3d}/{total}] {ticker:<6s}  "
            f"({pct:5.1f}%)  elapsed={elapsed:.0f}s  eta={eta:.0f}s",
            end="",
        )

        rec = _fetch_gg_for_ticker(ticker, cache=_cache)
        gg_records.append(rec)

        if rec["error"]:
            print(f"  -> SKIP ({rec['error']})")
            errors += 1
        else:
            gg_pct = rec["quick_gg"] * 100
            print(f"  -> GG={gg_pct:+.2f}%")

        # Pause between tickers to respect rate limits
        if i < total:
            if i % batch_size == 0:
                print(f"  --- batch pause ({inter_batch_pause}s) ---")
                time.sleep(inter_batch_pause)
            else:
                time.sleep(inter_ticker_pause)

    elapsed_total = time.time() - t0
    stats = _cache.stats()
    print(f"\n  GG scan complete: {total} tickers in {elapsed_total:.1f}s  "
          f"({errors} errors, cache: {stats['hits']} hits / {stats['misses']} misses)")

    # Merge GG data into tier1 dataframe
    df_gg = pd.DataFrame(gg_records)
    df_merged = df_tier1.merge(
        df_gg[["ticker", "ocf", "capex", "fcf", "market_cap_yf", "quick_gg", "error"]],
        on="ticker",
        how="left",
        suffixes=("", "_gg"),
    )

    # Sort by quick_gg descending (NaN goes to bottom)
    df_merged = df_merged.sort_values("quick_gg", ascending=False, na_position="last")
    df_merged = df_merged.reset_index(drop=True)

    # Summary stats
    valid_gg = df_merged["quick_gg"].dropna()
    if len(valid_gg) > 0:
        print(f"  GG range: {valid_gg.min()*100:.2f}% .. {valid_gg.max()*100:.2f}%")
        print(f"  GG median: {valid_gg.median()*100:.2f}%")
        threshold_ii = DEFAULT_CONFIG.threshold_ii
        above = (valid_gg >= threshold_ii).sum()
        print(f"  Above Threshold II ({threshold_ii*100:.1f}%): {above} stocks")

    return df_merged


# ============================================================================
#  Display
# ============================================================================

def display_results(df: pd.DataFrame, title: str, limit: int = 50):
    """Pretty-print a results table to stdout."""
    print(f"\n{'='*150}")
    print(f"{title}  ({min(limit, len(df))} of {len(df)} shown)")
    print(f"{'='*150}")

    if df.empty:
        print("  (no results)")
        return

    show = df.head(limit).copy()
    show.insert(0, "rank", range(1, len(show) + 1))

    # Formatters
    def _fb(x):
        return f"${x:.1f}B" if pd.notna(x) else "--"

    def _fn(x):
        return f"{x:.2f}" if pd.notna(x) else "--"

    def _fp(x):
        return f"{x:.1f}%" if pd.notna(x) else "--"

    def _fgg(x):
        return f"{x*100:+.2f}%" if pd.notna(x) else "--"

    has_gg = "quick_gg" in show.columns

    # Header
    hdr = (
        f"{'#':>3}  {'Ticker':<7} {'Name':<32} {'Sector':<18} "
        f"{'MktCap':>8} {'PE':>6} {'PB':>6} {'ROE':>7} {'GrossM':>7} "
        f"{'DivY':>6} {'YTD':>7} {'Score':>6}"
    )
    if has_gg:
        hdr += f"  {'QuickGG':>8}"
    print(hdr)
    print("-" * (150 if has_gg else 140))

    for _, r in show.iterrows():
        name_short = str(r.get("name", r["ticker"]))[:30]
        sector_short = str(r.get("sector", "--"))[:16]
        line = (
            f"{r['rank']:>3}  {r['ticker']:<7} {name_short:<32} {sector_short:<18} "
            f"{_fb(r.get('market_cap_b')):>8} "
            f"{_fn(r.get('pe')):>6} {_fn(r.get('pb')):>6} "
            f"{_fp(r.get('roe')):>7} {_fp(r.get('gross_margin')):>7} "
            f"{_fp(r.get('div_yield')):>6} {_fp(r.get('perf_ytd')):>7} "
            f"{_fn(r.get('score')):>6}"
        )
        if has_gg:
            line += f"  {_fgg(r.get('quick_gg')):>8}"
        print(line)

    print(f"{'='*150}\n")


# ============================================================================
#  File I/O
# ============================================================================

# Columns saved in each tier file
_TIER1_COLS = [
    "ticker", "name", "sector", "industry", "country", "score",
    "market_cap_b", "price", "pe", "pb", "ps",
    "roe", "roa", "roic",
    "gross_margin", "op_margin", "net_margin",
    "current_ratio", "quick_ratio", "debt_equity", "lt_debt_equity",
    "div_yield", "eps", "eps_growth",
    "perf_ytd", "perf_year", "beta", "volume",
]

_GG_EXTRA_COLS = [
    "ocf", "capex", "fcf", "market_cap_yf", "quick_gg",
]


def _save_csv(df: pd.DataFrame, filename: str, extra_cols: Optional[List[str]] = None):
    """Save a DataFrame to output/screen/<filename>, selecting relevant columns."""
    out_dir = _ensure_output_dir()
    path = os.path.join(out_dir, filename)

    cols = list(_TIER1_COLS)
    if extra_cols:
        cols.extend(extra_cols)
    cols = [c for c in cols if c in df.columns]

    df[cols].to_csv(path, index=False, float_format="%.6f")
    print(f"  Saved {path}  ({len(df)} rows, {len(cols)} columns)")
    return path


def save_tier1(df: pd.DataFrame) -> str:
    return _save_csv(df, "tier1_candidates.csv")


def save_tier1_with_gg(df: pd.DataFrame) -> str:
    return _save_csv(df, "tier1_with_gg.csv", extra_cols=_GG_EXTRA_COLS)


def save_tier2_shortlist(df: pd.DataFrame, top_n: int = 10) -> str:
    """Save the top-N shortlist for deep analysis."""
    shortlist = df.head(top_n).copy()
    path = _save_csv(shortlist, "tier2_shortlist.csv", extra_cols=_GG_EXTRA_COLS)
    return path


# ============================================================================
#  CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="US Equity Quality Yield Strategy — Finviz Screener + Quick GG Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s                                          # Tier 1 only
  %(prog)s --with-gg                                # Tier 1 + GG scan
  %(prog)s --with-gg --top-n 10                     # Full pipeline
  %(prog)s --custom-filter "cap_largeover,fa_pe_u20" --with-gg
  %(prog)s --tier1-limit 30 --with-gg --top-n 5
""",
    )

    # --- Pipeline control ---
    parser.add_argument(
        "--with-gg",
        action="store_true",
        help="Run Tier 1.5 Quick GG scan after Finviz screening",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Select top N for tier2 shortlist (implies --with-gg if GG data available)",
    )

    # --- Finviz options ---
    parser.add_argument(
        "--custom-filter",
        help='Custom Finviz filter string (e.g. "cap_largeover,fa_pe_u20")',
    )
    parser.add_argument(
        "--tier1-limit",
        type=int,
        default=DEFAULT_CONFIG.tier1_limit,
        help=f"Max candidates from Tier 1 (default: {DEFAULT_CONFIG.tier1_limit})",
    )

    # --- GG scan tuning ---
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Tickers per batch in GG scan (default: 25)",
    )

    # --- Display ---
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the results table (still writes CSVs)",
    )

    return parser.parse_args()


# ============================================================================
#  Main
# ============================================================================

def main() -> None:
    args = parse_args()

    print("=" * 80)
    print("US EQUITY QUALITY YIELD STRATEGY — Screening Pipeline")
    print(f"Started: {_now_stamp()}")
    print("=" * 80)
    t_start = time.time()

    # ---- Tier 1 ----
    df_tier1 = run_tier1(
        custom_filter=args.custom_filter,
        limit=args.tier1_limit,
    )

    if df_tier1.empty:
        print("\nNo candidates survived Tier 1.  Exiting.")
        sys.exit(0)

    tier1_path = save_tier1(df_tier1)
    if not args.quiet:
        display_results(df_tier1, "TIER 1 — Finviz Candidates", limit=args.tier1_limit)

    # ---- Tier 1.5 (optional) ----
    df_with_gg = None
    if args.with_gg or args.top_n is not None:
        df_with_gg = run_tier15(df_tier1, batch_size=args.batch_size)
        gg_path = save_tier1_with_gg(df_with_gg)
        if not args.quiet:
            display_results(df_with_gg, "TIER 1.5 — With Quick GG", limit=args.tier1_limit)

    # ---- Tier 2 shortlist ----
    top_n = args.top_n or DEFAULT_CONFIG.tier2_limit
    if df_with_gg is not None:
        shortlist_path = save_tier2_shortlist(df_with_gg, top_n=top_n)
        shortlist = df_with_gg.head(top_n)
    else:
        shortlist_path = save_tier2_shortlist(df_tier1, top_n=top_n)
        shortlist = df_tier1.head(top_n)

    if not args.quiet:
        display_results(shortlist, f"TIER 2 SHORTLIST — Top {top_n}", limit=top_n)

    # ---- Summary ----
    elapsed = time.time() - t_start
    print(f"\n{'='*80}")
    print("Pipeline Summary")
    print(f"{'='*80}")
    print(f"  Tier 1 candidates : {len(df_tier1)}")
    if df_with_gg is not None:
        valid_gg = df_with_gg["quick_gg"].dropna()
        print(f"  GG scanned        : {len(valid_gg)} (of {len(df_with_gg)})")
        threshold = DEFAULT_CONFIG.threshold_ii
        above = (valid_gg >= threshold).sum()
        print(f"  Above Threshold II: {above}  ({threshold*100:.1f}%)")
    print(f"  Shortlist (top {top_n}) : {len(shortlist)}")
    print(f"  Total time        : {elapsed:.1f}s")
    print(f"\nOutput files:")
    print(f"  {tier1_path}")
    if df_with_gg is not None:
        print(f"  {gg_path}")
    print(f"  {shortlist_path}")
    print(f"\nDone.  [{_now_stamp()}]")


if __name__ == "__main__":
    main()
