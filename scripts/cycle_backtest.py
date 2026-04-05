#!/usr/bin/env python3
"""Historical Cycle Replay & Buy-at-Trough Simulation.

Backtests the cyclical trough strategy by replaying historical data:
  1. At each quarterly checkpoint, compute normalized GG and cycle phase
  2. Buy when Phase 1-2 and NormGG >= threshold
  3. Reduce when phase upgrades to 3+
  4. Sell when phase reaches 5

Usage:
    python3 scripts/cycle_backtest.py \\
        --tickers PBR QCOM FRO \\
        --start 2018-01-01 --end 2025-12-31 \\
        --source yfinance

    python3 scripts/cycle_backtest.py \\
        --tickers PBR --start 2020-01-01 --end 2025-12-31
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402
from cycle_config import CYCLE_CONFIG, classify_phase, phase_label  # noqa: E402

logger = logging.getLogger("cycle_backtest")

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: yfinance, pandas, numpy required.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    """Configuration for cycle backtest."""
    tickers: List[str] = field(default_factory=list)
    start_date: str = "2018-01-01"
    end_date: str = "2025-12-31"
    rebalance_freq: str = "quarterly"  # quarterly or semiannual
    initial_capital: float = 100_000.0
    benchmark: str = "SPY"
    output_dir: str = "output/cycle/backtest"
    threshold_pct: float = 7.30  # Normalized GG threshold


@dataclass
class PortfolioSnapshot:
    """Portfolio state at a point in time."""
    date: str
    nav: float
    cash: float
    positions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # positions = {ticker: {shares, cost_basis, current_price, value, phase, norm_gg}}
    actions: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Historical data helpers
# ---------------------------------------------------------------------------

def fetch_historical_prices(
    ticker: str,
    start: str,
    end: str,
) -> Optional[pd.DataFrame]:
    """Fetch daily price history."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end, interval="1d")
        if hist.empty:
            return None
        return hist
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", ticker, e)
        return None


def compute_historical_normalized_gg(
    ticker: str,
    as_of_date: str,
    lookback_years: int = 5,
) -> Optional[float]:
    """Estimate normalized GG at a historical point in time.

    Uses annual financial data available up to as_of_date.
    This is an approximation — actual historical financials may differ.
    """
    try:
        t = yf.Ticker(ticker)
        cf = t.cashflow
        info = t.info

        if cf is None or cf.empty:
            return None

        market_cap = info.get("marketCap", 0)
        if market_cap <= 0:
            return None

        # Get OCF and CapEx series
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

        if ocf_row is None or capex_row is None:
            return None

        ocf_vals = ocf_row.values.astype(float)
        capex_vals = np.abs(capex_row.values.astype(float))

        n = min(len(ocf_vals), len(capex_vals), lookback_years)
        if n < 2:
            return None

        med_ocf = np.median(ocf_vals[:n])
        med_capex = np.median(capex_vals[:n])
        norm_aa = med_ocf - med_capex

        return (norm_aa / market_cap) * 100

    except Exception:
        return None


def estimate_cycle_phase(
    ticker: str,
    price_history: pd.DataFrame,
    as_of_date: str,
) -> int:
    """Estimate cycle phase from price history percentile."""
    if price_history is None or price_history.empty:
        return 3  # default mid-cycle

    # Use 5-year lookback from as_of_date
    cutoff = pd.Timestamp(as_of_date)
    lookback = cutoff - pd.Timedelta(days=5 * 365)

    mask = (price_history.index >= lookback) & (price_history.index <= cutoff)
    window = price_history.loc[mask, "Close"]

    if len(window) < 50:
        return 3

    current = window.iloc[-1]
    low = window.min()
    high = window.max()
    rng = high - low

    if rng <= 0:
        return 3

    pct = (current - low) / rng

    # Invert to trough score and classify
    score = 1.0 - pct
    return classify_phase(score)


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(config: BacktestConfig) -> Dict[str, Any]:
    """Run historical cycle backtest."""
    print(f"\n{'=' * 70}")
    print("Cyclical Trough Backtest")
    print(f"{'=' * 70}")
    print(f"  Tickers: {', '.join(config.tickers)}")
    print(f"  Period: {config.start_date} to {config.end_date}")
    print(f"  Initial Capital: ${config.initial_capital:,.0f}")
    print(f"  Benchmark: {config.benchmark}")
    print()

    # Fetch all price histories
    all_prices: Dict[str, pd.DataFrame] = {}
    for ticker in config.tickers + [config.benchmark]:
        hist = fetch_historical_prices(ticker, config.start_date, config.end_date)
        if hist is not None:
            all_prices[ticker] = hist
            print(f"  {ticker}: {len(hist)} daily prices loaded")
        else:
            print(f"  {ticker}: FAILED to load")

    if not all_prices:
        print("ERROR: No price data loaded.")
        return {}

    # Generate rebalance dates (quarterly)
    start = pd.Timestamp(config.start_date)
    end = pd.Timestamp(config.end_date)
    rebalance_dates = pd.date_range(start, end, freq="QS").tolist()

    # Initialize portfolio
    cash = config.initial_capital
    positions: Dict[str, Dict[str, float]] = {}
    snapshots: List[PortfolioSnapshot] = []
    nav_series = []

    print(f"\n  {len(rebalance_dates)} rebalance points")
    print(f"  {'=' * 60}")

    for reb_date in rebalance_dates:
        date_str = reb_date.strftime("%Y-%m-%d")
        actions = []

        # Get current prices
        current_prices = {}
        for ticker in config.tickers:
            if ticker in all_prices:
                hist = all_prices[ticker]
                mask = hist.index <= reb_date
                if mask.any():
                    current_prices[ticker] = float(hist.loc[mask, "Close"].iloc[-1])

        # Compute NAV
        position_value = sum(
            pos.get("shares", 0) * current_prices.get(t, pos.get("current_price", 0))
            for t, pos in positions.items()
        )
        nav = cash + position_value

        # Evaluate each ticker
        for ticker in config.tickers:
            if ticker not in current_prices:
                continue

            price = current_prices[ticker]
            phase = estimate_cycle_phase(
                ticker, all_prices.get(ticker), date_str,
            )
            norm_gg = compute_historical_normalized_gg(ticker, date_str)

            phase_name = phase_label(phase)

            # Decision logic
            if ticker in positions:
                # Already holding — check for reduce/sell
                if phase >= 4:
                    # Late cycle / Peak — sell
                    shares = positions[ticker]["shares"]
                    proceeds = shares * price
                    cash += proceeds
                    cost = positions[ticker]["cost_basis"]
                    pnl = proceeds - cost
                    actions.append(
                        f"SELL {ticker}: {shares:.0f} shares @ ${price:.2f} "
                        f"(P&L: ${pnl:+,.0f}, Phase {phase}-{phase_name})"
                    )
                    del positions[ticker]

                elif phase == 3:
                    # Mid-cycle — reduce to 50%
                    shares = positions[ticker]["shares"]
                    sell_shares = shares * 0.5
                    if sell_shares >= 1:
                        proceeds = sell_shares * price
                        cash += proceeds
                        positions[ticker]["shares"] -= sell_shares
                        positions[ticker]["cost_basis"] *= 0.5
                        actions.append(
                            f"REDUCE {ticker}: sold {sell_shares:.0f} shares "
                            f"(Phase {phase}-{phase_name})"
                        )
                else:
                    # Update position tracking
                    positions[ticker]["current_price"] = price
                    positions[ticker]["phase"] = phase

            else:
                # Not holding — check for buy
                if phase <= 2 and norm_gg is not None and norm_gg >= config.threshold_pct:
                    # Buy signal
                    max_pos = CYCLE_CONFIG.max_single_position
                    target_value = nav * max_pos * (0.8 if phase == 1 else 0.5)
                    invest = min(target_value, cash * 0.9)  # keep some cash

                    if invest > 0 and price > 0:
                        shares = int(invest / price)
                        if shares > 0:
                            cost = shares * price
                            cash -= cost
                            positions[ticker] = {
                                "shares": float(shares),
                                "cost_basis": cost,
                                "current_price": price,
                                "phase": phase,
                                "norm_gg": norm_gg,
                            }
                            actions.append(
                                f"BUY {ticker}: {shares} shares @ ${price:.2f} "
                                f"(NormGG={norm_gg:.1f}%, Phase {phase}-{phase_name})"
                            )

        # Record snapshot
        position_value = sum(
            pos["shares"] * current_prices.get(t, pos["current_price"])
            for t, pos in positions.items()
        )
        nav = cash + position_value

        snapshot = PortfolioSnapshot(
            date=date_str,
            nav=nav,
            cash=cash,
            positions={t: dict(p) for t, p in positions.items()},
            actions=actions,
        )
        snapshots.append(snapshot)
        nav_series.append({"date": date_str, "nav": nav})

        # Print summary
        n_pos = len(positions)
        print(f"  {date_str}  NAV=${nav:>12,.0f}  Cash=${cash:>10,.0f}  "
              f"Positions={n_pos}  Actions={len(actions)}")
        for act in actions:
            print(f"    -> {act}")

    # Benchmark performance
    bench_return = 0.0
    if config.benchmark in all_prices:
        bench = all_prices[config.benchmark]
        start_price = bench["Close"].iloc[0]
        end_price = bench["Close"].iloc[-1]
        bench_return = (end_price - start_price) / start_price * 100

    # Final metrics
    final_nav = snapshots[-1].nav if snapshots else config.initial_capital
    total_return = (final_nav - config.initial_capital) / config.initial_capital * 100

    # Max drawdown
    navs = [s.nav for s in snapshots]
    peak = navs[0]
    max_dd = 0.0
    for n in navs:
        peak = max(peak, n)
        dd = (n - peak) / peak
        max_dd = min(max_dd, dd)

    results = {
        "initial_capital": config.initial_capital,
        "final_nav": final_nav,
        "total_return_pct": round(total_return, 2),
        "benchmark_return_pct": round(bench_return, 2),
        "excess_return_pct": round(total_return - bench_return, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "num_rebalances": len(snapshots),
        "snapshots": nav_series,
    }

    # Print summary
    print(f"\n{'=' * 70}")
    print("  BACKTEST RESULTS")
    print(f"{'=' * 70}")
    print(f"  Total Return:     {total_return:>+8.2f}%")
    print(f"  Benchmark ({config.benchmark}): {bench_return:>+8.2f}%")
    print(f"  Excess Return:    {total_return - bench_return:>+8.2f}%")
    print(f"  Max Drawdown:     {max_dd * 100:>8.2f}%")
    print(f"  Final NAV:        ${final_nav:>12,.0f}")
    print()

    # Save results
    out_dir = Path(_SCRIPTS_DIR).parent / config.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save checkpoints
    cp_dir = out_dir / "checkpoints"
    cp_dir.mkdir(exist_ok=True)
    for snap in snapshots:
        cp_file = cp_dir / f"rebalance_{snap.date}.json"
        cp_file.write_text(
            json.dumps(asdict(snap), indent=2, default=str),
            encoding="utf-8",
        )

    # Save report
    report = _format_backtest_report(config, results, snapshots)
    report_path = out_dir / "cycle_backtest_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved to: {report_path}")

    return results


def _format_backtest_report(
    config: BacktestConfig,
    results: Dict[str, Any],
    snapshots: List[PortfolioSnapshot],
) -> str:
    """Generate markdown backtest report."""
    L = []
    L.append("# Cyclical Trough Strategy — Backtest Report")
    L.append("")
    L.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"**Period**: {config.start_date} to {config.end_date}")
    L.append(f"**Tickers**: {', '.join(config.tickers)}")
    L.append(f"**Benchmark**: {config.benchmark}")
    L.append("")
    L.append("---")
    L.append("")

    L.append("## Performance Summary")
    L.append("")
    L.append("| Metric | Value |")
    L.append("|--------|------:|")
    L.append(f"| Initial Capital | ${config.initial_capital:,.0f} |")
    L.append(f"| Final NAV | ${results['final_nav']:,.0f} |")
    L.append(f"| Total Return | {results['total_return_pct']:+.2f}% |")
    L.append(f"| Benchmark Return | {results['benchmark_return_pct']:+.2f}% |")
    L.append(f"| Excess Return | {results['excess_return_pct']:+.2f}% |")
    L.append(f"| Max Drawdown | {results['max_drawdown_pct']:.2f}% |")
    L.append(f"| Rebalance Points | {results['num_rebalances']} |")
    L.append("")

    L.append("## NAV History")
    L.append("")
    L.append("| Date | NAV | Change |")
    L.append("|------|----:|-------:|")
    prev_nav = config.initial_capital
    for snap in snapshots:
        change = (snap.nav - prev_nav) / prev_nav * 100
        L.append(f"| {snap.date} | ${snap.nav:,.0f} | {change:+.1f}% |")
        prev_nav = snap.nav
    L.append("")

    L.append("## Trade Log")
    L.append("")
    for snap in snapshots:
        if snap.actions:
            L.append(f"### {snap.date}")
            for act in snap.actions:
                L.append(f"- {act}")
            L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by Cyclical Trough Strategy — Backtest Engine*")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cyclical Trough Strategy Backtester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--capital", type=float, default=100_000)
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--output", default="output/cycle/backtest")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    config = BacktestConfig(
        tickers=[t.upper() for t in args.tickers],
        start_date=args.start,
        end_date=args.end,
        initial_capital=args.capital,
        benchmark=args.benchmark,
        output_dir=args.output,
    )

    run_backtest(config)


if __name__ == "__main__":
    main()
