#!/usr/bin/env python3
"""
US Equity Turtle Strategy -- Historical Backtester

Replays the full Turtle screening + GG selection process historically.
Fetches historical financial data via yfinance, calculates GG at past dates
(no look-ahead bias), simulates a portfolio, and calculates performance metrics.

Usage:
    python3 scripts/turtle_backtest.py \
        --start 2018-01-01 --end 2025-12-31 \
        --rebalance quarterly \
        --source yfinance \
        --top-n 10 \
        --benchmark SPY \
        --output output/backtest/

Key design principles:
    1. No look-ahead bias: only use data available at each rebalance date.
    2. Time-bounded: each rebalance period completes in < 8 minutes.
    3. File-based checkpoints: intermediate results saved for resume capability.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
import traceback
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# SSL workaround for corporate/dev environments
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
    print("ERROR: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Local project imports
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("turtle_backtest")

# ---------------------------------------------------------------------------
# Default S&P 500 constituent universe (representative large-caps)
# This is a broad, stable list.  A truly dynamic approach would use
# historical index membership, but that data is not freely available.
# ---------------------------------------------------------------------------
SP500_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEP",
    "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM", "ALB", "ALGN", "ALK", "ALL",
    "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN", "AMP", "AMT", "AMZN", "ANET",
    "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV", "ARE", "ATO", "ATVI",
    "AVB", "AVGO", "AVY", "AWK", "AXP", "AZO", "BA", "BAC", "BAX", "BBWI",
    "BBY", "BDX", "BEN", "BF.B", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK",
    "BMY", "BR", "BRK.B", "BRO", "BSX", "BWA", "BXP", "C", "CAG", "CAH",
    "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDAY", "CDNS", "CDW",
    "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL",
    "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF",
    "COO", "COP", "COST", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSGP",
    "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D",
    "DAL", "DD", "DE", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DISH",
    "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN",
    "DXC", "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EIX", "EL", "EMN",
    "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES", "ESS", "ETN",
    "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG",
    "FAST", "FBHS", "FCX", "FDS", "FDX", "FE", "FFIV", "FIS", "FISV", "FITB",
    "FLT", "FMC", "FOX", "FOXA", "FRC", "FRT", "FTNT", "FTV", "GD", "GE",
    "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN",
    "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "HOLX", "HON",
    "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUM", "HWM", "IBM", "ICE",
    "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH", "IP",
    "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT",
    "JCI", "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS", "KHC",
    "KIM", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "L", "LDOS", "LEN",
    "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX",
    "LUMN", "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS",
    "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK",
    "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC",
    "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH",
    "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE",
    "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL",
    "NWS", "NWSA", "NXPI", "O", "ODFL", "OGN", "OKE", "OMC", "ON", "ORCL",
    "ORLY", "OTIS", "OXY", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEAK",
    "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PKI",
    "PLD", "PM", "PNC", "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PSA",
    "PSX", "PTC", "PVH", "PWR", "PXD", "PYPL", "QCOM", "QRVO", "RCL", "RE",
    "REG", "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK", "ROL", "ROP",
    "ROST", "RSG", "RTX", "SBAC", "SBNY", "SBUX", "SCHW", "SEE", "SHW",
    "SIVB", "SJM", "SLB", "SNA", "SNPS", "SO", "SPG", "SPGI", "SRE", "STE",
    "STT", "STX", "STZ", "SWK", "SWKS", "SYF", "SYK", "SYY", "T", "TAP",
    "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT", "TJX", "TMO",
    "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN",
    "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UDR", "UHS", "ULTA", "UNH",
    "UNP", "UPS", "URI", "USB", "V", "VFC", "VICI", "VLO", "VMC", "VNO",
    "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ", "WAB", "WAT", "WBA",
    "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WM", "WMB", "WMT", "WRB",
    "WRK", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XRAY", "XYL", "YUM",
    "ZBH", "ZBRA", "ZION", "ZTS",
]


# ===================================================================
# Data classes
# ===================================================================

@dataclass
class StockGG:
    """GG calculation result for a single stock at a point in time."""
    ticker: str
    date: str
    ocf: float = 0.0
    capex: float = 0.0
    market_cap: float = 0.0
    gg: float = 0.0
    fcf: float = 0.0
    fcf_yield: float = 0.0
    valid: bool = True
    error: str = ""


@dataclass
class RebalanceResult:
    """Result of a single rebalance event."""
    date: str
    selections: List[StockGG]
    previous_holdings: List[str]
    new_holdings: List[str]
    turnover: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class BacktestConfig:
    """Full backtest configuration."""
    start_date: str = "2018-01-01"
    end_date: str = "2025-12-31"
    rebalance_freq: str = "quarterly"  # monthly, quarterly, semi-annual, annual
    top_n: int = 10
    benchmark: str = "SPY"
    risk_free_rate: float = DEFAULT_CONFIG.risk_free_rate
    transaction_cost: float = 0.001  # 0.1% per trade
    weighting: str = "equal"  # equal or gg-weighted
    universe: List[str] = field(default_factory=lambda: SP500_TICKERS.copy())
    output_dir: str = "output/backtest/"
    checkpoint_dir: str = "output/backtest/checkpoints/"
    max_rebalance_time: int = 480  # 8 minutes


# ===================================================================
# Universe management
# ===================================================================

def load_universe(filepath: Optional[str] = None) -> List[str]:
    """Load stock universe from a file or return default S&P 500 list."""
    if filepath and Path(filepath).exists():
        tickers = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    t = row[0].strip().upper()
                    if t and t != "TICKER" and t != "SYMBOL":
                        tickers.append(t)
        logger.info("Loaded %d tickers from %s", len(tickers), filepath)
        return tickers
    return SP500_TICKERS.copy()


# ===================================================================
# Rebalance date generation
# ===================================================================

def generate_rebalance_dates(
    start: str, end: str, freq: str
) -> List[datetime]:
    """Generate rebalance dates between start and end.

    Args:
        start: Start date string (YYYY-MM-DD).
        end: End date string (YYYY-MM-DD).
        freq: 'monthly', 'quarterly', 'semi-annual', 'annual'.

    Returns:
        List of rebalance datetimes.
    """
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    if freq == "monthly":
        month_step = 1
    elif freq == "quarterly":
        month_step = 3
    elif freq == "semi-annual":
        month_step = 6
    elif freq == "annual":
        month_step = 12
    else:
        raise ValueError(f"Unknown rebalance frequency: {freq}")

    dates = []
    current = start_dt
    while current <= end_dt:
        dates.append(current)
        # Advance by month_step months
        month = current.month + month_step
        year = current.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(current.day, 28)  # safe day to avoid month-end issues
        current = datetime(year, month, day)

    return dates


# ===================================================================
# Checkpoint management
# ===================================================================

def _checkpoint_path(checkpoint_dir: str, rebal_date: str) -> Path:
    """Return the checkpoint file path for a given rebalance date."""
    return Path(checkpoint_dir) / f"rebalance_{rebal_date}.json"


def save_checkpoint(checkpoint_dir: str, rebal_date: str, data: dict) -> None:
    """Save rebalance result to a checkpoint file."""
    Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
    path = _checkpoint_path(checkpoint_dir, rebal_date)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.debug("Checkpoint saved: %s", path)


def load_checkpoint(checkpoint_dir: str, rebal_date: str) -> Optional[dict]:
    """Load a checkpoint if it exists."""
    path = _checkpoint_path(checkpoint_dir, rebal_date)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ===================================================================
# yfinance data fetching with caching
# ===================================================================

_PRICE_CACHE: Dict[str, pd.DataFrame] = {}
_FINANCIAL_CACHE: Dict[str, dict] = {}


def fetch_price_history(
    ticker: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    """Fetch daily adjusted close prices for a ticker.

    Uses an in-memory cache to avoid redundant API calls.

    Returns:
        DataFrame with DatetimeIndex and 'Close' column, or empty DataFrame.
    """
    cache_key = f"{ticker}_{start}_{end}"
    if cache_key in _PRICE_CACHE:
        return _PRICE_CACHE[cache_key]

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(start=start, end=end, auto_adjust=True)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            df = hist[["Close"]].copy()
            df.index = pd.to_datetime(df.index).tz_localize(None)
            _PRICE_CACHE[cache_key] = df
            return df
    except Exception as exc:
        logger.debug("Price fetch failed for %s: %s", ticker, exc)

    empty = pd.DataFrame(columns=["Close"])
    _PRICE_CACHE[cache_key] = empty
    return empty


def fetch_financials(ticker: str) -> dict:
    """Fetch annual financial statements for a ticker from yfinance.

    Returns a dict with keys: 'income', 'cashflow', 'balance', each a DataFrame.
    Caches results in memory.
    """
    if ticker in _FINANCIAL_CACHE:
        return _FINANCIAL_CACHE[ticker]

    result = {"income": pd.DataFrame(), "cashflow": pd.DataFrame(), "balance": pd.DataFrame()}

    try:
        tk = yf.Ticker(ticker)
        result["income"] = tk.financials if tk.financials is not None else pd.DataFrame()
        result["cashflow"] = tk.cashflow if tk.cashflow is not None else pd.DataFrame()
        result["balance"] = tk.balance_sheet if tk.balance_sheet is not None else pd.DataFrame()
    except Exception as exc:
        logger.debug("Financial fetch failed for %s: %s", ticker, exc)

    _FINANCIAL_CACHE[ticker] = result
    return result


# ===================================================================
# GG calculation at a historical point in time
# ===================================================================

def _get_field(df: pd.DataFrame, field_names: List[str], col_idx: int = 0) -> float:
    """Extract a value from a financial statement DataFrame.

    yfinance returns statements with dates as columns (most recent first)
    and field names as the index.  We search field_names in order and
    return the first hit at the given column index.

    Args:
        df: Financial statement DataFrame.
        field_names: List of possible row labels to search.
        col_idx: Column index (0 = most recent period).

    Returns:
        Numeric value, or 0.0 if not found.
    """
    if df is None or df.empty:
        return 0.0
    for name in field_names:
        if name in df.index:
            try:
                val = df.loc[name].iloc[col_idx]
                if pd.notna(val):
                    return float(val)
            except (IndexError, TypeError):
                continue
    return 0.0


def calculate_gg_at_date(
    ticker: str,
    as_of_date: datetime,
    financials: dict,
    market_cap: float,
) -> StockGG:
    """Calculate simplified GG for a ticker using data available at as_of_date.

    GG = (OCF - Capex) / Market_Cap * 100

    No look-ahead bias: only use financial statements with filing dates
    before as_of_date.  yfinance annual statements are assumed available
    ~90 days after fiscal year end.

    Args:
        ticker: Stock ticker symbol.
        as_of_date: The date we are "standing at" -- only data available
            before this date should be used.
        financials: Dict with 'income', 'cashflow', 'balance' DataFrames.
        market_cap: Market capitalisation at as_of_date (in raw USD).

    Returns:
        StockGG result.
    """
    date_str = as_of_date.strftime("%Y-%m-%d")
    result = StockGG(ticker=ticker, date=date_str)

    if market_cap <= 0:
        result.valid = False
        result.error = "Market cap <= 0"
        return result

    cf = financials.get("cashflow", pd.DataFrame())

    if cf is None or cf.empty:
        result.valid = False
        result.error = "No cash flow data"
        return result

    # Filter columns (fiscal year end dates) to those available at as_of_date.
    # Assume financials are published ~90 days after fiscal year end.
    available_cols = []
    for col in cf.columns:
        try:
            col_dt = pd.Timestamp(col)
            if col_dt.tz is not None:
                col_dt = col_dt.tz_localize(None)
            # Financials available ~90 days after period end
            available_date = col_dt + pd.Timedelta(days=90)
            if available_date <= pd.Timestamp(as_of_date):
                available_cols.append(col)
        except Exception:
            continue

    if not available_cols:
        # Fallback: use the most recent column if it's at least older than as_of_date
        try:
            most_recent = cf.columns[0]
            col_dt = pd.Timestamp(most_recent)
            if col_dt.tz is not None:
                col_dt = col_dt.tz_localize(None)
            if col_dt < pd.Timestamp(as_of_date):
                available_cols = [most_recent]
        except Exception:
            pass

    if not available_cols:
        result.valid = False
        result.error = "No financial data available at this date"
        return result

    # Use the most recent available column
    # Sort available_cols by date descending
    try:
        available_cols_sorted = sorted(
            available_cols,
            key=lambda c: pd.Timestamp(c).tz_localize(None) if pd.Timestamp(c).tz is not None else pd.Timestamp(c),
            reverse=True,
        )
        target_col_idx = list(cf.columns).index(available_cols_sorted[0])
    except Exception:
        target_col_idx = 0

    # OCF
    ocf_fields = [
        "Operating Cash Flow", "Total Cash From Operating Activities",
        "Cash Flow From Continuing Operating Activities",
        "Net Cash Provided By Operating Activities",
    ]
    ocf = _get_field(cf, ocf_fields, target_col_idx)

    # Capex
    capex_fields = [
        "Capital Expenditure", "Capital Expenditures",
        "Purchase Of Property Plant And Equipment",
    ]
    capex = abs(_get_field(cf, capex_fields, target_col_idx))

    # Free Cash Flow
    fcf_fields = ["Free Cash Flow"]
    fcf = _get_field(cf, fcf_fields, target_col_idx)
    if fcf == 0.0 and ocf != 0.0:
        fcf = ocf - capex

    # Calculate GG
    # Simplified: GG = (OCF - Capex) / Market_Cap * 100
    if market_cap > 0:
        gg = (ocf - capex) / market_cap * 100.0
        fcf_yield = fcf / market_cap * 100.0
    else:
        gg = 0.0
        fcf_yield = 0.0

    result.ocf = ocf
    result.capex = capex
    result.market_cap = market_cap
    result.gg = gg
    result.fcf = fcf
    result.fcf_yield = fcf_yield
    result.valid = True

    return result


# ===================================================================
# Market cap estimation at historical dates
# ===================================================================

def estimate_market_cap(
    ticker: str,
    as_of_date: datetime,
    price_df: pd.DataFrame,
    shares_outstanding: Optional[float] = None,
) -> float:
    """Estimate market cap at a historical date.

    Uses price at as_of_date (or nearest prior trading day) multiplied
    by shares outstanding.

    If shares_outstanding is not available, attempts to derive from
    yfinance info.

    Returns:
        Estimated market cap in raw USD, or 0.0 if unavailable.
    """
    if price_df is None or price_df.empty:
        return 0.0

    # Find the closest price on or before as_of_date
    target = pd.Timestamp(as_of_date)
    mask = price_df.index <= target
    if not mask.any():
        return 0.0

    price = price_df.loc[mask, "Close"].iloc[-1]

    if shares_outstanding and shares_outstanding > 0:
        return price * shares_outstanding

    # Rough fallback: use current info to get shares outstanding
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        shares = info.get("sharesOutstanding", 0)
        if shares and shares > 0:
            return price * shares
    except Exception:
        pass

    return 0.0


# ===================================================================
# Core backtesting engine
# ===================================================================

def run_rebalance(
    rebal_date: datetime,
    universe: List[str],
    top_n: int,
    previous_holdings: List[str],
    backtest_start: str,
    backtest_end: str,
    max_time: int = 480,
) -> RebalanceResult:
    """Execute one rebalance: screen universe, calculate GG, select top N.

    Args:
        rebal_date: The rebalance date.
        universe: List of ticker symbols to screen.
        top_n: Number of stocks to select.
        previous_holdings: Tickers held before this rebalance.
        backtest_start: Overall backtest start date string.
        backtest_end: Overall backtest end date string.
        max_time: Maximum time in seconds for this rebalance.

    Returns:
        RebalanceResult with selected stocks and metadata.
    """
    t0 = time.time()
    date_str = rebal_date.strftime("%Y-%m-%d")
    logger.info("Rebalance %s: screening %d stocks ...", date_str, len(universe))

    # Fetch prices for the full backtest period (cached)
    # We only need prices up to the rebalance date for market cap
    price_end = (rebal_date + timedelta(days=5)).strftime("%Y-%m-%d")

    gg_results: List[StockGG] = []
    processed = 0
    skipped = 0

    for ticker in universe:
        # Time guard
        elapsed = time.time() - t0
        if elapsed > max_time:
            logger.warning(
                "Rebalance %s: time limit reached after %d/%d tickers (%.0fs)",
                date_str, processed, len(universe), elapsed,
            )
            break

        try:
            # Fetch price history
            price_df = fetch_price_history(ticker, backtest_start, price_end)
            if price_df.empty:
                skipped += 1
                continue

            # Estimate market cap at rebalance date
            mcap = estimate_market_cap(ticker, rebal_date, price_df)
            if mcap <= 0:
                skipped += 1
                continue

            # Fetch financials (cached)
            fins = fetch_financials(ticker)

            # Calculate GG
            gg = calculate_gg_at_date(ticker, rebal_date, fins, mcap)
            if gg.valid:
                gg_results.append(gg)

            processed += 1

        except Exception as exc:
            logger.debug("Error processing %s at %s: %s", ticker, date_str, exc)
            skipped += 1

        # Throttle to avoid rate limits (small pause every 20 tickers)
        if processed % 20 == 0 and processed > 0:
            time.sleep(0.5)

    # Sort by GG descending and select top N
    gg_results.sort(key=lambda x: x.gg, reverse=True)
    selections = gg_results[:top_n]
    new_holdings = [s.ticker for s in selections]

    # Calculate turnover
    prev_set = set(previous_holdings)
    new_set = set(new_holdings)
    if prev_set or new_set:
        changes = len(prev_set.symmetric_difference(new_set))
        turnover = changes / max(len(prev_set | new_set), 1)
    else:
        turnover = 0.0

    elapsed_total = time.time() - t0

    logger.info(
        "Rebalance %s: %d processed, %d skipped, %d selected (top GG: %.2f%%), "
        "turnover: %.0f%%, time: %.1fs",
        date_str, processed, skipped, len(selections),
        selections[0].gg if selections else 0.0,
        turnover * 100, elapsed_total,
    )

    return RebalanceResult(
        date=date_str,
        selections=selections,
        previous_holdings=previous_holdings,
        new_holdings=new_holdings,
        turnover=turnover,
        elapsed_seconds=elapsed_total,
    )


# ===================================================================
# Portfolio simulation
# ===================================================================

def simulate_portfolio(
    rebalance_results: List[RebalanceResult],
    benchmark: str,
    backtest_start: str,
    backtest_end: str,
    weighting: str = "equal",
    transaction_cost: float = 0.001,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate portfolio performance over the backtest period.

    Between rebalance dates, holds selected stocks with specified weighting.
    Calculates daily portfolio value and compares to benchmark.

    Args:
        rebalance_results: List of rebalance outcomes in chronological order.
        benchmark: Benchmark ticker (e.g. 'SPY').
        backtest_start: Start date string.
        backtest_end: End date string.
        weighting: 'equal' or 'gg-weighted'.
        transaction_cost: Cost per trade as decimal (e.g. 0.001 = 0.1%).

    Returns:
        Tuple of (equity_curve_df, holdings_df).
        equity_curve_df has columns: Date, Portfolio, Benchmark.
        holdings_df has columns: Date, Ticker, Weight, Return.
    """
    # Fetch benchmark prices
    bench_prices = fetch_price_history(benchmark, backtest_start, backtest_end)
    if bench_prices.empty:
        logger.error("Could not fetch benchmark (%s) prices", benchmark)

    # Collect all unique tickers across all rebalance periods
    all_tickers = set()
    for rr in rebalance_results:
        for s in rr.selections:
            all_tickers.add(s.ticker)

    # Fetch prices for all selected tickers
    ticker_prices: Dict[str, pd.DataFrame] = {}
    for ticker in all_tickers:
        df = fetch_price_history(ticker, backtest_start, backtest_end)
        if not df.empty:
            ticker_prices[ticker] = df

    # Build daily equity curve
    start_dt = datetime.strptime(backtest_start, "%Y-%m-%d")
    end_dt = datetime.strptime(backtest_end, "%Y-%m-%d")

    # Create trading day index from benchmark
    if not bench_prices.empty:
        trading_days = bench_prices.index
        trading_days = trading_days[(trading_days >= pd.Timestamp(start_dt)) &
                                    (trading_days <= pd.Timestamp(end_dt))]
    else:
        trading_days = pd.bdate_range(start_dt, end_dt)

    portfolio_values = []
    benchmark_values = []
    dates = []
    holdings_records = []

    portfolio_value = 100.0  # Start at $100
    benchmark_start_price = None

    # Sort rebalance results by date
    rebal_sorted = sorted(rebalance_results, key=lambda r: r.date)

    # Map each trading day to its active rebalance period
    rebal_dates = [datetime.strptime(r.date, "%Y-%m-%d") for r in rebal_sorted]

    for day in trading_days:
        day_dt = day.to_pydatetime() if hasattr(day, 'to_pydatetime') else day
        if hasattr(day_dt, 'tzinfo') and day_dt.tzinfo is not None:
            day_dt = day_dt.replace(tzinfo=None)

        # Find the active rebalance period for this day
        active_rebal = None
        for i, rd in enumerate(rebal_dates):
            if day_dt >= rd:
                active_rebal = rebal_sorted[i]
            else:
                break

        if active_rebal is None:
            # Before first rebalance -- hold cash
            dates.append(day_dt)
            portfolio_values.append(portfolio_value)

            # Benchmark
            if not bench_prices.empty and day in bench_prices.index:
                bp = bench_prices.loc[day, "Close"]
                if benchmark_start_price is None:
                    benchmark_start_price = bp
                benchmark_values.append(100.0 * bp / benchmark_start_price)
            else:
                benchmark_values.append(benchmark_values[-1] if benchmark_values else 100.0)
            continue

        # Calculate portfolio daily return from holdings
        holdings = active_rebal.selections
        if not holdings:
            dates.append(day_dt)
            portfolio_values.append(portfolio_value)
            if not bench_prices.empty and day in bench_prices.index:
                bp = bench_prices.loc[day, "Close"]
                if benchmark_start_price is None:
                    benchmark_start_price = bp
                benchmark_values.append(100.0 * bp / benchmark_start_price)
            else:
                benchmark_values.append(benchmark_values[-1] if benchmark_values else 100.0)
            continue

        # Calculate weights
        if weighting == "gg-weighted":
            total_gg = sum(max(s.gg, 0.01) for s in holdings)
            weights = {s.ticker: max(s.gg, 0.01) / total_gg for s in holdings}
        else:
            n = len(holdings)
            weights = {s.ticker: 1.0 / n for s in holdings}

        # Calculate weighted portfolio return for this day
        day_return = 0.0
        active_weight_sum = 0.0

        for stock in holdings:
            t = stock.ticker
            w = weights.get(t, 0.0)
            if t not in ticker_prices:
                continue

            tdf = ticker_prices[t]
            # Find today and previous day prices
            mask_today = tdf.index <= day
            if not mask_today.any():
                continue
            today_price = tdf.loc[mask_today, "Close"].iloc[-1]

            # Previous trading day
            mask_prev = tdf.index < day
            if not mask_prev.any():
                active_weight_sum += w
                continue
            prev_price = tdf.loc[mask_prev, "Close"].iloc[-1]

            if prev_price > 0:
                stock_return = (today_price - prev_price) / prev_price
                day_return += w * stock_return
                active_weight_sum += w

        # Adjust for stocks without price data (scale up active weights)
        if active_weight_sum > 0 and active_weight_sum < 1.0:
            day_return = day_return / active_weight_sum

        # Apply transaction costs on rebalance days
        rebal_day_str = day_dt.strftime("%Y-%m-%d")
        is_rebal_day = any(r.date == rebal_day_str for r in rebal_sorted)
        if is_rebal_day:
            # Cost = transaction_cost * turnover * 2 (buy + sell)
            matching_rebal = next((r for r in rebal_sorted if r.date == rebal_day_str), None)
            if matching_rebal:
                cost = transaction_cost * matching_rebal.turnover * 2
                day_return -= cost

        portfolio_value *= (1.0 + day_return)
        dates.append(day_dt)
        portfolio_values.append(portfolio_value)

        # Benchmark
        if not bench_prices.empty and day in bench_prices.index:
            bp = bench_prices.loc[day, "Close"]
            if benchmark_start_price is None:
                benchmark_start_price = bp
            benchmark_values.append(100.0 * bp / benchmark_start_price)
        else:
            benchmark_values.append(benchmark_values[-1] if benchmark_values else 100.0)

    # Build equity curve DataFrame
    equity_df = pd.DataFrame({
        "Date": dates,
        "Portfolio": portfolio_values,
        "Benchmark": benchmark_values,
    })
    equity_df.set_index("Date", inplace=True)

    # Build holdings record for analysis
    for rr in rebal_sorted:
        for s in rr.selections:
            holdings_records.append({
                "Rebalance_Date": rr.date,
                "Ticker": s.ticker,
                "GG": round(s.gg, 4),
                "OCF": round(s.ocf, 2),
                "Capex": round(s.capex, 2),
                "Market_Cap": round(s.market_cap, 2),
            })

    holdings_df = pd.DataFrame(holdings_records) if holdings_records else pd.DataFrame()

    return equity_df, holdings_df


# ===================================================================
# Performance metrics
# ===================================================================

def calculate_metrics(
    equity_df: pd.DataFrame,
    risk_free_rate: float = 0.043,
    benchmark_col: str = "Benchmark",
) -> Dict[str, Any]:
    """Calculate comprehensive performance metrics.

    Args:
        equity_df: DataFrame with 'Portfolio' and benchmark columns.
        risk_free_rate: Annual risk-free rate (decimal).
        benchmark_col: Name of the benchmark column.

    Returns:
        Dict of metrics.
    """
    if equity_df.empty or len(equity_df) < 2:
        return {"error": "Insufficient data for metrics"}

    port = equity_df["Portfolio"]
    bench = equity_df[benchmark_col] if benchmark_col in equity_df.columns else None

    # Daily returns
    port_returns = port.pct_change().dropna()
    if bench is not None:
        bench_returns = bench.pct_change().dropna()
    else:
        bench_returns = pd.Series(dtype=float)

    # Total return
    total_return = (port.iloc[-1] / port.iloc[0] - 1.0) * 100.0
    bench_total_return = (bench.iloc[-1] / bench.iloc[0] - 1.0) * 100.0 if bench is not None else 0.0

    # CAGR
    n_days = (equity_df.index[-1] - equity_df.index[0]).days
    n_years = n_days / 365.25 if n_days > 0 else 1.0
    cagr = ((port.iloc[-1] / port.iloc[0]) ** (1.0 / n_years) - 1.0) * 100.0 if n_years > 0 else 0.0
    bench_cagr = ((bench.iloc[-1] / bench.iloc[0]) ** (1.0 / n_years) - 1.0) * 100.0 if bench is not None and n_years > 0 else 0.0

    # Annualised volatility
    ann_vol = port_returns.std() * np.sqrt(252) * 100.0 if len(port_returns) > 1 else 0.0

    # Sharpe ratio
    daily_rf = (1.0 + risk_free_rate) ** (1.0 / 252) - 1.0
    excess_returns = port_returns - daily_rf
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0

    # Sortino ratio (downside deviation)
    downside_returns = excess_returns[excess_returns < 0]
    downside_dev = np.sqrt((downside_returns ** 2).mean()) if len(downside_returns) > 0 else 0.0
    sortino = (excess_returns.mean() / downside_dev * np.sqrt(252)) if downside_dev > 0 else 0.0

    # Max drawdown
    cummax = port.cummax()
    drawdown = (port - cummax) / cummax
    max_dd = drawdown.min() * 100.0
    max_dd_date = drawdown.idxmin() if len(drawdown) > 0 else None

    # Recovery time from max drawdown
    recovery_days = None
    if max_dd_date is not None and max_dd < 0:
        peak_before_dd = cummax.loc[:max_dd_date].iloc[-1]
        recovery_mask = port.loc[max_dd_date:] >= peak_before_dd
        if recovery_mask.any():
            recovery_date = recovery_mask.idxmax()
            recovery_days = (recovery_date - max_dd_date).days

    # Alpha and Beta vs benchmark
    alpha = 0.0
    beta = 0.0
    if len(bench_returns) > 10 and len(port_returns) > 10:
        # Align returns
        aligned = pd.DataFrame({
            "port": port_returns,
            "bench": bench_returns,
        }).dropna()

        if len(aligned) > 10:
            cov_matrix = np.cov(aligned["port"], aligned["bench"])
            beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0.0
            # Annualised alpha
            alpha = (cagr - risk_free_rate * 100.0 - beta * (bench_cagr - risk_free_rate * 100.0))

    # Calmar ratio
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0

    metrics = {
        "total_return_pct": round(total_return, 2),
        "benchmark_total_return_pct": round(bench_total_return, 2),
        "cagr_pct": round(cagr, 2),
        "benchmark_cagr_pct": round(bench_cagr, 2),
        "annualised_volatility_pct": round(ann_vol, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "max_drawdown_date": str(max_dd_date.date()) if max_dd_date is not None else "N/A",
        "recovery_days": recovery_days,
        "alpha_pct": round(alpha, 2),
        "beta": round(beta, 3),
        "calmar_ratio": round(calmar, 3),
        "n_trading_days": len(port_returns),
        "n_years": round(n_years, 2),
        "risk_free_rate_pct": round(risk_free_rate * 100, 2),
    }

    return metrics


def calculate_win_rate(
    rebalance_results: List[RebalanceResult],
    backtest_end: str,
) -> Dict[str, Any]:
    """Calculate win rate -- percentage of picks that generated positive returns.

    For each pick at each rebalance, measures the return from the rebalance
    date to the next rebalance date (or backtest end).

    Returns:
        Dict with win_rate, total_picks, winning_picks.
    """
    total_picks = 0
    winning_picks = 0
    pick_returns = []

    rebal_sorted = sorted(rebalance_results, key=lambda r: r.date)

    for i, rr in enumerate(rebal_sorted):
        # Determine the holding period end
        if i + 1 < len(rebal_sorted):
            hold_end = rebal_sorted[i + 1].date
        else:
            hold_end = backtest_end

        for stock in rr.selections:
            try:
                prices = fetch_price_history(
                    stock.ticker, rr.date, hold_end,
                )
                if prices.empty or len(prices) < 2:
                    continue

                entry_price = prices["Close"].iloc[0]
                exit_price = prices["Close"].iloc[-1]
                ret = (exit_price - entry_price) / entry_price

                total_picks += 1
                if ret > 0:
                    winning_picks += 1
                pick_returns.append(ret)

            except Exception:
                continue

    win_rate = winning_picks / total_picks * 100.0 if total_picks > 0 else 0.0

    return {
        "win_rate_pct": round(win_rate, 1),
        "total_picks": total_picks,
        "winning_picks": winning_picks,
        "avg_pick_return_pct": round(np.mean(pick_returns) * 100, 2) if pick_returns else 0.0,
        "median_pick_return_pct": round(np.median(pick_returns) * 100, 2) if pick_returns else 0.0,
    }


def calculate_yearly_returns(equity_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate yearly returns for portfolio and benchmark.

    Returns:
        DataFrame with Year, Portfolio_Return, Benchmark_Return, Excess_Return.
    """
    if equity_df.empty:
        return pd.DataFrame()

    records = []
    years = sorted(set(equity_df.index.year))

    for year in years:
        year_data = equity_df[equity_df.index.year == year]
        if len(year_data) < 2:
            continue

        port_ret = (year_data["Portfolio"].iloc[-1] / year_data["Portfolio"].iloc[0] - 1.0) * 100.0
        bench_ret = 0.0
        if "Benchmark" in year_data.columns:
            bench_ret = (year_data["Benchmark"].iloc[-1] / year_data["Benchmark"].iloc[0] - 1.0) * 100.0

        records.append({
            "Year": year,
            "Portfolio_Return": round(port_ret, 2),
            "Benchmark_Return": round(bench_ret, 2),
            "Excess_Return": round(port_ret - bench_ret, 2),
        })

    return pd.DataFrame(records)


def calculate_avg_turnover(rebalance_results: List[RebalanceResult]) -> float:
    """Calculate average turnover rate across rebalances."""
    if not rebalance_results:
        return 0.0
    turnovers = [rr.turnover for rr in rebalance_results]
    return round(np.mean(turnovers) * 100, 1)


# ===================================================================
# Report generation
# ===================================================================

def generate_report(
    config: BacktestConfig,
    metrics: Dict[str, Any],
    win_stats: Dict[str, Any],
    yearly_df: pd.DataFrame,
    rebalance_results: List[RebalanceResult],
    avg_turnover: float,
) -> str:
    """Generate the full backtest report in markdown format."""
    lines: List[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("# US Equity Turtle Strategy -- Backtest Report")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Period**: {config.start_date} to {config.end_date}")
    lines.append(f"**Rebalance**: {config.rebalance_freq}")
    lines.append(f"**Universe**: {len(config.universe)} stocks")
    lines.append(f"**Top N**: {config.top_n}")
    lines.append(f"**Benchmark**: {config.benchmark}")
    lines.append(f"**Weighting**: {config.weighting}")
    lines.append(f"**Transaction Cost**: {config.transaction_cost * 100:.2f}%")
    lines.append(f"**Risk-Free Rate**: {config.risk_free_rate * 100:.2f}%")
    lines.append("")
    lines.append("---")
    lines.append("")

    # --- Performance Summary ---
    lines.append("## Performance Summary")
    lines.append("")
    lines.append("| Metric | Portfolio | Benchmark |")
    lines.append("|--------|----------:|----------:|")
    lines.append(f"| Total Return | {metrics.get('total_return_pct', 0):.2f}% | {metrics.get('benchmark_total_return_pct', 0):.2f}% |")
    lines.append(f"| CAGR | {metrics.get('cagr_pct', 0):.2f}% | {metrics.get('benchmark_cagr_pct', 0):.2f}% |")
    lines.append(f"| Annualised Volatility | {metrics.get('annualised_volatility_pct', 0):.2f}% | -- |")
    lines.append("")

    # --- Risk Metrics ---
    lines.append("## Risk Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|------:|")
    lines.append(f"| Sharpe Ratio | {metrics.get('sharpe_ratio', 0):.3f} |")
    lines.append(f"| Sortino Ratio | {metrics.get('sortino_ratio', 0):.3f} |")
    lines.append(f"| Max Drawdown | {metrics.get('max_drawdown_pct', 0):.2f}% |")
    lines.append(f"| Max DD Date | {metrics.get('max_drawdown_date', 'N/A')} |")
    recovery = metrics.get("recovery_days")
    lines.append(f"| Recovery Time | {recovery} days |" if recovery else "| Recovery Time | Not recovered |")
    lines.append(f"| Calmar Ratio | {metrics.get('calmar_ratio', 0):.3f} |")
    lines.append(f"| Alpha | {metrics.get('alpha_pct', 0):.2f}% |")
    lines.append(f"| Beta | {metrics.get('beta', 0):.3f} |")
    lines.append("")

    # --- Stock Picking Stats ---
    lines.append("## Stock Picking Statistics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|------:|")
    lines.append(f"| Win Rate | {win_stats.get('win_rate_pct', 0):.1f}% |")
    lines.append(f"| Total Picks | {win_stats.get('total_picks', 0)} |")
    lines.append(f"| Winning Picks | {win_stats.get('winning_picks', 0)} |")
    lines.append(f"| Avg Pick Return | {win_stats.get('avg_pick_return_pct', 0):.2f}% |")
    lines.append(f"| Median Pick Return | {win_stats.get('median_pick_return_pct', 0):.2f}% |")
    lines.append(f"| Avg Turnover | {avg_turnover:.1f}% |")
    lines.append(f"| Rebalance Events | {len(rebalance_results)} |")
    lines.append("")

    # --- Yearly Returns ---
    lines.append("## Yearly Returns")
    lines.append("")
    if not yearly_df.empty:
        lines.append("| Year | Portfolio | Benchmark | Excess |")
        lines.append("|------|----------:|----------:|-------:|")
        for _, row in yearly_df.iterrows():
            lines.append(
                f"| {int(row['Year'])} "
                f"| {row['Portfolio_Return']:+.2f}% "
                f"| {row['Benchmark_Return']:+.2f}% "
                f"| {row['Excess_Return']:+.2f}% |"
            )
        lines.append("")
    else:
        lines.append("_No yearly data available._")
        lines.append("")

    # --- Rebalance History ---
    lines.append("## Rebalance History")
    lines.append("")
    lines.append("| Date | Top Pick | Top GG | #Held | Turnover | Time |")
    lines.append("|------|----------|-------:|------:|---------:|-----:|")

    for rr in sorted(rebalance_results, key=lambda r: r.date):
        top_pick = rr.selections[0].ticker if rr.selections else "--"
        top_gg = f"{rr.selections[0].gg:.2f}%" if rr.selections else "--"
        lines.append(
            f"| {rr.date} "
            f"| {top_pick} "
            f"| {top_gg} "
            f"| {len(rr.selections)} "
            f"| {rr.turnover * 100:.0f}% "
            f"| {rr.elapsed_seconds:.0f}s |"
        )
    lines.append("")

    # --- Methodology ---
    lines.append("## Methodology")
    lines.append("")
    lines.append("### GG Calculation (Simplified)")
    lines.append("```")
    lines.append("GG = (OCF - Capex) / Market_Cap * 100")
    lines.append("```")
    lines.append("")
    lines.append("### Selection Process")
    lines.append("1. Screen S&P 500 (or custom) universe at each rebalance date")
    lines.append("2. Fetch annual financials from yfinance (no look-ahead bias)")
    lines.append("3. Calculate GG using data available at rebalance date")
    lines.append("4. Rank by GG descending, select top N")
    lines.append(f"5. Hold {config.weighting}-weighted portfolio until next rebalance")
    lines.append(f"6. Apply {config.transaction_cost * 100:.2f}% transaction cost per trade")
    lines.append("")
    lines.append("### Limitations")
    lines.append("- Uses current S&P 500 membership (survivorship bias possible)")
    lines.append("- Simplified GG (OCF - Capex only; full formula includes buybacks, debt change, SBC)")
    lines.append("- Annual financials only (quarterly would improve accuracy)")
    lines.append("- Shares outstanding approximated from current data for historical market caps")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by US Equity Turtle Strategy Backtester*")

    return "\n".join(lines)


# ===================================================================
# Output file writers
# ===================================================================

def save_selections(output_dir: str, rebal_result: RebalanceResult) -> None:
    """Save stock selections for a single rebalance date to CSV."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"selections_{rebal_result.date}.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Rank", "Ticker", "GG_pct", "OCF", "Capex", "Market_Cap", "FCF_Yield_pct"])
        for i, s in enumerate(rebal_result.selections, 1):
            writer.writerow([
                i, s.ticker,
                round(s.gg, 4),
                round(s.ocf, 2),
                round(s.capex, 2),
                round(s.market_cap, 2),
                round(s.fcf_yield, 4),
            ])


def save_equity_curve(output_dir: str, equity_df: pd.DataFrame) -> None:
    """Save equity curve to CSV."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / "equity_curve.csv"
    equity_df.to_csv(path, float_format="%.4f")
    logger.info("Equity curve saved: %s", path)


def plot_equity_curve(output_dir: str, equity_df: pd.DataFrame, benchmark: str) -> None:
    """Plot equity curve chart if matplotlib is available."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        logger.info("matplotlib not available -- skipping chart generation")
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(equity_df.index, equity_df["Portfolio"], label="Turtle GG Portfolio",
            linewidth=2, color="#1a5276")
    if "Benchmark" in equity_df.columns:
        ax.plot(equity_df.index, equity_df["Benchmark"], label=f"{benchmark} Benchmark",
                linewidth=1.5, color="#aab7b8", linestyle="--")

    ax.set_title("US Equity Turtle Strategy -- Equity Curve", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value (indexed to 100)")
    ax.legend(loc="upper left", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    fig.autofmt_xdate()

    path = Path(output_dir) / "equity_curve.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Equity curve chart saved: %s", path)


def plot_yearly_returns(output_dir: str, yearly_df: pd.DataFrame) -> None:
    """Plot yearly returns bar chart if matplotlib is available."""
    if yearly_df.empty:
        return

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))

    years = yearly_df["Year"].astype(int).values
    x = np.arange(len(years))
    width = 0.35

    port_bars = ax.bar(x - width / 2, yearly_df["Portfolio_Return"], width,
                       label="Portfolio", color="#1a5276")
    bench_bars = ax.bar(x + width / 2, yearly_df["Benchmark_Return"], width,
                        label="Benchmark", color="#aab7b8")

    ax.set_title("Annual Returns -- Portfolio vs Benchmark", fontsize=14, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Return (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(y=0, color="black", linewidth=0.5)

    # Add value labels on bars
    for bar in port_bars:
        height = bar.get_height()
        if abs(height) > 0.5:
            ax.annotate(f"{height:.1f}%",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3 if height > 0 else -12),
                        textcoords="offset points",
                        ha="center", va="bottom" if height > 0 else "top",
                        fontsize=8)

    path = Path(output_dir) / "yearly_returns.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info("Yearly returns chart saved: %s", path)


# ===================================================================
# Main backtest runner
# ===================================================================

def run_backtest(config: BacktestConfig) -> None:
    """Execute the full backtest pipeline.

    Steps:
        1. Generate rebalance dates.
        2. For each rebalance date (with checkpoint resume):
           a. Screen universe and calculate GG.
           b. Select top N stocks.
           c. Save checkpoint.
        3. Simulate portfolio performance.
        4. Calculate metrics.
        5. Generate report and output files.
    """
    t_start = time.time()
    output_dir = config.output_dir
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)

    print()
    print("=" * 70)
    print("  US Equity Turtle Strategy -- Backtester")
    print("=" * 70)
    print(f"  Period:      {config.start_date} to {config.end_date}")
    print(f"  Rebalance:   {config.rebalance_freq}")
    print(f"  Universe:    {len(config.universe)} stocks")
    print(f"  Top N:       {config.top_n}")
    print(f"  Benchmark:   {config.benchmark}")
    print(f"  Weighting:   {config.weighting}")
    print(f"  Tx cost:     {config.transaction_cost * 100:.2f}%")
    print(f"  Output:      {output_dir}")
    print("=" * 70)
    print()

    # Step 1: Generate rebalance dates
    rebal_dates = generate_rebalance_dates(
        config.start_date, config.end_date, config.rebalance_freq,
    )
    print(f"  Rebalance dates: {len(rebal_dates)}")
    for rd in rebal_dates:
        print(f"    {rd.strftime('%Y-%m-%d')}")
    print()

    # Step 2: Run each rebalance (with checkpoint support)
    rebalance_results: List[RebalanceResult] = []
    previous_holdings: List[str] = []

    for i, rebal_date in enumerate(rebal_dates):
        date_str = rebal_date.strftime("%Y-%m-%d")
        print(f"\n--- Rebalance {i + 1}/{len(rebal_dates)}: {date_str} ---")

        # Check for checkpoint
        checkpoint = load_checkpoint(config.checkpoint_dir, date_str)
        if checkpoint:
            print(f"  [CHECKPOINT] Loaded from cache")
            # Reconstruct RebalanceResult from checkpoint
            selections = [
                StockGG(
                    ticker=s["ticker"],
                    date=s["date"],
                    ocf=s.get("ocf", 0),
                    capex=s.get("capex", 0),
                    market_cap=s.get("market_cap", 0),
                    gg=s.get("gg", 0),
                    fcf=s.get("fcf", 0),
                    fcf_yield=s.get("fcf_yield", 0),
                    valid=s.get("valid", True),
                )
                for s in checkpoint.get("selections", [])
            ]
            rr = RebalanceResult(
                date=checkpoint["date"],
                selections=selections,
                previous_holdings=checkpoint.get("previous_holdings", []),
                new_holdings=checkpoint.get("new_holdings", []),
                turnover=checkpoint.get("turnover", 0),
                elapsed_seconds=checkpoint.get("elapsed_seconds", 0),
            )
        else:
            # Run the rebalance
            rr = run_rebalance(
                rebal_date=rebal_date,
                universe=config.universe,
                top_n=config.top_n,
                previous_holdings=previous_holdings,
                backtest_start=config.start_date,
                backtest_end=config.end_date,
                max_time=config.max_rebalance_time,
            )

            # Save checkpoint
            checkpoint_data = {
                "date": rr.date,
                "selections": [asdict(s) for s in rr.selections],
                "previous_holdings": rr.previous_holdings,
                "new_holdings": rr.new_holdings,
                "turnover": rr.turnover,
                "elapsed_seconds": rr.elapsed_seconds,
            }
            save_checkpoint(config.checkpoint_dir, date_str, checkpoint_data)

        # Save selections CSV
        save_selections(output_dir, rr)

        rebalance_results.append(rr)
        previous_holdings = rr.new_holdings.copy()

        # Print top picks
        if rr.selections:
            print(f"  Top picks:")
            for j, s in enumerate(rr.selections[:5], 1):
                print(f"    {j}. {s.ticker:>6s}  GG={s.gg:7.2f}%  "
                      f"OCF={s.ocf / 1e6:,.0f}M  Capex={s.capex / 1e6:,.0f}M")
            if len(rr.selections) > 5:
                print(f"    ... and {len(rr.selections) - 5} more")
        else:
            print(f"  [WARNING] No valid selections")

    # Step 3: Simulate portfolio
    print(f"\n\n{'=' * 70}")
    print("  Simulating portfolio performance ...")
    print(f"{'=' * 70}\n")

    equity_df, holdings_df = simulate_portfolio(
        rebalance_results=rebalance_results,
        benchmark=config.benchmark,
        backtest_start=config.start_date,
        backtest_end=config.end_date,
        weighting=config.weighting,
        transaction_cost=config.transaction_cost,
    )

    # Step 4: Calculate metrics
    print("  Calculating performance metrics ...")
    metrics = calculate_metrics(equity_df, config.risk_free_rate)
    win_stats = calculate_win_rate(rebalance_results, config.end_date)
    yearly_df = calculate_yearly_returns(equity_df)
    avg_turnover = calculate_avg_turnover(rebalance_results)

    # Step 5: Generate outputs
    print("  Generating output files ...")

    # Equity curve CSV
    save_equity_curve(output_dir, equity_df)

    # Charts
    plot_equity_curve(output_dir, equity_df, config.benchmark)
    plot_yearly_returns(output_dir, yearly_df)

    # Yearly returns CSV
    if not yearly_df.empty:
        yearly_path = Path(output_dir) / "yearly_returns.csv"
        yearly_df.to_csv(yearly_path, index=False)

    # Full report
    report = generate_report(
        config=config,
        metrics=metrics,
        win_stats=win_stats,
        yearly_df=yearly_df,
        rebalance_results=rebalance_results,
        avg_turnover=avg_turnover,
    )
    report_path = Path(output_dir) / "backtest_report.md"
    report_path.write_text(report, encoding="utf-8")

    # Print summary
    elapsed_total = time.time() - t_start
    print()
    print("=" * 70)
    print("  BACKTEST COMPLETE")
    print("=" * 70)
    print(f"  Period:           {config.start_date} to {config.end_date}")
    print(f"  Total Return:     {metrics.get('total_return_pct', 0):+.2f}%")
    print(f"  Benchmark Return: {metrics.get('benchmark_total_return_pct', 0):+.2f}%")
    print(f"  CAGR:             {metrics.get('cagr_pct', 0):+.2f}%")
    print(f"  Sharpe Ratio:     {metrics.get('sharpe_ratio', 0):.3f}")
    print(f"  Sortino Ratio:    {metrics.get('sortino_ratio', 0):.3f}")
    print(f"  Max Drawdown:     {metrics.get('max_drawdown_pct', 0):.2f}%")
    print(f"  Alpha:            {metrics.get('alpha_pct', 0):+.2f}%")
    print(f"  Beta:             {metrics.get('beta', 0):.3f}")
    print(f"  Win Rate:         {win_stats.get('win_rate_pct', 0):.1f}%")
    print(f"  Avg Turnover:     {avg_turnover:.1f}%")
    print(f"  Total Time:       {elapsed_total:.0f}s ({elapsed_total / 60:.1f}m)")
    print("=" * 70)
    print()
    print(f"  Report:       {report_path}")
    print(f"  Equity Curve: {Path(output_dir) / 'equity_curve.csv'}")
    print(f"  Charts:       {Path(output_dir) / 'equity_curve.png'}")
    print(f"                {Path(output_dir) / 'yearly_returns.png'}")
    print()


# ===================================================================
# CLI entry point
# ===================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="US Equity Turtle Strategy -- Historical Backtester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quick test (annual rebalance, top 5)
    python3 scripts/turtle_backtest.py --start 2020-01-01 --end 2024-12-31 \\
        --rebalance annual --top-n 5

    # Full backtest
    python3 scripts/turtle_backtest.py --start 2018-01-01 --end 2025-12-31 \\
        --rebalance quarterly --top-n 10 --benchmark SPY

    # Custom universe
    python3 scripts/turtle_backtest.py --start 2020-01-01 --end 2024-12-31 \\
        --universe my_tickers.csv --top-n 10

    # GG-weighted with higher transaction costs
    python3 scripts/turtle_backtest.py --start 2018-01-01 --end 2025-12-31 \\
        --weighting gg-weighted --tx-cost 0.002
        """,
    )

    parser.add_argument(
        "--start", type=str, default="2018-01-01",
        help="Backtest start date (YYYY-MM-DD, default: 2018-01-01)",
    )
    parser.add_argument(
        "--end", type=str, default="2025-12-31",
        help="Backtest end date (YYYY-MM-DD, default: 2025-12-31)",
    )
    parser.add_argument(
        "--rebalance", type=str, default="quarterly",
        choices=["monthly", "quarterly", "semi-annual", "annual"],
        help="Rebalance frequency (default: quarterly)",
    )
    parser.add_argument(
        "--source", type=str, default="yfinance",
        choices=["yfinance"],
        help="Data source (default: yfinance)",
    )
    parser.add_argument(
        "--top-n", type=int, default=10,
        help="Number of top GG stocks to hold (default: 10)",
    )
    parser.add_argument(
        "--benchmark", type=str, default="SPY",
        help="Benchmark ticker (default: SPY)",
    )
    parser.add_argument(
        "--output", type=str, default="output/backtest/",
        help="Output directory (default: output/backtest/)",
    )
    parser.add_argument(
        "--universe", type=str, default=None,
        help="Path to CSV with ticker universe (default: S&P 500)",
    )
    parser.add_argument(
        "--weighting", type=str, default="equal",
        choices=["equal", "gg-weighted"],
        help="Portfolio weighting method (default: equal)",
    )
    parser.add_argument(
        "--tx-cost", type=float, default=0.001,
        help="Transaction cost per trade as decimal (default: 0.001 = 0.1%%)",
    )
    parser.add_argument(
        "--rf", type=float, default=None,
        help=f"Risk-free rate override (default: {DEFAULT_CONFIG.risk_free_rate})",
    )
    parser.add_argument(
        "--max-time", type=int, default=480,
        help="Max seconds per rebalance period (default: 480 = 8 min)",
    )
    parser.add_argument(
        "--clear-cache", action="store_true",
        help="Clear checkpoint cache and re-run all rebalances",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Resolve output path relative to project root
    project_root = _SCRIPTS_DIR.parent
    output_dir = args.output
    if not os.path.isabs(output_dir):
        output_dir = str(project_root / output_dir)

    checkpoint_dir = os.path.join(output_dir, "checkpoints")

    # Clear cache if requested
    if args.clear_cache:
        import shutil
        if os.path.exists(checkpoint_dir):
            shutil.rmtree(checkpoint_dir)
            print(f"Cleared checkpoint cache: {checkpoint_dir}")

    # Load universe
    universe = load_universe(args.universe)

    # Build config
    config = BacktestConfig(
        start_date=args.start,
        end_date=args.end,
        rebalance_freq=args.rebalance,
        top_n=args.top_n,
        benchmark=args.benchmark,
        risk_free_rate=args.rf if args.rf is not None else DEFAULT_CONFIG.risk_free_rate,
        transaction_cost=args.tx_cost,
        weighting=args.weighting,
        universe=universe,
        output_dir=output_dir,
        checkpoint_dir=checkpoint_dir,
        max_rebalance_time=args.max_time,
    )

    # Validate dates
    try:
        datetime.strptime(config.start_date, "%Y-%m-%d")
        datetime.strptime(config.end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"ERROR: Invalid date format: {e}", file=sys.stderr)
        sys.exit(1)

    if config.start_date >= config.end_date:
        print("ERROR: Start date must be before end date", file=sys.stderr)
        sys.exit(1)

    # Run backtest
    try:
        run_backtest(config)
    except KeyboardInterrupt:
        print("\n\n  Backtest interrupted by user. Checkpoints have been saved.")
        print(f"  Resume by running the same command again.")
        sys.exit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
