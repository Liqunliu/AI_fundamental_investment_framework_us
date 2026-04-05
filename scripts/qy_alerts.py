#!/usr/bin/env python3
"""Daily Alert Monitor for US Equity Quality Yield Strategy.

Checks portfolio holdings for important price and volume changes:
  1. Price change > 5% in one day     -> Flag for review
  2. 52-week low breached             -> Potential buying opportunity
  3. 52-week high reached             -> Potential trimming opportunity
  4. Volume spike > 3x average        -> Unusual activity

Budget: Complete in < 30 seconds for a typical portfolio (5-15 holdings).

Usage:
    python3 scripts/qy_alerts.py                        # Check all holdings
    python3 scripts/qy_alerts.py --tickers AAPL MSFT    # Check specific tickers
"""

from __future__ import annotations

import argparse
import os
import ssl
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# SSL workaround (same as yfinance_collector.py)
# ---------------------------------------------------------------------------
os.environ.setdefault("CURL_CA_BUNDLE", "")
os.environ.setdefault("PYTHONHTTPSVERIFY", "0")

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
# Local imports
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402
from portfolio_manager import read_tickers  # noqa: E402

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
try:
    import yfinance as yf
except ImportError:
    print(
        "ERROR: yfinance is required.  Run:  pip install yfinance",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = _SCRIPTS_DIR.parent
_ALERTS_DIR = _PROJECT_ROOT / "output" / "alerts"

# ---------------------------------------------------------------------------
# Alert thresholds (from config, with local defaults as fallback)
# ---------------------------------------------------------------------------
PRICE_CHANGE_THRESHOLD = getattr(DEFAULT_CONFIG, "alert_price_change_pct", 5.0)
VOLUME_SPIKE_MULTIPLIER = 3.0
WEEK52_LOW_PROXIMITY_PCT = 2.0   # within 2% of 52-week low
WEEK52_HIGH_PROXIMITY_PCT = 2.0  # within 2% of 52-week high


# ============================================================================
#  Alert data structures
# ============================================================================

class Alert:
    """Single alert for one ticker."""

    LEVELS = ("INFO", "WARNING", "CRITICAL")

    def __init__(
        self,
        ticker: str,
        level: str,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.ticker = ticker
        self.level = level if level in self.LEVELS else "INFO"
        self.category = category
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def __repr__(self) -> str:
        return f"[{self.level}] {self.ticker}: {self.message}"

    @property
    def emoji(self) -> str:
        return {
            "CRITICAL": "!!",
            "WARNING": "!",
            "INFO": "-",
        }.get(self.level, "-")


# ============================================================================
#  Data fetching
# ============================================================================

def fetch_ticker_data(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch current price data and metadata for a single ticker via yfinance.

    Returns:
        Dict with keys: ticker, price, prev_close, change_pct, volume,
        avg_volume, week52_high, week52_low, name.
        None if the fetch fails.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        volume = info.get("volume") or info.get("regularMarketVolume")
        avg_volume = info.get("averageVolume") or info.get("averageDailyVolume10Day")
        week52_high = info.get("fiftyTwoWeekHigh")
        week52_low = info.get("fiftyTwoWeekLow")
        name = info.get("shortName") or info.get("longName") or ticker

        if price is None or prev_close is None:
            return None

        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

        return {
            "ticker": ticker,
            "price": float(price),
            "prev_close": float(prev_close),
            "change_pct": round(change_pct, 2),
            "volume": int(volume) if volume else 0,
            "avg_volume": int(avg_volume) if avg_volume else 0,
            "week52_high": float(week52_high) if week52_high else None,
            "week52_low": float(week52_low) if week52_low else None,
            "name": str(name),
        }

    except Exception as exc:
        print(f"  [ERR] Failed to fetch {ticker}: {exc}", file=sys.stderr)
        return None


# ============================================================================
#  Alert checks
# ============================================================================

def check_price_change(data: Dict[str, Any]) -> List[Alert]:
    """Check 1: Daily price change exceeds threshold."""
    alerts = []
    change = abs(data["change_pct"])

    if change >= PRICE_CHANGE_THRESHOLD:
        direction = "UP" if data["change_pct"] > 0 else "DOWN"
        level = "CRITICAL" if change >= PRICE_CHANGE_THRESHOLD * 2 else "WARNING"
        alerts.append(Alert(
            ticker=data["ticker"],
            level=level,
            category="PRICE_CHANGE",
            message=(
                f"Price {direction} {data['change_pct']:+.2f}% today "
                f"(${data['prev_close']:.2f} -> ${data['price']:.2f})"
            ),
            details={
                "change_pct": data["change_pct"],
                "price": data["price"],
                "prev_close": data["prev_close"],
                "threshold": PRICE_CHANGE_THRESHOLD,
            },
        ))

    return alerts


def check_52week_low(data: Dict[str, Any]) -> List[Alert]:
    """Check 2: Price near or below 52-week low -- potential buying opportunity."""
    alerts = []
    week52_low = data.get("week52_low")
    if week52_low is None or week52_low <= 0:
        return alerts

    price = data["price"]
    proximity_pct = ((price - week52_low) / week52_low) * 100

    if price <= week52_low:
        alerts.append(Alert(
            ticker=data["ticker"],
            level="CRITICAL",
            category="52W_LOW_BREACH",
            message=(
                f"NEW 52-week low: ${price:.2f} "
                f"(previous low: ${week52_low:.2f}). "
                f"Potential buying opportunity per Quality Yield Strategy."
            ),
            details={
                "price": price,
                "week52_low": week52_low,
                "proximity_pct": round(proximity_pct, 2),
            },
        ))
    elif proximity_pct <= WEEK52_LOW_PROXIMITY_PCT:
        alerts.append(Alert(
            ticker=data["ticker"],
            level="WARNING",
            category="52W_LOW_NEAR",
            message=(
                f"Price ${price:.2f} is {proximity_pct:.1f}% above "
                f"52-week low (${week52_low:.2f}). Watch for buying opportunity."
            ),
            details={
                "price": price,
                "week52_low": week52_low,
                "proximity_pct": round(proximity_pct, 2),
            },
        ))

    return alerts


def check_52week_high(data: Dict[str, Any]) -> List[Alert]:
    """Check 3: Price near or above 52-week high -- potential trimming opportunity."""
    alerts = []
    week52_high = data.get("week52_high")
    if week52_high is None or week52_high <= 0:
        return alerts

    price = data["price"]
    proximity_pct = ((week52_high - price) / week52_high) * 100

    if price >= week52_high:
        alerts.append(Alert(
            ticker=data["ticker"],
            level="WARNING",
            category="52W_HIGH_BREACH",
            message=(
                f"NEW 52-week high: ${price:.2f} "
                f"(previous high: ${week52_high:.2f}). "
                f"Consider trimming per Quality Yield Strategy."
            ),
            details={
                "price": price,
                "week52_high": week52_high,
                "proximity_pct": round(proximity_pct, 2),
            },
        ))
    elif proximity_pct <= WEEK52_HIGH_PROXIMITY_PCT:
        alerts.append(Alert(
            ticker=data["ticker"],
            level="INFO",
            category="52W_HIGH_NEAR",
            message=(
                f"Price ${price:.2f} is {proximity_pct:.1f}% below "
                f"52-week high (${week52_high:.2f}). Watch for trimming opportunity."
            ),
            details={
                "price": price,
                "week52_high": week52_high,
                "proximity_pct": round(proximity_pct, 2),
            },
        ))

    return alerts


def check_volume_spike(data: Dict[str, Any]) -> List[Alert]:
    """Check 4: Volume spike > 3x average -- unusual activity."""
    alerts = []
    volume = data.get("volume", 0)
    avg_volume = data.get("avg_volume", 0)

    if avg_volume <= 0 or volume <= 0:
        return alerts

    volume_ratio = volume / avg_volume

    if volume_ratio >= VOLUME_SPIKE_MULTIPLIER:
        level = "CRITICAL" if volume_ratio >= VOLUME_SPIKE_MULTIPLIER * 2 else "WARNING"
        alerts.append(Alert(
            ticker=data["ticker"],
            level=level,
            category="VOLUME_SPIKE",
            message=(
                f"Volume spike: {volume:,.0f} ({volume_ratio:.1f}x average of "
                f"{avg_volume:,.0f}). Unusual activity detected."
            ),
            details={
                "volume": volume,
                "avg_volume": avg_volume,
                "volume_ratio": round(volume_ratio, 2),
                "threshold_multiplier": VOLUME_SPIKE_MULTIPLIER,
            },
        ))

    return alerts


def run_all_checks(data: Dict[str, Any]) -> List[Alert]:
    """Run all alert checks on a single ticker's data."""
    alerts = []
    alerts.extend(check_price_change(data))
    alerts.extend(check_52week_low(data))
    alerts.extend(check_52week_high(data))
    alerts.extend(check_volume_spike(data))
    return alerts


# ============================================================================
#  Report generation
# ============================================================================

def format_alert_report(
    all_alerts: Dict[str, List[Alert]],
    all_data: Dict[str, Dict[str, Any]],
    elapsed: float,
) -> str:
    """Generate a markdown alert report.

    Args:
        all_alerts: Dict mapping ticker -> list of Alert objects.
        all_data: Dict mapping ticker -> raw data dict.
        elapsed: Total processing time in seconds.

    Returns:
        Markdown report string.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Flatten and count
    flat_alerts = [a for alerts in all_alerts.values() for a in alerts]
    critical = sum(1 for a in flat_alerts if a.level == "CRITICAL")
    warnings_count = sum(1 for a in flat_alerts if a.level == "WARNING")
    info_count = sum(1 for a in flat_alerts if a.level == "INFO")
    tickers_with_alerts = [t for t, alerts in all_alerts.items() if alerts]

    lines = []
    lines.append(f"# Quality Yield Strategy Daily Alerts -- {today}")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Tickers Checked**: {len(all_data)}")
    lines.append(f"**Total Alerts**: {len(flat_alerts)} "
                 f"(CRITICAL: {critical}, WARNING: {warnings_count}, INFO: {info_count})")
    lines.append(f"**Processing Time**: {elapsed:.1f}s")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not flat_alerts:
        lines.append("## No Alerts Triggered")
        lines.append("")
        lines.append("All portfolio holdings are within normal parameters.")
        lines.append("")
    else:
        # Summary table
        lines.append("## Alert Summary")
        lines.append("")
        lines.append("| Ticker | Level | Category | Message |")
        lines.append("|--------|-------|----------|---------|")
        for alert in sorted(flat_alerts, key=lambda a: (
            {"CRITICAL": 0, "WARNING": 1, "INFO": 2}.get(a.level, 3),
            a.ticker,
        )):
            lines.append(
                f"| **{alert.ticker}** | {alert.level} | "
                f"{alert.category} | {alert.message} |"
            )
        lines.append("")

        # Detailed section per ticker with alerts
        lines.append("## Detailed Alerts")
        lines.append("")
        for ticker in tickers_with_alerts:
            ticker_alerts = all_alerts[ticker]
            data = all_data.get(ticker, {})
            lines.append(f"### {ticker} -- {data.get('name', ticker)}")
            lines.append("")
            lines.append(
                f"- **Price**: ${data.get('price', 0):.2f}  "
                f"(prev close: ${data.get('prev_close', 0):.2f}, "
                f"change: {data.get('change_pct', 0):+.2f}%)"
            )
            if data.get("week52_high"):
                lines.append(
                    f"- **52-Week Range**: "
                    f"${data.get('week52_low', 0):.2f} -- "
                    f"${data.get('week52_high', 0):.2f}"
                )
            if data.get("avg_volume"):
                vol_ratio = (
                    data["volume"] / data["avg_volume"]
                    if data["avg_volume"] > 0 else 0
                )
                lines.append(
                    f"- **Volume**: {data.get('volume', 0):,.0f}  "
                    f"(avg: {data.get('avg_volume', 0):,.0f}, "
                    f"ratio: {vol_ratio:.1f}x)"
                )
            lines.append("")
            for alert in ticker_alerts:
                lines.append(f"**[{alert.level}] {alert.category}**")
                lines.append(f"> {alert.message}")
                lines.append("")
            lines.append("---")
            lines.append("")

    # Portfolio snapshot table
    lines.append("## Portfolio Snapshot")
    lines.append("")
    lines.append("| Ticker | Price | Change | Volume | Vol Ratio | 52W Low | 52W High | Alerts |")
    lines.append("|--------|------:|-------:|-------:|----------:|--------:|---------:|:------:|")
    for ticker, data in sorted(all_data.items()):
        alert_count = len(all_alerts.get(ticker, []))
        vol_ratio = (
            f"{data['volume'] / data['avg_volume']:.1f}x"
            if data.get("avg_volume") and data["avg_volume"] > 0
            else "--"
        )
        w52_low = f"${data['week52_low']:.2f}" if data.get("week52_low") else "--"
        w52_high = f"${data['week52_high']:.2f}" if data.get("week52_high") else "--"
        flag = f"**{alert_count}**" if alert_count > 0 else "0"
        lines.append(
            f"| {ticker} | ${data['price']:.2f} | {data['change_pct']:+.2f}% | "
            f"{data.get('volume', 0):,.0f} | {vol_ratio} | {w52_low} | {w52_high} | {flag} |"
        )
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by Quality Yield Strategy Daily Alert Monitor*")

    return "\n".join(lines)


def write_alert_file(content: str, force: bool = False) -> Optional[str]:
    """Write the alert report to output/alerts/YYYY-MM-DD.md.

    Returns:
        Path string if written, None if skipped.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    _ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _ALERTS_DIR / f"{today}.md"

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


# ============================================================================
#  Main pipeline
# ============================================================================

def run_alerts(tickers: List[str]) -> Dict[str, Any]:
    """Run the full alert pipeline for the given tickers.

    Returns:
        Dict with keys: alerts, data, report_path, elapsed, summary.
    """
    t0 = time.time()
    budget = getattr(DEFAULT_CONFIG, "daily_alert_budget", 30)

    print(f"\n{'='*70}")
    print("QUALITY YIELD STRATEGY -- Daily Alert Monitor")
    print(f"{'='*70}")
    print(f"  Tickers: {', '.join(tickers)}")
    print(f"  Budget: {budget}s")
    print(f"  Thresholds:")
    print(f"    Price change:  {PRICE_CHANGE_THRESHOLD}%")
    print(f"    Volume spike:  {VOLUME_SPIKE_MULTIPLIER}x avg")
    print(f"    52W proximity: {WEEK52_LOW_PROXIMITY_PCT}%")
    print()

    all_alerts: Dict[str, List[Alert]] = {}
    all_data: Dict[str, Dict[str, Any]] = {}
    fetch_errors: List[str] = []

    for i, ticker in enumerate(tickers, start=1):
        elapsed = time.time() - t0
        if elapsed > budget:
            remaining = tickers[i - 1:]
            print(f"\n  Budget exceeded ({elapsed:.1f}s > {budget}s). "
                  f"Skipping {len(remaining)} tickers: {', '.join(remaining)}")
            break

        print(f"  [{i:2d}/{len(tickers)}] {ticker:<6s} ... ", end="", flush=True)

        data = fetch_ticker_data(ticker)
        if data is None:
            print("SKIP (fetch failed)")
            fetch_errors.append(ticker)
            continue

        alerts = run_all_checks(data)
        all_alerts[ticker] = alerts
        all_data[ticker] = data

        if alerts:
            levels = [a.level for a in alerts]
            print(f"${data['price']:.2f} ({data['change_pct']:+.2f}%)  "
                  f"-> {len(alerts)} alert(s) [{', '.join(levels)}]")
        else:
            print(f"${data['price']:.2f} ({data['change_pct']:+.2f}%)  OK")

    elapsed = time.time() - t0

    # Count totals
    total_alerts = sum(len(a) for a in all_alerts.values())
    critical = sum(1 for a in all_alerts.values() for x in a if x.level == "CRITICAL")
    warnings_count = sum(1 for a in all_alerts.values() for x in a if x.level == "WARNING")

    # Generate and write report (only if alerts triggered)
    report_path = None
    if total_alerts > 0:
        report = format_alert_report(all_alerts, all_data, elapsed)
        report_path = write_alert_file(report)

    # Console summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}")
    print(f"  Tickers checked : {len(all_data)}")
    if fetch_errors:
        print(f"  Fetch errors    : {len(fetch_errors)} ({', '.join(fetch_errors)})")
    print(f"  Total alerts    : {total_alerts}")
    if total_alerts > 0:
        print(f"    CRITICAL      : {critical}")
        print(f"    WARNING       : {warnings_count}")
        print(f"    INFO          : {total_alerts - critical - warnings_count}")
    print(f"  Processing time : {elapsed:.1f}s (budget: {budget}s)")
    if report_path:
        print(f"  Report written  : {report_path}")
    else:
        print(f"  Report          : (no alerts triggered, no file written)")
    print()

    return {
        "alerts": all_alerts,
        "data": all_data,
        "report_path": report_path,
        "elapsed": elapsed,
        "summary": {
            "total": total_alerts,
            "critical": critical,
            "warnings": warnings_count,
            "tickers_checked": len(all_data),
            "fetch_errors": fetch_errors,
        },
    }


# ============================================================================
#  CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quality Yield Strategy Daily Alert Monitor -- US Equity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s                          # Check all portfolio holdings
  %(prog)s --tickers AAPL MSFT      # Check specific tickers
  %(prog)s --tickers AAPL --verbose  # Verbose output
""",
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Specific tickers to check (default: read from US_PORTFOLIO.md)",
    )
    parser.add_argument(
        "--portfolio",
        default=None,
        help="Path to portfolio file (default: output/US_PORTFOLIO.md)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Determine tickers
    if args.tickers:
        tickers = [t.upper().strip() for t in args.tickers]
    else:
        tickers = read_tickers(args.portfolio)
        if not tickers:
            print(
                "No tickers found in portfolio. Either:\n"
                "  1. Initialize the portfolio: python3 scripts/portfolio_manager.py init --tickers AAPL MSFT\n"
                "  2. Specify tickers directly: python3 scripts/qy_alerts.py --tickers AAPL MSFT",
                file=sys.stderr,
            )
            sys.exit(1)

    result = run_alerts(tickers)

    # Exit code: 2 for critical, 1 for warnings, 0 for clean
    if result["summary"]["critical"] > 0:
        sys.exit(2)
    elif result["summary"]["warnings"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
