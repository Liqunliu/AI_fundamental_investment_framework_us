#!/usr/bin/env python3
"""Two-Tier Screening Pipeline — Finviz → yfinance → GG → Factor Inputs → EDGAR.

Orchestrates the full pipeline:
  Tier 1   : Finviz screening + quick GG     (finviz_screener.py)
  Tier 2   : Deep analysis for shortlisted tickers:
    a. Data collection  (yfinance_collector.py)
    b. GG calculation   (calculate_qy_gg.py)
    c. Factor inputs    (calculate_factor_inputs.py)
    d. EDGAR download + parse (optional)

Features:
  - Checkpoint/resume: tracks completed tickers in pipeline_checkpoint.json
  - Cache-aware: leverages disk cache to avoid redundant API calls
  - Produces final_candidates.csv + summary.md

Usage:
    python3 scripts/screen_pipeline.py --top-n 5
    python3 scripts/screen_pipeline.py --top-n 10 --with-edgar
    python3 scripts/screen_pipeline.py --skip-tier1  # Resume from existing shortlist
    python3 scripts/screen_pipeline.py --no-cache
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve script dir for sibling imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_OUTPUT_SCREEN = _PROJECT_ROOT / "output" / "screen"

sys.path.insert(0, str(_SCRIPT_DIR))
from config import DEFAULT_CONFIG  # noqa: E402


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------

def _checkpoint_path() -> Path:
    return _OUTPUT_SCREEN / "pipeline_checkpoint.json"


def _load_checkpoint() -> dict:
    cp = _checkpoint_path()
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"completed": [], "failed": [], "started_at": None}


def _save_checkpoint(data: dict) -> None:
    _OUTPUT_SCREEN.mkdir(parents=True, exist_ok=True)
    _checkpoint_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Script runners
# ---------------------------------------------------------------------------

def _run_script(args: list, label: str, timeout: int = 300) -> bool:
    """Run a Python script via subprocess. Returns True on success."""
    print(f"    [{label}] {' '.join(args[:4])}...")
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-200:]
            print(f"    [{label}] FAILED (rc={result.returncode}): {stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    [{label}] TIMEOUT after {timeout}s")
        return False
    except Exception as exc:
        print(f"    [{label}] ERROR: {exc}")
        return False


def _run_data_collection(ticker: str, no_cache: bool) -> bool:
    """Run yfinance_collector.py for a ticker."""
    args = [
        sys.executable, str(_SCRIPT_DIR / "yfinance_collector.py"),
        "--ticker", ticker,
        "--output", str(_PROJECT_ROOT / "output" / ticker / "data_pack.md"),
    ]
    if no_cache:
        args.append("--no-cache")
    return _run_script(args, "collect")


def _run_gg_calc(ticker: str) -> bool:
    """Run calculate_qy_gg.py for a ticker."""
    data_pack = _PROJECT_ROOT / "output" / ticker / "data_pack.md"
    return _run_script([
        sys.executable, str(_SCRIPT_DIR / "calculate_qy_gg.py"),
        "--input", str(data_pack),
        "--code", ticker,
    ], "GG")


def _run_factor_inputs(ticker: str) -> bool:
    """Run calculate_factor_inputs.py for a ticker."""
    data_pack = _PROJECT_ROOT / "output" / ticker / "data_pack.md"
    return _run_script([
        sys.executable, str(_SCRIPT_DIR / "calculate_factor_inputs.py"),
        "--input", str(data_pack),
        "--code", ticker,
    ], "factor_inputs")


def _run_edgar(ticker: str) -> bool:
    """Run edgar_downloader.py + edgar_parser.py for a ticker."""
    # Download
    ok = _run_script([
        sys.executable, str(_SCRIPT_DIR / "edgar_downloader.py"),
        "--ticker", ticker,
    ], "EDGAR-dl", timeout=60)
    if not ok:
        return False

    # Find the downloaded HTML via filing_meta.json
    output_dir = _PROJECT_ROOT / "output" / ticker
    meta_path = output_dir / f"{ticker}_filing_meta.json"
    if not meta_path.exists():
        print(f"    [EDGAR-parse] No filing_meta.json found, skipping parse")
        return False

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        # Derive HTML filename from primary_document
        primary_doc = meta.get("primary_document", "")
        if primary_doc:
            # Use the extension from primary_document
            ext = Path(primary_doc).suffix or ".html"
            form_type = meta.get("form_type", "10-K")
            form_tag = form_type.replace("-", "")  # "10-K" -> "10K", "20-F" -> "20F"
            html_name = f"{ticker}_{form_tag}{ext}"
        else:
            html_name = f"{ticker}_10K.html"
    except (json.JSONDecodeError, OSError):
        html_name = f"{ticker}_10K.html"

    html_path = output_dir / html_name
    if not html_path.exists():
        # Fallback: try to find any filing HTML
        for ext in (".html", ".htm"):
            for prefix in (f"{ticker}_10K", f"{ticker}_20F", f"{ticker}_10k", f"{ticker}_20f"):
                candidate = output_dir / f"{prefix}{ext}"
                if candidate.exists():
                    html_path = candidate
                    break

    if not html_path.exists():
        print(f"    [EDGAR-parse] Filing HTML not found, skipping parse")
        return False

    # Parse
    return _run_script([
        sys.executable, str(_SCRIPT_DIR / "edgar_parser.py"),
        "--input", str(html_path),
        "--ticker", ticker,
    ], "EDGAR-parse")


# ---------------------------------------------------------------------------
# GG extraction from output file
# ---------------------------------------------------------------------------

def _extract_gg_from_file(ticker: str) -> Optional[float]:
    """Parse GG value from {ticker}_GG.md output file."""
    gg_path = _PROJECT_ROOT / "output" / ticker / f"{ticker}_GG.md"
    if not gg_path.exists():
        return None
    try:
        text = gg_path.read_text(encoding="utf-8")
        # Look for "GG = X.XX%" or "GG: X.XX%" or "**GG**: X.XX%"
        m = re.search(r"GG\s*[=:]\s*([+-]?\d+\.?\d*)%", text)
        if m:
            return float(m.group(1)) / 100
        # Also try "Penetration Return Rate"
        m = re.search(r"Penetration Return Rate\s*[=:]\s*([+-]?\d+\.?\d*)%", text)
        if m:
            return float(m.group(1)) / 100
    except (OSError, ValueError):
        pass
    return None


def _extract_warnings_count(ticker: str) -> tuple:
    """Read warnings.json and return (total_count, high_count)."""
    warn_path = _PROJECT_ROOT / "output" / ticker / "warnings.json"
    if not warn_path.exists():
        return (0, 0)
    try:
        data = json.loads(warn_path.read_text(encoding="utf-8"))
        total = len(data)
        high = sum(1 for w in data if w.get("severity") == "HIGH")
        return (total, high)
    except (json.JSONDecodeError, OSError):
        return (0, 0)


def _extract_info_from_data_pack(ticker: str) -> dict:
    """Extract key fields from data_pack.md for the final CSV."""
    dp_path = _PROJECT_ROOT / "output" / ticker / "data_pack.md"
    result = {"name": "", "sector": "", "market_cap": "", "pe": "", "pb": ""}
    if not dp_path.exists():
        return result
    try:
        text = dp_path.read_text(encoding="utf-8")[:5000]  # First 5K is enough
        # Company name from header
        m = re.search(r"Data Pack:\s*(.+?)\s*\(", text)
        if m:
            result["name"] = m.group(1).strip()
        # Sector
        m = re.search(r"\*\*Sector\*\*:\s*(.+)", text)
        if m:
            result["sector"] = m.group(1).strip()
        # Market cap
        m = re.search(r"\*\*Market Cap\*\*:\s*\$?([\d,]+\.?\d*)", text)
        if m:
            result["market_cap"] = m.group(1).replace(",", "")
        # PE
        m = re.search(r"\*\*(?:PE|P/E|PE \(TTM\))\*\*:\s*([\d.]+)", text)
        if m:
            result["pe"] = m.group(1)
        # PB
        m = re.search(r"\*\*(?:PB|P/B)\*\*:\s*([\d.]+)", text)
        if m:
            result["pb"] = m.group(1)
    except OSError:
        pass
    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    top_n: int = 10,
    skip_tier1: bool = False,
    with_edgar: bool = True,
    no_cache: bool = False,
) -> dict:
    """Execute the full screening pipeline.

    Args:
        top_n: Number of top tickers from Tier 1.5 to process in Tier 2.
        skip_tier1: If True, resume from existing tier2_shortlist.csv.
        with_edgar: If True, include EDGAR download+parse for each ticker.
        no_cache: If True, force fresh data fetch (bypass cache).

    Returns:
        dict with keys: tickers_processed, tickers_failed, output_files.
    """
    _OUTPUT_SCREEN.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    print("=" * 80)
    print("US EQUITY QUALITY YIELD STRATEGY — Full Screening Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Settings: top_n={top_n}, edgar={with_edgar}, cache={'off' if no_cache else 'on'}")
    print("=" * 80)

    # ---------------------------------------------------------------
    # Tier 1 + 1.5: Finviz screening + quick GG
    # ---------------------------------------------------------------
    tickers: List[str] = []

    if skip_tier1:
        shortlist_csv = _OUTPUT_SCREEN / "tier2_shortlist.csv"
        if not shortlist_csv.exists():
            print(f"ERROR: --skip-tier1 but {shortlist_csv} not found", file=sys.stderr)
            sys.exit(1)
        tickers = _read_tickers_from_csv(shortlist_csv, top_n)
        print(f"\nResuming from existing shortlist: {len(tickers)} tickers")
    else:
        print("\n--- TIER 1 + 1.5: Finviz Screening + Quick GG ---")
        cache_flag = ["--no-cache"] if no_cache else []
        ok = _run_script([
            sys.executable, str(_SCRIPT_DIR / "finviz_screener.py"),
            "--with-gg", "--top-n", str(top_n),
        ], "finviz", timeout=600)
        if not ok:
            print("ERROR: Finviz screening failed", file=sys.stderr)
            sys.exit(1)

        shortlist_csv = _OUTPUT_SCREEN / "tier2_shortlist.csv"
        if not shortlist_csv.exists():
            print("ERROR: tier2_shortlist.csv was not produced", file=sys.stderr)
            sys.exit(1)
        tickers = _read_tickers_from_csv(shortlist_csv, top_n)

    if not tickers:
        print("No tickers to process. Exiting.")
        return {"tickers_processed": 0, "tickers_failed": 0, "output_files": []}

    print(f"\nTier 2 tickers: {', '.join(tickers)}")

    # ---------------------------------------------------------------
    # Tier 2: Deep analysis per ticker
    # ---------------------------------------------------------------
    checkpoint = _load_checkpoint()
    completed = set(checkpoint.get("completed", []))
    failed_tickers: List[str] = []
    processed: List[str] = []

    if not checkpoint.get("started_at"):
        checkpoint["started_at"] = datetime.now().isoformat()

    print(f"\n--- TIER 2: Deep Analysis ({len(tickers)} tickers) ---")
    if completed:
        print(f"  Resuming — already completed: {', '.join(sorted(completed))}")

    for i, ticker in enumerate(tickers, 1):
        if ticker in completed:
            print(f"\n  [{i}/{len(tickers)}] {ticker} — SKIPPED (checkpoint)")
            processed.append(ticker)
            continue

        print(f"\n  [{i}/{len(tickers)}] {ticker}")
        ticker_t0 = time.time()
        success = True

        # Step a: Data collection
        if not (_PROJECT_ROOT / "output" / ticker / "data_pack.md").exists():
            if not _run_data_collection(ticker, no_cache):
                print(f"    FAILED: data collection — skipping {ticker}")
                failed_tickers.append(ticker)
                success = False
        else:
            print(f"    [collect] data_pack.md exists, skipping")

        # Step b: GG calculation
        if success:
            gg_file = _PROJECT_ROOT / "output" / ticker / f"{ticker}_GG.md"
            if not gg_file.exists():
                if not _run_gg_calc(ticker):
                    print(f"    WARNING: GG calculation failed for {ticker}")
                    # Non-fatal — continue
            else:
                print(f"    [GG] {ticker}_GG.md exists, skipping")

        # Step c: Factor inputs
        if success:
            fi_file = _PROJECT_ROOT / "output" / ticker / f"{ticker}_factor_inputs.md"
            if not fi_file.exists():
                if not _run_factor_inputs(ticker):
                    print(f"    WARNING: factor inputs failed for {ticker}")
                    # Non-fatal
            else:
                print(f"    [factor_inputs] {ticker}_factor_inputs.md exists, skipping")

        # Step d: EDGAR (optional)
        if success and with_edgar:
            sections_file = _PROJECT_ROOT / "output" / ticker / "filing_sections.json"
            if not sections_file.exists():
                if not _run_edgar(ticker):
                    print(f"    WARNING: EDGAR failed for {ticker} — continuing without")
            else:
                print(f"    [EDGAR] filing_sections.json exists, skipping")

        elapsed_t = time.time() - ticker_t0
        if success:
            processed.append(ticker)
            checkpoint["completed"] = list(set(checkpoint.get("completed", [])) | {ticker})
            _save_checkpoint(checkpoint)
            print(f"    Done ({elapsed_t:.1f}s)")
        else:
            checkpoint["failed"] = list(set(checkpoint.get("failed", [])) | {ticker})
            _save_checkpoint(checkpoint)

    # ---------------------------------------------------------------
    # Final output: build candidates CSV + summary
    # ---------------------------------------------------------------
    print(f"\n--- Building final output ---")
    output_files = _build_final_output(processed, tickers)

    elapsed_total = time.time() - t_start
    print(f"\n{'='*80}")
    print("Pipeline Complete")
    print(f"{'='*80}")
    print(f"  Tickers processed : {len(processed)}")
    print(f"  Tickers failed    : {len(failed_tickers)}")
    print(f"  Total time        : {elapsed_total:.1f}s")
    for f in output_files:
        print(f"  Output: {f}")
    print(f"\nDone.  [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")

    # Clean up checkpoint on full success
    if not failed_tickers and len(processed) == len(tickers):
        cp = _checkpoint_path()
        if cp.exists():
            cp.unlink()

    return {
        "tickers_processed": len(processed),
        "tickers_failed": len(failed_tickers),
        "output_files": output_files,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_tickers_from_csv(csv_path: Path, limit: int) -> List[str]:
    """Read ticker symbols from a CSV file (expects 'ticker' column)."""
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            tickers = []
            for row in reader:
                t = row.get("ticker", row.get("Ticker", "")).strip().upper()
                if t and len(tickers) < limit:
                    tickers.append(t)
            return tickers
    except (OSError, KeyError) as exc:
        print(f"ERROR reading {csv_path}: {exc}", file=sys.stderr)
        return []


def _build_final_output(processed: List[str], all_tickers: List[str]) -> List[str]:
    """Build final_candidates.csv and summary.md from processed tickers."""
    output_files = []

    # --- final_candidates.csv ---
    csv_path = _OUTPUT_SCREEN / "final_candidates.csv"
    threshold_ii = DEFAULT_CONFIG.threshold_ii

    rows = []
    for ticker in processed:
        info = _extract_info_from_data_pack(ticker)
        gg = _extract_gg_from_file(ticker)
        warn_total, warn_high = _extract_warnings_count(ticker)

        gg_str = f"{gg * 100:.2f}%" if gg is not None else "N/A"
        gg_vs = ""
        if gg is not None:
            diff = (gg - threshold_ii) * 100
            gg_vs = f"{diff:+.2f}pp"

        rows.append({
            "ticker": ticker,
            "name": info["name"],
            "sector": info["sector"],
            "market_cap": info["market_cap"],
            "full_gg": gg_str,
            "gg_vs_threshold": gg_vs,
            "pe": info["pe"],
            "pb": info["pb"],
            "warnings_count": warn_total,
            "warnings_high": warn_high,
        })

    if rows:
        fieldnames = list(rows[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Written: {csv_path}")
        output_files.append(str(csv_path))

    # --- summary.md ---
    summary_path = _OUTPUT_SCREEN / "summary.md"
    lines = [
        f"# Screening Pipeline Summary",
        f"",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Tickers processed**: {len(processed)} / {len(all_tickers)}",
        f"**Threshold II**: {threshold_ii * 100:.1f}%",
        f"",
        f"## Candidates",
        f"",
        f"| Ticker | Name | GG | vs Threshold | Warnings |",
        f"|--------|------|-----|-------------|----------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['ticker']} | {r['name'][:30]} | {r['full_gg']} "
            f"| {r['gg_vs_threshold']} | {r['warnings_count']} ({r['warnings_high']} HIGH) |"
        )
    lines.append("")
    lines.append("## Output Files")
    lines.append("")
    for ticker in processed:
        ticker_dir = f"output/{ticker}/"
        lines.append(f"- `{ticker_dir}`: data_pack.md, {ticker}_GG.md, {ticker}_factor_inputs.md")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by screen_pipeline.py*")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Written: {summary_path}")
    output_files.append(str(summary_path))

    return output_files


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Full Tier 1 → Tier 2 screening pipeline for US Equity Quality Yield Strategy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --top-n 5                         # Quick: top 5 tickers
  %(prog)s --top-n 10 --with-edgar           # Full: top 10 + EDGAR
  %(prog)s --skip-tier1                      # Resume from shortlist
  %(prog)s --top-n 3 --no-cache --no-edgar   # Fresh data, no EDGAR
        """,
    )
    parser.add_argument(
        "--top-n", type=int,
        default=DEFAULT_CONFIG.pipeline_top_n,
        help=f"Number of tickers for deep analysis (default: {DEFAULT_CONFIG.pipeline_top_n})",
    )
    parser.add_argument(
        "--skip-tier1", action="store_true",
        help="Skip Finviz screening, resume from existing tier2_shortlist.csv",
    )
    parser.add_argument(
        "--with-edgar", action="store_true",
        default=DEFAULT_CONFIG.pipeline_with_edgar,
        help="Include EDGAR download + parse (default: on)",
    )
    parser.add_argument(
        "--no-edgar", action="store_true",
        help="Disable EDGAR download + parse",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Bypass disk cache and force fresh data fetch",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with_edgar = args.with_edgar and not args.no_edgar
    run_pipeline(
        top_n=args.top_n,
        skip_tier1=args.skip_tier1,
        with_edgar=with_edgar,
        no_cache=args.no_cache,
    )


if __name__ == "__main__":
    main()
