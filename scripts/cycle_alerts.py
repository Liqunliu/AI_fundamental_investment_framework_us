#!/usr/bin/env python3
"""Cycle Phase Change Detection & Commodity Price Monitoring.

Monitors cyclical portfolio holdings for:
  1. Phase changes (e.g., Phase 2 -> Phase 3 = reduce signal)
  2. Commodity price moves (sector indicator breaks)
  3. Price alerts (52-week lows, large daily moves)

Usage:
    python3 scripts/cycle_alerts.py
    python3 scripts/cycle_alerts.py --tickers PBR QCOM FRO
    python3 scripts/cycle_alerts.py --commodities-only
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore")

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from cycle_config import (  # noqa: E402
    CYCLE_CONFIG,
    CYCLE_PORTFOLIO_CONFIG,
    classify_phase,
    phase_label,
    phase_action,
)
from cycle_indicator_collector import (  # noqa: E402
    SECTOR_INDICATORS,
    MACRO_INDICATORS,
    fetch_indicator_history,
    compute_percentile,
    compute_trend,
)

try:
    import yfinance as yf
    import numpy as np
except ImportError:
    print("ERROR: yfinance, numpy required.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Alert definitions
# ---------------------------------------------------------------------------

@dataclass
class CycleAlert:
    """A single alert event."""
    ticker: str
    level: str  # CRITICAL, WARNING, INFO
    category: str  # phase_change, commodity, price, volume
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Portfolio reading
# ---------------------------------------------------------------------------

def _read_cycle_portfolio_tickers() -> List[str]:
    """Read tickers from CYCLE_PORTFOLIO.md."""
    portfolio_path = os.path.join(
        os.path.dirname(__file__), "..",
        CYCLE_PORTFOLIO_CONFIG.portfolio_file,
    )
    if not os.path.exists(portfolio_path):
        return []

    with open(portfolio_path, encoding="utf-8") as f:
        content = f.read()

    match = re.search(
        r"^## Holdings\s*\n(.+?)(?=\n## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    text = re.sub(r"[*_`]", "", match.group(1).strip())
    raw = re.split(r"[,\n\s]+", text)
    return [t.strip().upper() for t in raw if re.match(r"^[A-Z]{1,5}$", t.strip().upper())]


def _read_previous_phases() -> Dict[str, int]:
    """Read last known phases from cycle_score.md files."""
    cycle_dir = os.path.join(os.path.dirname(__file__), "..", "output", "cycle")
    phases = {}

    if not os.path.isdir(cycle_dir):
        return phases

    for name in os.listdir(cycle_dir):
        ticker_dir = os.path.join(cycle_dir, name)
        if not os.path.isdir(ticker_dir) or name == "screen":
            continue

        score_file = os.path.join(ticker_dir, "cycle_score.md")
        if not os.path.exists(score_file):
            continue

        with open(score_file, encoding="utf-8") as f:
            content = f.read()

        m = re.search(r"\*\*Phase\*\*:\s*\*?\*?(\d)", content)
        if m:
            phases[name] = int(m.group(1))

    return phases


# ---------------------------------------------------------------------------
# Phase change detection
# ---------------------------------------------------------------------------

def check_phase_changes(tickers: List[str]) -> List[CycleAlert]:
    """Detect phase changes by re-estimating current phase from price."""
    alerts = []
    previous_phases = _read_previous_phases()

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5y", interval="1wk")
            if hist is None or hist.empty:
                continue

            # Compute current phase from price percentile
            closes = hist["Close"].dropna()
            if len(closes) < 20:
                continue

            current = closes.iloc[-1]
            low = closes.min()
            high = closes.max()
            rng = high - low

            if rng <= 0:
                continue

            pct = (current - low) / rng
            score = 1.0 - pct
            current_phase = classify_phase(score)
            current_phase_name = phase_label(current_phase)

            prev_phase = previous_phases.get(ticker)

            if prev_phase is not None and current_phase != prev_phase:
                prev_name = phase_label(prev_phase)
                direction = "UPGRADE" if current_phase > prev_phase else "DOWNGRADE"

                if current_phase <= 2 and prev_phase >= 3:
                    level = "CRITICAL"
                    msg = (f"{ticker}: Phase {direction} {prev_phase}-{prev_name} -> "
                           f"{current_phase}-{current_phase_name}. "
                           f"BUY SIGNAL — entering trough phase!")
                elif current_phase >= 3 and prev_phase <= 2:
                    level = "WARNING"
                    msg = (f"{ticker}: Phase {direction} {prev_phase}-{prev_name} -> "
                           f"{current_phase}-{current_phase_name}. "
                           f"REDUCE — exiting trough phase.")
                elif current_phase == 5:
                    level = "WARNING"
                    msg = (f"{ticker}: Phase {direction} -> {current_phase}-PEAK. "
                           f"SELL SIGNAL — at cycle peak.")
                else:
                    level = "INFO"
                    msg = (f"{ticker}: Phase {prev_phase}-{prev_name} -> "
                           f"{current_phase}-{current_phase_name}")

                alerts.append(CycleAlert(
                    ticker=ticker,
                    level=level,
                    category="phase_change",
                    message=msg,
                    details={
                        "prev_phase": prev_phase,
                        "current_phase": current_phase,
                        "price_percentile": round(pct * 100, 1),
                        "current_price": round(current, 2),
                    },
                ))
            else:
                # No change, but report current status
                alerts.append(CycleAlert(
                    ticker=ticker,
                    level="INFO",
                    category="phase_status",
                    message=(f"{ticker}: Phase {current_phase}-{current_phase_name} "
                             f"(price at {pct * 100:.1f}% of 5yr range)"),
                    details={
                        "current_phase": current_phase,
                        "price_percentile": round(pct * 100, 1),
                        "action": phase_action(current_phase),
                    },
                ))

        except Exception as e:
            alerts.append(CycleAlert(
                ticker=ticker,
                level="WARNING",
                category="error",
                message=f"{ticker}: Failed to check phase: {e}",
            ))

    return alerts


# ---------------------------------------------------------------------------
# Commodity price monitoring
# ---------------------------------------------------------------------------

def check_commodity_alerts() -> List[CycleAlert]:
    """Monitor commodity prices for extreme moves."""
    alerts = []

    for key, ind in SECTOR_INDICATORS.items():
        try:
            hist = fetch_indicator_history(ind["symbol"], years=5)
            if hist is None:
                continue

            pct_data = compute_percentile(hist)
            trend_data = compute_trend(hist)

            percentile = pct_data.get("percentile", 50)
            current = pct_data.get("current", 0)
            change_3m = trend_data.get("change_3m", 0)

            # Alert on extreme percentiles
            if percentile <= 10:
                alerts.append(CycleAlert(
                    ticker=ind["symbol"],
                    level="CRITICAL",
                    category="commodity",
                    message=(f"{ind['name']}: At {percentile:.0f}% of 5yr range "
                             f"(${current:.2f}). DEEP TROUGH for {key} sector!"),
                    details={
                        "indicator": key,
                        "percentile": percentile,
                        "current": current,
                        "change_3m": change_3m,
                    },
                ))
            elif percentile <= 25:
                alerts.append(CycleAlert(
                    ticker=ind["symbol"],
                    level="WARNING",
                    category="commodity",
                    message=(f"{ind['name']}: At {percentile:.0f}% of 5yr range "
                             f"(${current:.2f}). Near trough for {key} sector."),
                    details={"indicator": key, "percentile": percentile},
                ))
            elif percentile >= 90:
                alerts.append(CycleAlert(
                    ticker=ind["symbol"],
                    level="WARNING",
                    category="commodity",
                    message=(f"{ind['name']}: At {percentile:.0f}% of 5yr range "
                             f"(${current:.2f}). Near PEAK for {key} sector — caution."),
                    details={"indicator": key, "percentile": percentile},
                ))

            # Alert on sharp 3M moves
            if abs(change_3m) >= 20:
                direction = "crash" if change_3m < 0 else "surge"
                alerts.append(CycleAlert(
                    ticker=ind["symbol"],
                    level="WARNING",
                    category="commodity_move",
                    message=(f"{ind['name']}: {change_3m:+.1f}% in 3 months "
                             f"({direction}). Monitor {key} sector stocks."),
                    details={"indicator": key, "change_3m": change_3m},
                ))

        except Exception as e:
            alerts.append(CycleAlert(
                ticker=ind["symbol"],
                level="INFO",
                category="error",
                message=f"{ind['name']}: Failed to check: {e}",
            ))

    return alerts


# ---------------------------------------------------------------------------
# Stock-level price alerts
# ---------------------------------------------------------------------------

def check_price_alerts(tickers: List[str]) -> List[CycleAlert]:
    """Check for large daily moves and 52-week extremes."""
    alerts = []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            prev_close = info.get("previousClose", 0)
            week52_low = info.get("fiftyTwoWeekLow", 0)
            week52_high = info.get("fiftyTwoWeekHigh", 0)
            volume = info.get("volume", 0)
            avg_volume = info.get("averageVolume", 1)

            if not price or not prev_close:
                continue

            change_pct = (price - prev_close) / prev_close * 100

            # Large daily move
            if abs(change_pct) >= 5:
                alerts.append(CycleAlert(
                    ticker=ticker,
                    level="WARNING",
                    category="price_move",
                    message=(f"{ticker}: {change_pct:+.1f}% daily move "
                             f"(${prev_close:.2f} -> ${price:.2f})"),
                    details={"change_pct": change_pct, "price": price},
                ))

            # 52-week low proximity
            if week52_low > 0:
                low_proximity = (price - week52_low) / week52_low * 100
                if low_proximity <= 5:
                    alerts.append(CycleAlert(
                        ticker=ticker,
                        level="CRITICAL" if low_proximity <= 2 else "WARNING",
                        category="52wk_low",
                        message=(f"{ticker}: Within {low_proximity:.1f}% of 52-week low "
                                 f"(${week52_low:.2f}). Potential trough entry!"),
                        details={"price": price, "week52_low": week52_low},
                    ))

            # Volume spike
            if avg_volume > 0 and volume > 0:
                vol_ratio = volume / avg_volume
                if vol_ratio >= 3:
                    alerts.append(CycleAlert(
                        ticker=ticker,
                        level="WARNING",
                        category="volume",
                        message=(f"{ticker}: Volume {vol_ratio:.1f}x average "
                                 f"({volume:,.0f} vs {avg_volume:,.0f})"),
                        details={"volume_ratio": vol_ratio},
                    ))

        except Exception as e:
            alerts.append(CycleAlert(
                ticker=ticker,
                level="INFO",
                category="error",
                message=f"{ticker}: Price check failed: {e}",
            ))

    return alerts


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def format_alert_report(alerts: List[CycleAlert]) -> str:
    """Generate markdown alert report."""
    L = []
    L.append("# Cyclical Trough Strategy — Alert Report")
    L.append("")
    L.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append("")

    # Summary counts
    critical = [a for a in alerts if a.level == "CRITICAL"]
    warning = [a for a in alerts if a.level == "WARNING"]
    info = [a for a in alerts if a.level == "INFO"]

    L.append(f"**CRITICAL**: {len(critical)} | **WARNING**: {len(warning)} | **INFO**: {len(info)}")
    L.append("")
    L.append("---")
    L.append("")

    # Group by category
    for level_name, level_alerts in [
        ("CRITICAL", critical),
        ("WARNING", warning),
        ("INFO", info),
    ]:
        if not level_alerts:
            continue

        L.append(f"## {level_name}")
        L.append("")
        for alert in level_alerts:
            prefix = {"CRITICAL": "!!!", "WARNING": "!", "INFO": "-"}.get(alert.level, "-")
            L.append(f"{prefix} **[{alert.category}]** {alert.message}")
        L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by Cyclical Trough Strategy — Alert Monitor*")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cycle Phase Change Detection & Commodity Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--tickers", nargs="*", help="Override tickers (default: from portfolio)")
    parser.add_argument("--commodities-only", action="store_true",
                        help="Only check commodity indicators")
    parser.add_argument("--output", help="Output file path")

    args = parser.parse_args()

    # Get tickers
    if args.tickers:
        tickers = [t.upper() for t in args.tickers]
    else:
        tickers = _read_cycle_portfolio_tickers()
        if not tickers:
            print("No tickers in cycle portfolio. Use --tickers or create portfolio first.")
            if not args.commodities_only:
                return

    all_alerts: List[CycleAlert] = []

    # Commodity alerts (always run)
    print("Checking commodity indicators...")
    commodity_alerts = check_commodity_alerts()
    all_alerts.extend(commodity_alerts)
    print(f"  {len(commodity_alerts)} commodity alerts")

    if not args.commodities_only and tickers:
        # Phase change detection
        print(f"Checking phase changes for {len(tickers)} tickers...")
        phase_alerts = check_phase_changes(tickers)
        all_alerts.extend(phase_alerts)
        print(f"  {len(phase_alerts)} phase alerts")

        # Price alerts
        print(f"Checking price alerts...")
        price_alerts = check_price_alerts(tickers)
        all_alerts.extend(price_alerts)
        print(f"  {len(price_alerts)} price alerts")

    # Sort by severity
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.level, 3))

    # Display
    print(f"\n{'=' * 70}")
    critical = sum(1 for a in all_alerts if a.level == "CRITICAL")
    warning = sum(1 for a in all_alerts if a.level == "WARNING")
    info = sum(1 for a in all_alerts if a.level == "INFO")
    print(f"  CRITICAL: {critical} | WARNING: {warning} | INFO: {info}")
    print(f"{'=' * 70}")

    for alert in all_alerts:
        prefix = {"CRITICAL": "!!!", "WARNING": " ! ", "INFO": "   "}.get(alert.level, "   ")
        print(f"  {prefix} [{alert.category}] {alert.message}")

    print()

    # Save report
    report = format_alert_report(all_alerts)
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "output", "cycle", "alerts")
        os.makedirs(output_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_path = os.path.join(output_dir, f"cycle_alerts_{date_str}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  Report saved to: {output_path}")


if __name__ == "__main__":
    main()
