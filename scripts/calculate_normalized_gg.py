#!/usr/bin/env python3
"""Normalized GG Calculator for Cyclical Trough Strategy.

Uses median-based cash flows instead of TTM to avoid penalizing cyclical
stocks at trough. Formula:

    Normalized_AA = Median(5yr OCF) - Median(5yr Capex)
                  + Avg(3yr Buybacks) - Avg(3yr Dividends) - Avg(3yr SBC)

    Normalized_GG = Normalized_AA / Current_Market_Cap * 100

Single-ticker:
    python3 scripts/calculate_normalized_gg.py \\
        --input output/PBR/data_pack.md --code PBR

Batch:
    python3 scripts/calculate_normalized_gg.py \\
        --batch output/cycle/screen/cyclical_candidates.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Local imports (reuse QY parsers)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402
from cycle_config import CYCLE_CONFIG, get_cycle_output_dir  # noqa: E402
from calculate_qy_gg import (  # noqa: E402
    _parse_numeric,
    _parse_markdown_table,
    _extract_market_data,
    _extract_sections,
    _columns_are_descending,
    _METRIC_LABEL_MAP,
)

logger = logging.getLogger("normalized_gg")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class NormalizedGGResult:
    """Container for normalized GG outputs."""

    stock_code: str
    market_cap: float

    # Multi-year series (all in millions USD)
    ocf_series: List[float]
    capex_series: List[float]
    buyback_series: List[float]
    dividend_series: List[float]
    sbc_series: List[float]

    # Medians / averages
    median_ocf: float
    median_capex: float
    avg_buybacks: float
    avg_dividends: float
    avg_sbc: float

    # Calculated
    normalized_aa: float
    normalized_gg: float  # percentage

    # TTM comparison
    ttm_gg: Optional[float]

    # Threshold check
    threshold_pct: float
    safety_margin: float
    pass_threshold: bool

    # Discount to mid-cycle price (if available)
    discount_to_midcycle: Optional[float]


# ---------------------------------------------------------------------------
# Multi-year extraction helpers
# ---------------------------------------------------------------------------

def _all_numeric_values(
    rows: List[Dict[str, Any]],
    metric_key: str,
) -> List[float]:
    """Extract ALL numeric values for a metric across all year columns.

    Returns values in chronological order (oldest to newest).
    """
    if not rows:
        return []

    descending = _columns_are_descending(rows)

    first_header = None
    for row in rows:
        for k in row:
            first_header = k
            break
        break

    for row in rows:
        if first_header is None:
            continue
        label_cell = row.get(first_header, "")
        if not isinstance(label_cell, str):
            continue
        canonical = _METRIC_LABEL_MAP.get(label_cell.strip())
        if canonical == metric_key:
            values = [
                float(v)
                for k, v in row.items()
                if k != first_header and isinstance(v, (int, float))
            ]
            if descending:
                values.reverse()  # convert to chronological
            return values

    return []


def _safe_median(values: List[float]) -> float:
    """Compute median, returning 0 if empty."""
    if not values:
        return 0.0
    return statistics.median(values)


def _safe_avg(values: List[float], n: int = 3) -> float:
    """Compute average of the last n values, returning 0 if empty."""
    if not values:
        return 0.0
    recent = values[-n:] if len(values) >= n else values
    return sum(recent) / len(recent)


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def calculate_normalized_gg(
    input_file: Path,
    stock_code: str,
    threshold: Optional[float] = None,
    rf: Optional[float] = None,
    ttm_gg: Optional[float] = None,
) -> NormalizedGGResult:
    """Calculate Normalized GG from a data-pack markdown file.

    Args:
        input_file: Path to data_pack.md.
        stock_code: Ticker symbol.
        threshold: GG hurdle rate (decimal). Defaults to Rf + 3%.
        rf: Risk-free rate override.
        ttm_gg: TTM GG from QY calculator (for comparison).

    Returns:
        NormalizedGGResult with all calculation outputs.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Data pack not found: {input_file}")

    content = input_file.read_text(encoding="utf-8")

    # Resolve threshold
    if rf is None:
        rf = DEFAULT_CONFIG.risk_free_rate
    if threshold is None:
        threshold = rf + DEFAULT_CONFIG.threshold_premium
    threshold_pct = threshold * 100.0

    # Parse data pack
    market_data = _extract_market_data(content)
    sections = _extract_sections(content)

    market_cap = market_data.get("market_cap", 0.0)
    if market_cap <= 0:
        raise ValueError(
            f"Market cap not found or zero in {input_file}."
        )

    # Extract multi-year series from cash flow
    cf_rows = sections.get("cashflow", {}).get("rows", [])

    ocf_series = _all_numeric_values(cf_rows, "ocf")
    capex_series = [abs(v) for v in _all_numeric_values(cf_rows, "capex")]
    sbc_series = [abs(v) for v in _all_numeric_values(cf_rows, "sbc")]
    dividend_series = [abs(v) for v in _all_numeric_values(cf_rows, "dividends")]

    # Buybacks may be in a separate section
    bb_rows = sections.get("buybacks", {}).get("rows", [])
    buyback_series = [abs(v) for v in _all_numeric_values(bb_rows, "buybacks")]
    if not buyback_series:
        buyback_series = [abs(v) for v in _all_numeric_values(cf_rows, "buybacks")]

    # If capex is missing but we have FCF and OCF, derive it
    if not capex_series and ocf_series:
        fcf_series = _all_numeric_values(cf_rows, "fcf")
        if fcf_series and len(fcf_series) == len(ocf_series):
            capex_series = [
                abs(o - f) for o, f in zip(ocf_series, fcf_series)
            ]

    # Compute medians and averages
    median_years = CYCLE_CONFIG.ocf_capex_median_years
    avg_years = CYCLE_CONFIG.shareholder_avg_years

    # Use up to median_years most recent values
    ocf_for_median = ocf_series[-median_years:] if ocf_series else []
    capex_for_median = capex_series[-median_years:] if capex_series else []

    median_ocf = _safe_median(ocf_for_median)
    median_capex = _safe_median(capex_for_median)
    avg_buybacks = _safe_avg(buyback_series, avg_years)
    avg_dividends = _safe_avg(dividend_series, avg_years)
    avg_sbc = _safe_avg(sbc_series, avg_years)

    # Normalized AA and GG
    normalized_aa = (
        median_ocf
        - median_capex
        + avg_buybacks
        - avg_dividends
        - avg_sbc
    )
    normalized_gg = (normalized_aa / market_cap) * 100.0

    safety_margin = normalized_gg - threshold_pct
    pass_threshold = normalized_gg >= threshold_pct

    # Mid-cycle price estimate (rough): if we know mid-cycle earnings,
    # we can estimate. For now, set to None.
    discount_to_midcycle = None

    return NormalizedGGResult(
        stock_code=stock_code,
        market_cap=market_cap,
        ocf_series=ocf_series,
        capex_series=capex_series,
        buyback_series=buyback_series,
        dividend_series=dividend_series,
        sbc_series=sbc_series,
        median_ocf=median_ocf,
        median_capex=median_capex,
        avg_buybacks=avg_buybacks,
        avg_dividends=avg_dividends,
        avg_sbc=avg_sbc,
        normalized_aa=normalized_aa,
        normalized_gg=normalized_gg,
        ttm_gg=ttm_gg,
        threshold_pct=threshold_pct,
        safety_margin=safety_margin,
        pass_threshold=pass_threshold,
        discount_to_midcycle=discount_to_midcycle,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _fmt(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def format_report(r: NormalizedGGResult) -> str:
    """Render normalized GG markdown report."""
    L: List[str] = []

    L.append(f"# {r.stock_code} -- Normalized GG (Cyclical Strategy)")
    L.append("")
    L.append(f"**Calculated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"**Threshold II**: {_fmt(r.threshold_pct)}%  (Rf + 3%)")
    L.append("")
    L.append("---")
    L.append("")

    # Results
    L.append("## Normalized GG Results")
    L.append("")
    status = "PASS" if r.pass_threshold else "FAIL"
    L.append(f"**Normalized GG**: **{_fmt(r.normalized_gg)}%** -- {status}")
    L.append(f"**Safety Margin**: {_fmt(r.safety_margin)} pct points")
    L.append("")

    L.append("| Method | Value | vs Threshold |")
    L.append("|--------|------:|:------------:|")
    L.append(f"| Normalized GG | {_fmt(r.normalized_gg)}% | {status} |")
    if r.ttm_gg is not None:
        ttm_status = "PASS" if r.ttm_gg >= r.threshold_pct else "FAIL"
        L.append(f"| TTM GG (QY) | {_fmt(r.ttm_gg)}% | {ttm_status} |")
        diff = r.normalized_gg - r.ttm_gg
        L.append(f"| Normalized vs TTM | {_fmt(diff, 2)} pct | {'Higher' if diff > 0 else 'Lower'} |")
    L.append("")

    # Calculation details
    L.append("## Calculation Details")
    L.append("")
    L.append("### Formula")
    L.append("```")
    L.append("Normalized_AA = Median(5yr OCF) - Median(5yr Capex)")
    L.append("              + Avg(3yr Buybacks) - Avg(3yr Dividends) - Avg(3yr SBC)")
    L.append("")
    L.append(f"Normalized_AA = {_fmt(r.median_ocf)} - {_fmt(r.median_capex)}")
    L.append(f"              + {_fmt(r.avg_buybacks)} - {_fmt(r.avg_dividends)} - {_fmt(r.avg_sbc)}")
    L.append(f"Normalized_AA = {_fmt(r.normalized_aa)}")
    L.append("")
    L.append(f"Normalized_GG = {_fmt(r.normalized_aa)} / {_fmt(r.market_cap)} * 100")
    L.append(f"Normalized_GG = {_fmt(r.normalized_gg)}%")
    L.append("```")
    L.append("")

    # Multi-year data
    L.append("## Multi-Year Cash Flow Data (millions USD)")
    L.append("")

    def _series_table(label: str, series: List[float]) -> None:
        if not series:
            L.append(f"- **{label}**: No data")
            return
        years = [f"Y-{len(series) - 1 - i}" for i in range(len(series))]
        L.append(f"### {label}")
        hdr = "| " + " | ".join(["Period"] + years) + " |"
        sep = "| " + " | ".join(["---"] + ["---:"] * len(years)) + " |"
        vals = "| Value | " + " | ".join(_fmt(v) for v in series) + " |"
        L.append(hdr)
        L.append(sep)
        L.append(vals)
        L.append("")

    _series_table("Operating Cash Flow", r.ocf_series)
    _series_table("Capital Expenditures", r.capex_series)
    _series_table("Stock Buybacks", r.buyback_series)
    _series_table("Dividends Paid", r.dividend_series)
    _series_table("Stock-Based Compensation", r.sbc_series)

    # Statistics
    L.append("## Normalization Statistics")
    L.append("")
    L.append("| Component | Method | Value ($M) |")
    L.append("|-----------|--------|----------:|")
    L.append(f"| OCF | Median (5yr) | {_fmt(r.median_ocf)} |")
    L.append(f"| Capex | Median (5yr) | {_fmt(r.median_capex)} |")
    L.append(f"| Buybacks | Avg (3yr) | {_fmt(r.avg_buybacks)} |")
    L.append(f"| Dividends | Avg (3yr) | {_fmt(r.avg_dividends)} |")
    L.append(f"| SBC | Avg (3yr) | {_fmt(r.avg_sbc)} |")
    L.append("")

    # Cyclicality note
    if r.ttm_gg is not None and r.normalized_gg > r.ttm_gg:
        gap = r.normalized_gg - r.ttm_gg
        L.append("## Cyclicality Impact")
        L.append("")
        L.append(f"Normalized GG is **{_fmt(gap)} pct higher** than TTM GG.")
        L.append("This indicates the stock is currently in a trough period where")
        L.append("TTM cash flows understate mid-cycle earning power.")
        L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by Cyclical Trough Strategy — Normalized GG Calculator*")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def _print_summary(r: NormalizedGGResult) -> None:
    w = 70
    print(f"\n{'=' * w}")
    print("Normalized GG Calculator -- Cyclical Trough Strategy")
    print(f"{'=' * w}")
    print(f"  Ticker:          {r.stock_code}")
    print(f"  Market Cap:      ${_fmt(r.market_cap)}M")
    print(f"  Threshold II:    {_fmt(r.threshold_pct)}%")
    print(f"{'=' * w}")
    print(f"\n  Normalized GG:   {r.normalized_gg:>8.2f}%")
    if r.ttm_gg is not None:
        print(f"  TTM GG (QY):     {r.ttm_gg:>8.2f}%")
    print(f"  Safety Margin:   {r.safety_margin:>+8.2f} pct pts")
    status = "PASS" if r.pass_threshold else "FAIL"
    print(f"  Status:          {status}")
    print()


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def run_batch(
    csv_path: Path,
    threshold: Optional[float] = None,
    rf: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Run normalized GG for every ticker in csv_path."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Batch CSV not found: {csv_path}")

    tickers: List[str] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        ticker_col = None
        for fn in fieldnames:
            if fn.strip().lower() in ("ticker", "symbol", "code"):
                ticker_col = fn
                break
        if ticker_col is None and fieldnames:
            ticker_col = fieldnames[0]
        if ticker_col is None:
            raise ValueError(f"Cannot determine ticker column in {csv_path}")
        for row in reader:
            val = row.get(ticker_col, "").strip().upper()
            if val and val not in tickers:
                tickers.append(val)

    project_root = _SCRIPTS_DIR.parent
    results: List[Dict[str, Any]] = []
    successes = 0
    failures = 0

    print(f"\nBatch normalized GG: {len(tickers)} tickers from {csv_path}\n")

    for ticker in tickers:
        data_pack = project_root / "output" / ticker / "data_pack.md"
        if not data_pack.exists():
            # Also check cycle output dir
            data_pack = project_root / "output" / "cycle" / ticker / "data_pack.md"
        if not data_pack.exists():
            logger.warning("  [SKIP] %s -- data_pack.md not found", ticker)
            failures += 1
            results.append({"ticker": ticker, "status": "SKIP", "reason": "no data pack"})
            continue

        try:
            r = calculate_normalized_gg(
                data_pack, ticker, threshold=threshold, rf=rf,
            )

            out_dir = Path(get_cycle_output_dir(ticker))
            report_path = out_dir / "normalized_gg.md"
            report_path.write_text(format_report(r), encoding="utf-8")

            status = "PASS" if r.pass_threshold else "FAIL"
            print(f"  [{status}] {ticker:>6s}  NormGG={r.normalized_gg:6.2f}%  "
                  f"SM={r.safety_margin:+6.2f}  -> {report_path}")

            successes += 1
            results.append({
                "ticker": ticker,
                "status": status,
                "normalized_gg": round(r.normalized_gg, 2),
                "safety_margin": round(r.safety_margin, 2),
                "median_ocf": round(r.median_ocf, 2),
                "median_capex": round(r.median_capex, 2),
                "report": str(report_path),
            })

        except Exception as exc:
            logger.error("  [ERR]  %s -- %s", ticker, exc)
            failures += 1
            results.append({"ticker": ticker, "status": "ERROR", "reason": str(exc)})

    print(f"\nBatch complete: {successes} processed, {failures} skipped/errored "
          f"out of {len(tickers)} tickers.\n")

    # Write summary CSV
    if results:
        summary_csv = csv_path.parent / "normalized_gg_results.csv"
        all_keys: List[str] = []
        seen: set = set()
        for row in results:
            for k in row:
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)
        with open(summary_csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print(f"  Summary written to {summary_csv}\n")

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalized GG Calculator (Cyclical Trough Strategy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--input", type=Path, help="Path to data_pack.md")
    parser.add_argument("--code", help="Stock ticker (e.g. PBR)")
    parser.add_argument("--batch", type=Path, help="CSV with tickers for batch processing")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--rf", type=float, default=None)
    parser.add_argument("--ttm-gg", type=float, default=None,
                        help="TTM GG from QY calculator for comparison")
    parser.add_argument("--output", type=Path, help="Output file path")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.batch:
        run_batch(args.batch, threshold=args.threshold, rf=args.rf)
        return

    if not args.input or not args.code:
        parser.error("Single-ticker mode requires --input and --code.")

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = calculate_normalized_gg(
        input_file=args.input,
        stock_code=args.code,
        threshold=args.threshold,
        rf=args.rf,
        ttm_gg=args.ttm_gg,
    )

    _print_summary(result)

    report = format_report(result)
    if args.output:
        output_file = args.output
    else:
        out_dir = Path(get_cycle_output_dir(args.code))
        output_file = out_dir / "normalized_gg.md"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding="utf-8")
    print(f"  Report saved to: {output_file}")


if __name__ == "__main__":
    main()
