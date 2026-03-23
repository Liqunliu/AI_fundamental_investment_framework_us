#!/usr/bin/env python3
"""Scheduler for US Equity Turtle Strategy.

Coordinates daily, weekly, and monthly tasks:

  Daily   : Run turtle_alerts.py for portfolio holdings         (< 30 sec)
  Weekly  : Re-run GG calculation for all holdings              (< 5 min)
            - Collect fresh data via yfinance_collector.py
            - Recalculate GG via calculate_turtle_gg.py
            - Compare new vs old GG values
  Monthly : Run full Finviz screen with GG scoring              (< 30 min)
            - finviz_screener.py --with-gg --top-n 10
            - Compare new candidates vs current holdings

Usage:
    # Run as daemon (continuous scheduler)
    python3 scripts/turtle_scheduler.py start

    # Run a single scheduled task
    python3 scripts/turtle_scheduler.py run-daily
    python3 scripts/turtle_scheduler.py run-weekly
    python3 scripts/turtle_scheduler.py run-monthly

    # Show schedule status
    python3 scripts/turtle_scheduler.py status
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402
from portfolio_manager import read_tickers  # noqa: E402

# ---------------------------------------------------------------------------
# Third-party: schedule library
# ---------------------------------------------------------------------------
try:
    import schedule
except ImportError:
    # schedule is only required for daemon mode; allow import for single-run
    schedule = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = _SCRIPTS_DIR.parent
_CONFIG_FILE = _SCRIPTS_DIR / "schedule_config.json"
_OUTPUT_DIR = _PROJECT_ROOT / "output"
_WEEKLY_DIR = _OUTPUT_DIR / "weekly"
_MONTHLY_DIR = _OUTPUT_DIR / "monthly_screen"

# Python interpreter
_PYTHON = sys.executable


# ============================================================================
#  Configuration
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load schedule configuration from schedule_config.json.

    Returns:
        Config dict with daily/weekly/monthly settings.
    """
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)

    # Defaults
    return {
        "daily": {"time": "09:00", "enabled": True},
        "weekly": {"day": "monday", "time": "09:30", "enabled": True},
        "monthly": {"day": 1, "time": "10:00", "enabled": True},
    }


# ============================================================================
#  Task: Daily Alerts
# ============================================================================

def run_daily() -> Dict[str, Any]:
    """Run the daily alert check for all portfolio holdings.

    Budget: < 30 seconds.

    Returns:
        Result dict with status, elapsed, and details.
    """
    t0 = time.time()
    budget = getattr(DEFAULT_CONFIG, "daily_alert_budget", 30)

    print(f"\n{'='*70}")
    print(f"DAILY TASK -- Alert Check")
    print(f"{'='*70}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Budget:  {budget}s")

    # Invoke turtle_alerts.py as a subprocess
    alerts_script = _SCRIPTS_DIR / "turtle_alerts.py"
    if not alerts_script.exists():
        print(f"  ERROR: {alerts_script} not found", file=sys.stderr)
        return {"status": "error", "reason": "script not found", "elapsed": 0}

    try:
        result = subprocess.run(
            [_PYTHON, str(alerts_script)],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=budget + 10,  # small grace period
        )

        elapsed = time.time() - t0

        # Print stdout from the alerts script
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        status = "ok" if result.returncode == 0 else (
            "warnings" if result.returncode == 1 else "critical"
        )

        print(f"\n  Daily task completed in {elapsed:.1f}s (status: {status})")
        return {
            "status": status,
            "returncode": result.returncode,
            "elapsed": elapsed,
        }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        print(f"\n  Daily task TIMED OUT after {elapsed:.1f}s", file=sys.stderr)
        return {"status": "timeout", "elapsed": elapsed}

    except Exception as exc:
        elapsed = time.time() - t0
        print(f"\n  Daily task FAILED: {exc}", file=sys.stderr)
        return {"status": "error", "reason": str(exc), "elapsed": elapsed}


# ============================================================================
#  Task: Weekly GG Refresh
# ============================================================================

def _read_existing_gg(ticker: str) -> Optional[float]:
    """Read the existing GG value from a ticker's GG report file.

    Returns:
        GG percentage as float, or None if not found.
    """
    gg_file = _OUTPUT_DIR / ticker / f"{ticker}_GG.md"
    if not gg_file.exists():
        # Try alternate name
        gg_file = _OUTPUT_DIR / ticker / "gg_result.md"
    if not gg_file.exists():
        return None

    content = gg_file.read_text(encoding="utf-8")
    match = re.search(r"GG\s*\(Standard\).*?:\s*\*?\*?([\d.]+)%", content)
    if match:
        return float(match.group(1))

    match = re.search(r"GG.*?:\s*\*?\*?([\d.]+)%", content)
    if match:
        return float(match.group(1))

    return None


def _run_subprocess(args: List[str], label: str, timeout: int) -> Tuple[bool, str]:
    """Run a subprocess with timeout and return (success, output)."""
    try:
        result = subprocess.run(
            args,
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        if not success:
            print(f"    [{label}] exited with code {result.returncode}")
        return success, output

    except subprocess.TimeoutExpired:
        print(f"    [{label}] TIMEOUT after {timeout}s")
        return False, f"Timeout after {timeout}s"

    except Exception as exc:
        print(f"    [{label}] ERROR: {exc}")
        return False, str(exc)


def run_weekly() -> Dict[str, Any]:
    """Run the weekly GG refresh for all portfolio holdings.

    For each ticker:
      1. Collect fresh data via yfinance_collector.py
      2. Recalculate GG via calculate_turtle_gg.py
      3. Compare new vs old GG values

    Budget: < 5 minutes.

    Returns:
        Result dict with status, comparisons, and report path.
    """
    t0 = time.time()
    budget = getattr(DEFAULT_CONFIG, "weekly_refresh_budget", 300)

    print(f"\n{'='*70}")
    print(f"WEEKLY TASK -- GG Refresh")
    print(f"{'='*70}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Budget:  {budget}s")

    # Read tickers
    tickers = read_tickers()
    if not tickers:
        print("  No tickers in portfolio. Skipping weekly refresh.")
        return {"status": "skipped", "reason": "empty portfolio", "elapsed": 0}

    print(f"  Tickers: {', '.join(tickers)}")
    print()

    collector_script = _SCRIPTS_DIR / "yfinance_collector.py"
    gg_script = _SCRIPTS_DIR / "calculate_turtle_gg.py"

    comparisons: List[Dict[str, Any]] = []
    successes = 0
    failures = 0
    per_ticker_budget = max(30, (budget - 30) // len(tickers))

    for i, ticker in enumerate(tickers, start=1):
        elapsed = time.time() - t0
        if elapsed > budget:
            print(f"\n  Budget exceeded ({elapsed:.1f}s). Stopping.")
            break

        print(f"  [{i}/{len(tickers)}] {ticker}")

        # Step 1: Read old GG value
        old_gg = _read_existing_gg(ticker)
        old_label = f"{old_gg:.2f}%" if old_gg is not None else "N/A"
        print(f"    Old GG: {old_label}")

        # Step 2: Collect fresh data
        print(f"    Collecting data via yfinance ...", end=" ", flush=True)
        ok, output = _run_subprocess(
            [_PYTHON, str(collector_script), "--ticker", ticker],
            label=f"{ticker} collect",
            timeout=per_ticker_budget,
        )
        if not ok:
            print("FAILED")
            failures += 1
            comparisons.append({
                "ticker": ticker,
                "old_gg": old_gg,
                "new_gg": None,
                "status": "collect_failed",
            })
            continue
        print("OK")

        # Step 3: Calculate GG
        data_pack = _OUTPUT_DIR / ticker / "data_pack.md"
        if not data_pack.exists():
            print(f"    Data pack not found at {data_pack}")
            failures += 1
            comparisons.append({
                "ticker": ticker,
                "old_gg": old_gg,
                "new_gg": None,
                "status": "no_data_pack",
            })
            continue

        print(f"    Calculating GG ...", end=" ", flush=True)
        ok, output = _run_subprocess(
            [
                _PYTHON, str(gg_script),
                "--input", str(data_pack),
                "--code", ticker,
            ],
            label=f"{ticker} GG",
            timeout=per_ticker_budget,
        )
        if not ok:
            print("FAILED")
            failures += 1
            comparisons.append({
                "ticker": ticker,
                "old_gg": old_gg,
                "new_gg": None,
                "status": "gg_failed",
            })
            continue
        print("OK")

        # Step 4: Read new GG value
        new_gg = _read_existing_gg(ticker)
        new_label = f"{new_gg:.2f}%" if new_gg is not None else "N/A"

        # Compare
        if old_gg is not None and new_gg is not None:
            delta = new_gg - old_gg
            direction = "UP" if delta > 0 else "DOWN" if delta < 0 else "FLAT"
            print(f"    New GG: {new_label}  ({direction} {abs(delta):+.2f} pct pts)")
        else:
            delta = None
            direction = "NEW"
            print(f"    New GG: {new_label}  (first calculation)")

        successes += 1
        comparisons.append({
            "ticker": ticker,
            "old_gg": old_gg,
            "new_gg": new_gg,
            "delta": delta,
            "direction": direction,
            "status": "ok",
        })

    elapsed = time.time() - t0

    # Write weekly refresh report
    report_path = _write_weekly_report(comparisons, tickers, elapsed)

    # Summary
    print(f"\n{'='*70}")
    print("Weekly Refresh Summary")
    print(f"{'='*70}")
    print(f"  Processed: {successes}/{len(tickers)}")
    print(f"  Failures:  {failures}")
    print(f"  Time:      {elapsed:.1f}s (budget: {budget}s)")
    if report_path:
        print(f"  Report:    {report_path}")
    print()

    return {
        "status": "ok" if failures == 0 else "partial",
        "comparisons": comparisons,
        "successes": successes,
        "failures": failures,
        "report_path": report_path,
        "elapsed": elapsed,
    }


def _write_weekly_report(
    comparisons: List[Dict[str, Any]],
    tickers: List[str],
    elapsed: float,
) -> Optional[str]:
    """Write the weekly GG refresh report to output/weekly/YYYY-MM-DD_refresh.md."""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    threshold = DEFAULT_CONFIG.threshold_ii * 100

    _WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    filepath = _WEEKLY_DIR / f"{today}_refresh.md"

    lines = []
    lines.append(f"# Weekly GG Refresh -- {today}")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Tickers Refreshed**: {len([c for c in comparisons if c['status'] == 'ok'])}/{len(tickers)}")
    lines.append(f"**Threshold II**: {threshold:.2f}%")
    lines.append(f"**Processing Time**: {elapsed:.1f}s")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Comparison table
    lines.append("## GG Comparison")
    lines.append("")
    lines.append("| Ticker | Old GG | New GG | Change | Direction | vs Threshold | Status |")
    lines.append("|--------|-------:|-------:|-------:|:---------:|:------------:|:------:|")

    for c in comparisons:
        old_str = f"{c['old_gg']:.2f}%" if c.get("old_gg") is not None else "N/A"
        new_str = f"{c['new_gg']:.2f}%" if c.get("new_gg") is not None else "N/A"

        if c.get("delta") is not None:
            delta_str = f"{c['delta']:+.2f}"
        else:
            delta_str = "--"

        direction = c.get("direction", "--")

        if c.get("new_gg") is not None:
            vs_thresh = "PASS" if c["new_gg"] >= threshold else "FAIL"
        else:
            vs_thresh = "--"

        status = c.get("status", "--").upper()
        lines.append(
            f"| **{c['ticker']}** | {old_str} | {new_str} | {delta_str} | "
            f"{direction} | {vs_thresh} | {status} |"
        )

    lines.append("")

    # Notable changes
    notable = [
        c for c in comparisons
        if c.get("delta") is not None and abs(c["delta"]) >= 1.0
    ]
    if notable:
        lines.append("## Notable Changes (|delta| >= 1 pct pt)")
        lines.append("")
        for c in sorted(notable, key=lambda x: abs(x.get("delta", 0)), reverse=True):
            lines.append(
                f"- **{c['ticker']}**: GG moved {c['delta']:+.2f} pct pts "
                f"({c.get('old_gg', 0):.2f}% -> {c.get('new_gg', 0):.2f}%)"
            )
        lines.append("")

    # Threshold crossings
    crossings = []
    for c in comparisons:
        if c.get("old_gg") is not None and c.get("new_gg") is not None:
            was_above = c["old_gg"] >= threshold
            now_above = c["new_gg"] >= threshold
            if was_above and not now_above:
                crossings.append((c["ticker"], "DROPPED BELOW", c["old_gg"], c["new_gg"]))
            elif not was_above and now_above:
                crossings.append((c["ticker"], "ROSE ABOVE", c["old_gg"], c["new_gg"]))

    if crossings:
        lines.append("## Threshold Crossings")
        lines.append("")
        for ticker, crossing, old, new in crossings:
            lines.append(
                f"- **{ticker}** {crossing} Threshold II "
                f"({old:.2f}% -> {new:.2f}%, threshold = {threshold:.2f}%)"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by Turtle Strategy Weekly Scheduler*")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


# ============================================================================
#  Task: Monthly Full Screen
# ============================================================================

def run_monthly() -> Dict[str, Any]:
    """Run the monthly full screening pipeline.

    Steps:
      1. Run finviz_screener.py --with-gg --top-n 10
      2. Compare new candidates vs current holdings
      3. Write output/monthly_screen/YYYY-MM/recommendations.md

    Budget: < 30 minutes (split into sub-tasks).

    Returns:
        Result dict with status, candidates, and report path.
    """
    t0 = time.time()
    budget = getattr(DEFAULT_CONFIG, "monthly_screen_budget", 1800)

    print(f"\n{'='*70}")
    print(f"MONTHLY TASK -- Full Screen")
    print(f"{'='*70}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Budget:  {budget}s ({budget // 60}min)")

    # Read current holdings
    current_tickers = read_tickers()
    print(f"  Current holdings: {', '.join(current_tickers) if current_tickers else '(none)'}")
    print()

    # Step 1: Run the screener
    screener_script = _SCRIPTS_DIR / "finviz_screener.py"
    if not screener_script.exists():
        print(f"  ERROR: {screener_script} not found", file=sys.stderr)
        return {"status": "error", "reason": "screener script not found", "elapsed": 0}

    print("  Step 1: Running Finviz screener with GG scan ...")
    ok, output = _run_subprocess(
        [_PYTHON, str(screener_script), "--with-gg", "--top-n", "10"],
        label="screener",
        timeout=budget,
    )
    if output:
        # Print a condensed version (last 30 lines)
        output_lines = output.strip().split("\n")
        if len(output_lines) > 30:
            print("    ... (truncated)")
        for line in output_lines[-30:]:
            print(f"    {line}")

    if not ok:
        elapsed = time.time() - t0
        print(f"\n  Screener failed after {elapsed:.1f}s")
        return {"status": "error", "reason": "screener failed", "elapsed": elapsed}

    # Step 2: Read screening results
    print("\n  Step 2: Comparing candidates vs holdings ...")
    shortlist_csv = _OUTPUT_DIR / "screen" / "tier2_shortlist.csv"
    new_candidates: List[Dict[str, Any]] = []

    if shortlist_csv.exists():
        try:
            import csv
            with open(shortlist_csv, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get("ticker", "").strip().upper()
                    if ticker:
                        quick_gg = row.get("quick_gg", "")
                        try:
                            gg_val = float(quick_gg) * 100 if quick_gg else None
                        except (ValueError, TypeError):
                            gg_val = None
                        new_candidates.append({
                            "ticker": ticker,
                            "name": row.get("name", ticker),
                            "sector": row.get("sector", "--"),
                            "quick_gg": gg_val,
                            "score": row.get("score", "--"),
                            "in_portfolio": ticker in current_tickers,
                        })
        except Exception as exc:
            print(f"    Warning: Failed to parse shortlist: {exc}")

    if new_candidates:
        print(f"    Found {len(new_candidates)} candidates:")
        for c in new_candidates:
            flag = " (HELD)" if c["in_portfolio"] else " (NEW)"
            gg_str = f"{c['quick_gg']:.2f}%" if c["quick_gg"] is not None else "N/A"
            print(f"      {c['ticker']:<6s} GG={gg_str:>8s} {c.get('name', '')[:30]}{flag}")

    # Identify new entries and departures
    candidate_tickers = {c["ticker"] for c in new_candidates}
    current_set = set(current_tickers)
    new_entries = candidate_tickers - current_set
    retained = candidate_tickers & current_set
    not_in_screen = current_set - candidate_tickers

    print(f"\n    Retained in portfolio : {len(retained)} "
          f"({', '.join(sorted(retained)) if retained else 'none'})")
    print(f"    New candidates        : {len(new_entries)} "
          f"({', '.join(sorted(new_entries)) if new_entries else 'none'})")
    print(f"    Holdings not in screen: {len(not_in_screen)} "
          f"({', '.join(sorted(not_in_screen)) if not_in_screen else 'none'})")

    elapsed = time.time() - t0

    # Step 3: Write monthly report
    report_path = _write_monthly_report(
        new_candidates, current_tickers, new_entries, retained, not_in_screen, elapsed
    )

    print(f"\n{'='*70}")
    print("Monthly Screen Summary")
    print(f"{'='*70}")
    print(f"  Candidates screened : {len(new_candidates)}")
    print(f"  New entries         : {len(new_entries)}")
    print(f"  Retained            : {len(retained)}")
    print(f"  Time                : {elapsed:.1f}s")
    if report_path:
        print(f"  Report              : {report_path}")
    print()

    return {
        "status": "ok",
        "candidates": new_candidates,
        "new_entries": sorted(new_entries),
        "retained": sorted(retained),
        "not_in_screen": sorted(not_in_screen),
        "report_path": report_path,
        "elapsed": elapsed,
    }


def _write_monthly_report(
    candidates: List[Dict[str, Any]],
    current_tickers: List[str],
    new_entries: set,
    retained: set,
    not_in_screen: set,
    elapsed: float,
) -> Optional[str]:
    """Write the monthly recommendations report."""
    now_obj = datetime.now()
    year_month = now_obj.strftime("%Y-%m")
    now = now_obj.strftime("%Y-%m-%d %H:%M:%S")
    threshold = DEFAULT_CONFIG.threshold_ii * 100

    month_dir = _MONTHLY_DIR / year_month
    month_dir.mkdir(parents=True, exist_ok=True)
    filepath = month_dir / "recommendations.md"

    lines = []
    lines.append(f"# Monthly Screen Recommendations -- {year_month}")
    lines.append("")
    lines.append(f"**Generated**: {now}")
    lines.append(f"**Candidates Screened**: {len(candidates)}")
    lines.append(f"**Current Holdings**: {len(current_tickers)}")
    lines.append(f"**Threshold II**: {threshold:.2f}%")
    lines.append(f"**Processing Time**: {elapsed:.1f}s")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Candidate table
    lines.append("## Top Candidates")
    lines.append("")
    lines.append("| Rank | Ticker | Name | Sector | Quick GG | Score | Status |")
    lines.append("|------|--------|------|--------|----------|-------|--------|")

    for i, c in enumerate(candidates, 1):
        gg_str = f"{c['quick_gg']:.2f}%" if c.get("quick_gg") is not None else "N/A"
        if c["ticker"] in retained:
            status = "HELD"
        elif c["ticker"] in new_entries:
            status = "NEW"
        else:
            status = "--"
        name = str(c.get("name", c["ticker"]))[:30]
        lines.append(
            f"| {i} | **{c['ticker']}** | {name} | {c.get('sector', '--')} | "
            f"{gg_str} | {c.get('score', '--')} | {status} |"
        )

    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")

    if new_entries:
        lines.append("### Consider Adding")
        lines.append("")
        for ticker in sorted(new_entries):
            cand = next((c for c in candidates if c["ticker"] == ticker), None)
            if cand:
                gg_str = f"{cand['quick_gg']:.2f}%" if cand.get("quick_gg") is not None else "N/A"
                lines.append(
                    f"- **{ticker}** ({cand.get('name', '')}): "
                    f"Quick GG = {gg_str}. "
                    f"Run full data collection and GG analysis before adding."
                )
        lines.append("")

    if not_in_screen:
        lines.append("### Review for Removal")
        lines.append("")
        for ticker in sorted(not_in_screen):
            lines.append(
                f"- **{ticker}**: Not in current screening results. "
                f"Review if still meets Turtle criteria."
            )
        lines.append("")

    if retained:
        lines.append("### Retained Holdings")
        lines.append("")
        for ticker in sorted(retained):
            cand = next((c for c in candidates if c["ticker"] == ticker), None)
            if cand:
                gg_str = f"{cand['quick_gg']:.2f}%" if cand.get("quick_gg") is not None else "N/A"
                lines.append(f"- **{ticker}**: Still appears in screen. Quick GG = {gg_str}.")
        lines.append("")

    # Action items
    lines.append("## Action Items")
    lines.append("")
    lines.append("- [ ] Review all NEW candidates -- run full GG analysis before adding")
    lines.append("- [ ] Review holdings NOT in screen -- check for deteriorating fundamentals")
    lines.append("- [ ] Update portfolio allocations if changes are warranted")
    lines.append("- [ ] Document rationale for any portfolio changes in US_PORTFOLIO.md")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by Turtle Strategy Monthly Scheduler*")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath)


# ============================================================================
#  Daemon mode
# ============================================================================

_running = True


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _running
    print(f"\n  Received signal {signum}. Shutting down scheduler ...")
    _running = False


def start_daemon(config: Dict[str, Any]) -> None:
    """Start the scheduler in daemon mode (continuous).

    Uses the `schedule` library to run tasks at configured times.
    """
    if schedule is None:
        print(
            "ERROR: 'schedule' library is required for daemon mode.\n"
            "  Install it with:  pip install schedule",
            file=sys.stderr,
        )
        sys.exit(1)

    global _running
    _running = True

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"\n{'='*70}")
    print("TURTLE STRATEGY SCHEDULER -- Daemon Mode")
    print(f"{'='*70}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Config:  {_CONFIG_FILE}")
    print()

    # Schedule daily task
    daily_cfg = config.get("daily", {})
    if daily_cfg.get("enabled", True):
        daily_time = daily_cfg.get("time", "09:00")
        schedule.every().day.at(daily_time).do(run_daily)
        print(f"  Daily alerts  : every day at {daily_time}")
    else:
        print(f"  Daily alerts  : DISABLED")

    # Schedule weekly task
    weekly_cfg = config.get("weekly", {})
    if weekly_cfg.get("enabled", True):
        weekly_day = weekly_cfg.get("day", "monday").lower()
        weekly_time = weekly_cfg.get("time", "09:30")
        day_scheduler = getattr(schedule.every(), weekly_day, None)
        if day_scheduler is not None:
            day_scheduler.at(weekly_time).do(run_weekly)
            print(f"  Weekly refresh : every {weekly_day} at {weekly_time}")
        else:
            print(f"  Weekly refresh : INVALID day '{weekly_day}'", file=sys.stderr)
    else:
        print(f"  Weekly refresh : DISABLED")

    # Schedule monthly task (approximated: run on the configured day each week,
    # but only execute if today matches the configured day-of-month)
    monthly_cfg = config.get("monthly", {})
    if monthly_cfg.get("enabled", True):
        monthly_day = monthly_cfg.get("day", 1)
        monthly_time = monthly_cfg.get("time", "10:00")

        def _monthly_check():
            if datetime.now().day == monthly_day:
                return run_monthly()
            return None

        schedule.every().day.at(monthly_time).do(_monthly_check)
        print(f"  Monthly screen : day {monthly_day} at {monthly_time}")
    else:
        print(f"  Monthly screen : DISABLED")

    print(f"\n  Scheduler running. Press Ctrl+C to stop.")
    print(f"  Next scheduled jobs:")
    for job in schedule.get_jobs():
        print(f"    {job}")
    print()

    # Main loop
    while _running:
        schedule.run_pending()
        time.sleep(30)  # Check every 30 seconds

    print("\n  Scheduler stopped.")


# ============================================================================
#  Status command
# ============================================================================

def show_status() -> None:
    """Show the current schedule status and recent run history."""
    config = load_config()

    print(f"\n{'='*70}")
    print("TURTLE STRATEGY SCHEDULER -- Status")
    print(f"{'='*70}")
    print(f"  Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Config file:  {_CONFIG_FILE}")
    print()

    # Configuration
    print("  Schedule Configuration:")
    daily = config.get("daily", {})
    print(f"    Daily  : {'ENABLED' if daily.get('enabled', True) else 'DISABLED'} "
          f"at {daily.get('time', '09:00')}")

    weekly = config.get("weekly", {})
    print(f"    Weekly : {'ENABLED' if weekly.get('enabled', True) else 'DISABLED'} "
          f"on {weekly.get('day', 'monday')} at {weekly.get('time', '09:30')}")

    monthly = config.get("monthly", {})
    print(f"    Monthly: {'ENABLED' if monthly.get('enabled', True) else 'DISABLED'} "
          f"on day {monthly.get('day', 1)} at {monthly.get('time', '10:00')}")
    print()

    # Portfolio
    tickers = read_tickers()
    print(f"  Portfolio: {', '.join(tickers) if tickers else '(empty)'}")
    print()

    # Recent alert files
    print("  Recent Daily Alerts:")
    alerts_dir = _OUTPUT_DIR / "alerts"
    if alerts_dir.exists():
        alert_files = sorted(alerts_dir.glob("*.md"), reverse=True)[:5]
        if alert_files:
            for f in alert_files:
                size = f.stat().st_size
                print(f"    {f.name} ({size:,} bytes)")
        else:
            print("    (none)")
    else:
        print("    (directory not created yet)")

    # Recent weekly reports
    print("\n  Recent Weekly Refreshes:")
    if _WEEKLY_DIR.exists():
        weekly_files = sorted(_WEEKLY_DIR.glob("*_refresh.md"), reverse=True)[:5]
        if weekly_files:
            for f in weekly_files:
                size = f.stat().st_size
                print(f"    {f.name} ({size:,} bytes)")
        else:
            print("    (none)")
    else:
        print("    (directory not created yet)")

    # Recent monthly reports
    print("\n  Recent Monthly Screens:")
    if _MONTHLY_DIR.exists():
        monthly_files = sorted(_MONTHLY_DIR.rglob("recommendations.md"), reverse=True)[:5]
        if monthly_files:
            for f in monthly_files:
                rel = f.relative_to(_MONTHLY_DIR)
                size = f.stat().st_size
                print(f"    {rel} ({size:,} bytes)")
        else:
            print("    (none)")
    else:
        print("    (directory not created yet)")

    print()


# ============================================================================
#  CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turtle Strategy Scheduler -- US Equity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Commands:
  start        Run as daemon (continuous scheduler)
  run-daily    Run the daily alert check once
  run-weekly   Run the weekly GG refresh once
  run-monthly  Run the monthly full screen once
  status       Show schedule configuration and recent history

Examples:
  %(prog)s start                    # Start daemon
  %(prog)s run-daily                # Single daily run
  %(prog)s run-weekly               # Single weekly run
  %(prog)s run-monthly              # Single monthly run
  %(prog)s status                   # Show status
""",
    )

    parser.add_argument(
        "command",
        choices=["start", "run-daily", "run-weekly", "run-monthly", "status"],
        help="Command to execute",
    )
    parser.add_argument(
        "--config",
        default=None,
        help=f"Path to schedule config JSON (default: {_CONFIG_FILE})",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load config
    global _CONFIG_FILE
    if args.config:
        _CONFIG_FILE = Path(args.config)
    config = load_config()

    if args.command == "start":
        start_daemon(config)

    elif args.command == "run-daily":
        result = run_daily()
        sys.exit(0 if result["status"] in ("ok", "warnings") else 1)

    elif args.command == "run-weekly":
        result = run_weekly()
        sys.exit(0 if result["status"] in ("ok", "partial") else 1)

    elif args.command == "run-monthly":
        result = run_monthly()
        sys.exit(0 if result["status"] == "ok" else 1)

    elif args.command == "status":
        show_status()
        sys.exit(0)


if __name__ == "__main__":
    main()
