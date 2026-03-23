#!/usr/bin/env python3
"""Portfolio Manager for US Equity Turtle Strategy.

Reads, writes, and updates the US_PORTFOLIO.md file.
Supports:
  - Reading ticker list from portfolio
  - Writing/updating allocation tables
  - Appending change history entries
  - Generating portfolio metrics

Usage:
    # Read tickers from portfolio
    python3 scripts/portfolio_manager.py read-tickers

    # Update portfolio with new GG results
    python3 scripts/portfolio_manager.py update --gg-dir output/

    # Initialize empty portfolio
    python3 scripts/portfolio_manager.py init
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from config import DEFAULT_CONFIG


PORTFOLIO_FILE = os.path.join(
    os.path.dirname(__file__), "..", "output", "US_PORTFOLIO.md"
)


def get_portfolio_path() -> Path:
    return Path(PORTFOLIO_FILE)


def read_tickers(portfolio_path: Optional[str] = None) -> List[str]:
    """Read ticker list from the ## Holdings section of the portfolio file.

    Returns:
        List of ticker strings (e.g., ['AAPL', 'MSFT', 'GOOGL']).
        Empty list if file doesn't exist or section not found.
    """
    path = Path(portfolio_path) if portfolio_path else get_portfolio_path()
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")

    # Find ## Holdings section
    match = re.search(
        r"^## Holdings\s*\n(.+?)(?=\n## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    holdings_text = match.group(1).strip()

    # Parse: could be comma-separated, one per line, or mixed
    # Remove any markdown formatting
    holdings_text = re.sub(r"[*_`]", "", holdings_text)

    # Split by comma, newline, or whitespace
    raw_tickers = re.split(r"[,\n\s]+", holdings_text)

    # Filter to valid ticker-like strings
    tickers = []
    for t in raw_tickers:
        t = t.strip().upper()
        if re.match(r"^[A-Z]{1,5}$", t):
            tickers.append(t)

    return tickers


def read_current_allocation(portfolio_path: Optional[str] = None) -> List[Dict]:
    """Read the current allocation table from the portfolio.

    Returns:
        List of dicts with keys: rank, ticker, allocation, gg, safety_margin, rating, last_updated
    """
    path = Path(portfolio_path) if portfolio_path else get_portfolio_path()
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")

    # Find ## Current Allocation section and its table
    match = re.search(
        r"^## Current Allocation\s*\n(.+?)(?=\n## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    section = match.group(1)

    # Parse markdown table rows
    rows = []
    for line in section.split("\n"):
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 6 and cells[0] != "Rank":
            try:
                rows.append({
                    "rank": int(cells[0]) if cells[0].isdigit() else 0,
                    "ticker": cells[1].replace("**", ""),
                    "allocation": cells[2].replace("%", ""),
                    "gg": cells[3].replace("%", ""),
                    "safety_margin": cells[4],
                    "rating": cells[5],
                    "last_updated": cells[6] if len(cells) > 6 else "",
                })
            except (ValueError, IndexError):
                continue

    return rows


def generate_portfolio_md(
    tickers: List[str],
    allocations: List[Dict],
    change_entry: Optional[str] = None,
    previous_content: Optional[str] = None,
) -> str:
    """Generate the full US_PORTFOLIO.md content.

    Args:
        tickers: List of ticker symbols.
        allocations: List of dicts with ticker, allocation, gg, safety_margin, rating.
        change_entry: New changelog entry to prepend to history.
        previous_content: Existing file content (to preserve history section).

    Returns:
        Complete markdown content for US_PORTFOLIO.md.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    rf = DEFAULT_CONFIG.risk_free_rate * 100
    threshold = DEFAULT_CONFIG.threshold_ii * 100

    lines = []
    lines.append("# US Equity Portfolio — Turtle Strategy")
    lines.append("")
    lines.append(f"**Last Updated**: {today}")
    lines.append(f"**Threshold II**: {threshold:.2f}% (Rf {rf:.2f}% + 3%)")
    lines.append("")

    # Holdings section
    lines.append("## Holdings")
    lines.append(", ".join(tickers) if tickers else "_No holdings_")
    lines.append("")

    # Current Allocation table
    lines.append("## Current Allocation")
    lines.append("")
    lines.append("| Rank | Ticker | Allocation | GG | Safety Margin | Rating | Last Updated |")
    lines.append("|------|--------|-----------|-----|---------------|--------|-------------|")

    if allocations:
        # Sort by GG descending
        sorted_allocs = sorted(
            allocations,
            key=lambda x: float(x.get("gg", 0) or 0),
            reverse=True,
        )
        for i, a in enumerate(sorted_allocs, 1):
            ticker = a.get("ticker", "—")
            alloc = a.get("allocation", "—")
            gg = a.get("gg", "—")
            margin = a.get("safety_margin", "—")
            rating = a.get("rating", "—")
            updated = a.get("last_updated", today)
            lines.append(f"| {i} | **{ticker}** | {alloc}% | {gg}% | {margin} pct | {rating} | {updated} |")
    else:
        lines.append("| — | _Empty_ | — | — | — | — | — |")

    lines.append("")

    # Portfolio Metrics
    lines.append("## Portfolio Metrics")
    lines.append("")
    if allocations:
        weighted_gg = sum(
            float(a.get("allocation", 0) or 0) / 100 * float(a.get("gg", 0) or 0)
            for a in allocations
        )
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Weighted GG | {weighted_gg:.2f}% |")
        lines.append(f"| Threshold II | {threshold:.2f}% |")
        lines.append(f"| Threshold Multiple | {weighted_gg / threshold:.2f}x |" if threshold > 0 else "")
        lines.append(f"| Number of Holdings | {len(tickers)} |")
    lines.append("")

    # Allocation Change History
    lines.append("## Allocation Change History")
    lines.append("")

    if change_entry:
        lines.append(change_entry)
        lines.append("")

    # Preserve previous history
    if previous_content:
        prev_match = re.search(
            r"^## Allocation Change History\s*\n(.+?)(?=\n## |\Z)",
            previous_content,
            re.MULTILINE | re.DOTALL,
        )
        if prev_match:
            prev_history = prev_match.group(1).strip()
            if prev_history:
                lines.append(prev_history)
                lines.append("")

    # Individual Analysis links
    lines.append("## Individual Analysis")
    lines.append("")
    for t in tickers:
        lines.append(f"- **{t}**: `output/{t}/analysis.md`")
    lines.append("")

    return "\n".join(lines)


def create_change_entry(
    action: str,
    changes: List[str],
    rationale: str,
    source: str = "Manual",
) -> str:
    """Create a formatted changelog entry.

    Args:
        action: Brief action description (e.g., "Initial Portfolio", "Quarterly Rebalance").
        changes: List of change descriptions.
        rationale: Overall reasoning.
        source: Data source used.

    Returns:
        Formatted markdown changelog entry.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"### {today} — {action}")
    lines.append(f"**Source**: {source}")
    lines.append("")
    for change in changes:
        lines.append(f"- {change}")
    lines.append("")
    lines.append(f"**Rationale**: {rationale}")
    lines.append("")
    return "\n".join(lines)


def init_portfolio(tickers: Optional[List[str]] = None) -> str:
    """Initialize an empty or pre-populated portfolio file.

    Returns:
        Path to created file.
    """
    path = get_portfolio_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tickers = tickers or []
    content = generate_portfolio_md(
        tickers=tickers,
        allocations=[],
        change_entry=create_change_entry(
            action="Portfolio Initialized",
            changes=["Created new US equity portfolio"] + (
                [f"Added tickers: {', '.join(tickers)}"] if tickers else []
            ),
            rationale="Initial setup of US Equity Turtle Strategy portfolio.",
            source="Manual",
        ),
    )

    path.write_text(content, encoding="utf-8")
    return str(path)


def update_from_gg_results(gg_dir: str, source: str = "yfinance") -> str:
    """Update portfolio allocations from GG result files.

    Scans gg_dir for {TICKER}/gg_result.md files and updates allocations.

    Returns:
        Path to updated portfolio file.
    """
    path = get_portfolio_path()
    gg_path = Path(gg_dir)

    # Collect GG results
    results = []
    for ticker_dir in sorted(gg_path.iterdir()):
        if not ticker_dir.is_dir():
            continue
        gg_file = ticker_dir / "gg_result.md"
        if not gg_file.exists():
            continue

        content = gg_file.read_text(encoding="utf-8")
        ticker = ticker_dir.name

        # Parse GG value
        gg_match = re.search(r"GG.*?:\s*\*?\*?([\d.]+)%", content)
        gg_val = float(gg_match.group(1)) if gg_match else 0.0

        # Parse safety margin
        margin_match = re.search(r"Safety Margin.*?:\s*\+?([\d.]+)", content)
        margin_val = float(margin_match.group(1)) if margin_match else 0.0

        # Parse pass/fail
        passed = "PASS" in content.upper() or "✅" in content

        results.append({
            "ticker": ticker,
            "gg": gg_val,
            "safety_margin": margin_val,
            "passed": passed,
        })

    if not results:
        print("No GG results found.", file=sys.stderr)
        return str(path)

    # Sort by GG descending
    results.sort(key=lambda x: x["gg"], reverse=True)

    # Filter to passing stocks
    passing = [r for r in results if r["passed"]]
    if not passing:
        passing = results  # Keep all if none pass (for review)

    # Simple equal-weight allocation for passing stocks
    n = len(passing)
    threshold = DEFAULT_CONFIG.threshold_ii * 100

    allocations = []
    today = datetime.now().strftime("%Y-%m-%d")
    for r in passing:
        alloc = round(100 / n, 1) if n > 0 else 0
        rating = "BUY" if r["gg"] >= threshold else "WATCH" if r["gg"] >= threshold * 0.5 else "AVOID"
        allocations.append({
            "ticker": r["ticker"],
            "allocation": str(alloc),
            "gg": f"{r['gg']:.2f}",
            "safety_margin": f"+{r['safety_margin']:.2f}",
            "rating": rating,
            "last_updated": today,
        })

    tickers = [a["ticker"] for a in allocations]

    # Load previous content for history preservation
    prev_content = path.read_text(encoding="utf-8") if path.exists() else None
    prev_tickers = read_tickers() if path.exists() else []

    # Generate change entry
    changes = []
    new_tickers = set(tickers) - set(prev_tickers)
    removed_tickers = set(prev_tickers) - set(tickers)
    for t in new_tickers:
        a = next((x for x in allocations if x["ticker"] == t), None)
        if a:
            changes.append(f"NEW {t}: {a['allocation']}% (GG {a['gg']}%)")
    for t in removed_tickers:
        changes.append(f"REMOVED {t}")
    if not changes:
        changes.append("GG values refreshed, allocations recalculated")

    change_entry = create_change_entry(
        action="Portfolio Update",
        changes=changes,
        rationale=f"Updated with latest {source} data. "
                  f"{len(passing)} stocks pass threshold ({threshold:.1f}%).",
        source=source,
    )

    content = generate_portfolio_md(
        tickers=tickers,
        allocations=allocations,
        change_entry=change_entry,
        previous_content=prev_content,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Portfolio updated: {path}")
    print(f"  Holdings: {', '.join(tickers)}")
    print(f"  Passing threshold: {len(passing)}/{len(results)}")

    return str(path)


def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Manager for US Equity Turtle Strategy",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # read-tickers
    p_read = sub.add_parser("read-tickers", help="Read tickers from portfolio")
    p_read.add_argument("--portfolio", default=PORTFOLIO_FILE, help="Portfolio file path")

    # init
    p_init = sub.add_parser("init", help="Initialize portfolio")
    p_init.add_argument("--tickers", nargs="*", help="Initial tickers")

    # update
    p_update = sub.add_parser("update", help="Update from GG results")
    p_update.add_argument("--gg-dir", default="output/", help="Directory with GG results")
    p_update.add_argument("--source", default="yfinance", help="Data source used")

    args = parser.parse_args()

    if args.command == "read-tickers":
        tickers = read_tickers(args.portfolio)
        if tickers:
            print(",".join(tickers))
        else:
            print("(empty portfolio)")
        return

    if args.command == "init":
        path = init_portfolio(args.tickers)
        print(f"Portfolio initialized: {path}")
        return

    if args.command == "update":
        path = update_from_gg_results(args.gg_dir, args.source)
        return


if __name__ == "__main__":
    main()
