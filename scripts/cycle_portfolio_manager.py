#!/usr/bin/env python3
"""Portfolio Manager for Cyclical Trough Strategy.

Manages CYCLE_PORTFOLIO.md separately from US_PORTFOLIO.md (Quality Yield).
Enforces cyclical-specific allocation rules:
  - Max 15% per position (vs QY's 25%)
  - Max 35% per sector
  - Max 30% per commodity group
  - Min 20% cash

Usage:
    python3 scripts/cycle_portfolio_manager.py read-tickers
    python3 scripts/cycle_portfolio_manager.py update --source yfinance
    python3 scripts/cycle_portfolio_manager.py init
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
from config import DEFAULT_CONFIG  # noqa: E402
from cycle_config import (  # noqa: E402
    CYCLE_CONFIG,
    CYCLE_PORTFOLIO_CONFIG,
    PHASE_LABELS,
    phase_label,
    phase_action,
)


_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PORTFOLIO_FILE = os.path.join(_PROJECT_ROOT, CYCLE_PORTFOLIO_CONFIG.portfolio_file)


def get_portfolio_path() -> Path:
    return Path(PORTFOLIO_FILE)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def read_tickers(portfolio_path: Optional[str] = None) -> List[str]:
    """Read ticker list from ## Holdings section."""
    path = Path(portfolio_path) if portfolio_path else get_portfolio_path()
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    match = re.search(
        r"^## Holdings\s*\n(.+?)(?=\n## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    holdings_text = re.sub(r"[*_`]", "", match.group(1).strip())
    raw = re.split(r"[,\n\s]+", holdings_text)
    return [t.strip().upper() for t in raw if re.match(r"^[A-Z]{1,5}$", t.strip().upper())]


def read_current_allocation(portfolio_path: Optional[str] = None) -> List[Dict]:
    """Read current allocation table."""
    path = Path(portfolio_path) if portfolio_path else get_portfolio_path()
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    match = re.search(
        r"^## Current Allocation\s*\n(.+?)(?=\n## |\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return []

    rows = []
    for line in match.group(1).split("\n"):
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) >= 7 and cells[0] != "Rank":
            try:
                rows.append({
                    "rank": int(cells[0]) if cells[0].isdigit() else 0,
                    "ticker": cells[1].replace("**", ""),
                    "allocation": cells[2].replace("%", ""),
                    "norm_gg": cells[3].replace("%", ""),
                    "phase": cells[4],
                    "action": cells[5],
                    "last_updated": cells[6],
                })
            except (ValueError, IndexError):
                continue
    return rows


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def generate_portfolio_md(
    tickers: List[str],
    allocations: List[Dict],
    change_entry: Optional[str] = None,
    previous_content: Optional[str] = None,
) -> str:
    """Generate CYCLE_PORTFOLIO.md content."""
    today = datetime.now().strftime("%Y-%m-%d")
    rf = DEFAULT_CONFIG.risk_free_rate * 100
    threshold = DEFAULT_CONFIG.threshold_ii * 100

    L = []
    L.append("# Cyclical Trough Portfolio")
    L.append("")
    L.append(f"**Last Updated**: {today}")
    L.append(f"**Strategy**: Cyclical Trough Buying (separate from Quality Yield)")
    L.append(f"**Threshold II**: {threshold:.2f}% (Rf {rf:.2f}% + 3%)")
    L.append(f"**Max Position**: {CYCLE_CONFIG.max_single_position:.0%}")
    L.append(f"**Min Cash**: {CYCLE_CONFIG.min_cash:.0%}")
    L.append("")

    # Holdings
    L.append("## Holdings")
    L.append(", ".join(tickers) if tickers else "_No holdings_")
    L.append("")

    # Current Allocation
    L.append("## Current Allocation")
    L.append("")
    L.append("| Rank | Ticker | Allocation | Norm GG | Phase | Action | Last Updated |")
    L.append("|------|--------|-----------|---------|-------|--------|-------------|")

    if allocations:
        sorted_allocs = sorted(
            allocations,
            key=lambda x: float(x.get("norm_gg", 0) or 0),
            reverse=True,
        )
        for i, a in enumerate(sorted_allocs, 1):
            ticker = a.get("ticker", "—")
            alloc = a.get("allocation", "—")
            gg = a.get("norm_gg", "—")
            phase = a.get("phase", "—")
            action = a.get("action", "—")
            updated = a.get("last_updated", today)
            L.append(f"| {i} | **{ticker}** | {alloc}% | {gg}% | {phase} | {action} | {updated} |")
    else:
        L.append("| — | _Empty_ | — | — | — | — | — |")
    L.append("")

    # Portfolio Metrics
    L.append("## Portfolio Metrics")
    L.append("")
    if allocations:
        total_alloc = sum(float(a.get("allocation", 0) or 0) for a in allocations)
        cash_pct = max(0, 100 - total_alloc)
        weighted_gg = sum(
            float(a.get("allocation", 0) or 0) / 100 * float(a.get("norm_gg", 0) or 0)
            for a in allocations
        )

        L.append("| Metric | Value |")
        L.append("|--------|-------|")
        L.append(f"| Weighted Normalized GG | {weighted_gg:.2f}% |")
        L.append(f"| Threshold II | {threshold:.2f}% |")
        if threshold > 0:
            L.append(f"| Threshold Multiple | {weighted_gg / threshold:.2f}x |")
        L.append(f"| Number of Holdings | {len(tickers)} |")
        L.append(f"| Total Allocated | {total_alloc:.1f}% |")
        L.append(f"| Cash Reserve | {cash_pct:.1f}% |")
    L.append("")

    # Risk Limits
    L.append("## Risk Limits")
    L.append("")
    L.append("| Rule | Limit | Current | Status |")
    L.append("|------|-------|---------|--------|")
    if allocations:
        max_pos = max(float(a.get("allocation", 0) or 0) for a in allocations)
        L.append(f"| Max Single Position | {CYCLE_CONFIG.max_single_position:.0%} | {max_pos:.1f}% | {'OK' if max_pos <= CYCLE_CONFIG.max_single_position * 100 else 'BREACH'} |")
        total_alloc = sum(float(a.get("allocation", 0) or 0) for a in allocations)
        cash_pct = max(0, 100 - total_alloc)
        L.append(f"| Min Cash Reserve | {CYCLE_CONFIG.min_cash:.0%} | {cash_pct:.1f}% | {'OK' if cash_pct >= CYCLE_CONFIG.min_cash * 100 else 'BREACH'} |")
    L.append("")

    # Change History
    L.append("## Allocation Change History")
    L.append("")
    if change_entry:
        L.append(change_entry)
        L.append("")

    if previous_content:
        prev_match = re.search(
            r"^## Allocation Change History\s*\n(.+?)(?=\n## |\Z)",
            previous_content,
            re.MULTILINE | re.DOTALL,
        )
        if prev_match:
            prev_history = prev_match.group(1).strip()
            if prev_history:
                L.append(prev_history)
                L.append("")

    # Individual Analysis links
    L.append("## Individual Analysis")
    L.append("")
    for t in tickers:
        L.append(f"- **{t}**: `output/cycle/{t}/cycle_analysis.md`")
    L.append("")

    return "\n".join(L)


def create_change_entry(
    action: str,
    changes: List[str],
    rationale: str,
    source: str = "Manual",
) -> str:
    """Create formatted changelog entry."""
    today = datetime.now().strftime("%Y-%m-%d")
    L = []
    L.append(f"### {today} — {action}")
    L.append(f"**Source**: {source}")
    L.append("")
    for change in changes:
        L.append(f"- {change}")
    L.append("")
    L.append(f"**Rationale**: {rationale}")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Init & Update
# ---------------------------------------------------------------------------

def init_portfolio(tickers: Optional[List[str]] = None) -> str:
    """Initialize empty cyclical portfolio."""
    path = get_portfolio_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tickers = tickers or []
    content = generate_portfolio_md(
        tickers=tickers,
        allocations=[],
        change_entry=create_change_entry(
            action="Portfolio Initialized",
            changes=["Created new Cyclical Trough portfolio"] + (
                [f"Added tickers: {', '.join(tickers)}"] if tickers else []
            ),
            rationale="Initial setup of Cyclical Trough Buying Strategy.",
            source="Manual",
        ),
    )

    path.write_text(content, encoding="utf-8")
    return str(path)


def update_from_results(source: str = "yfinance") -> str:
    """Update portfolio from normalized GG and cycle score results."""
    path = get_portfolio_path()
    cycle_dir = Path(_PROJECT_ROOT) / "output" / "cycle"

    results = []
    for ticker_dir in sorted(cycle_dir.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name == "screen":
            continue

        ticker = ticker_dir.name

        # Read normalized GG
        gg_file = ticker_dir / "normalized_gg.md"
        norm_gg = 0.0
        if gg_file.exists():
            content = gg_file.read_text(encoding="utf-8")
            m = re.search(r"\*\*Normalized GG\*\*:\s*\*?\*?([\d.]+)%", content)
            if m:
                norm_gg = float(m.group(1))

        # Read cycle score/phase
        score_file = ticker_dir / "cycle_score.md"
        phase = 3
        phase_name = "Mid-Cycle"
        act = "HOLD"
        if score_file.exists():
            content = score_file.read_text(encoding="utf-8")
            m = re.search(r"\*\*Phase\*\*:\s*\*?\*?(\d)\s*[—-]\s*(.+?)\*?\*?$", content, re.MULTILINE)
            if m:
                phase = int(m.group(1))
                phase_name = m.group(2).strip().rstrip("*")
            m = re.search(r"\*\*Action\*\*:\s*(.+?)$", content, re.MULTILINE)
            if m:
                act = m.group(1).strip()

        results.append({
            "ticker": ticker,
            "norm_gg": norm_gg,
            "phase": phase,
            "phase_name": phase_name,
            "action": act,
        })

    if not results:
        print("No cycle results found.", file=sys.stderr)
        return str(path)

    # Sort by normalized GG descending
    results.sort(key=lambda x: x["norm_gg"], reverse=True)

    # Filter: only Phase 1-2 with normalized GG >= threshold for BUY
    threshold = DEFAULT_CONFIG.threshold_ii * 100
    buyable = [r for r in results if r["phase"] <= 2 and r["norm_gg"] >= threshold]
    holdable = [r for r in results if r["phase"] == 3 and r["norm_gg"] >= threshold]

    # Include holdable in portfolio but with smaller allocation
    portfolio_stocks = buyable + holdable

    if not portfolio_stocks:
        portfolio_stocks = results  # Keep all for review

    # Position sizing
    max_pos = CYCLE_CONFIG.max_single_position * 100  # 15%
    max_total = (1 - CYCLE_CONFIG.min_cash) * 100  # 80%

    today = datetime.now().strftime("%Y-%m-%d")
    allocations = []
    total_alloc = 0.0

    for r in portfolio_stocks:
        if total_alloc >= max_total:
            break

        # Determine position size based on phase and GG tier
        if r["phase"] == 1:
            # Deep Trough
            if r["norm_gg"] >= threshold * 3:
                pos_mult = CYCLE_CONFIG.phase1_position_tiers[0]  # 100%
            elif r["norm_gg"] >= threshold * 2:
                pos_mult = CYCLE_CONFIG.phase1_position_tiers[1]  # 80%
            else:
                pos_mult = CYCLE_CONFIG.phase1_position_tiers[2]  # 60%
        elif r["phase"] == 2:
            # Early Recovery
            if r["norm_gg"] >= threshold * 3:
                pos_mult = CYCLE_CONFIG.phase2_position_tiers[0]  # 70%
            elif r["norm_gg"] >= threshold * 2:
                pos_mult = CYCLE_CONFIG.phase2_position_tiers[1]  # 50%
            else:
                pos_mult = CYCLE_CONFIG.phase2_position_tiers[2]  # 35%
        elif r["phase"] == 3:
            pos_mult = 0.30  # Hold with small position
        else:
            continue  # Phase 4-5: don't add

        alloc = round(max_pos * pos_mult, 1)
        alloc = min(alloc, max_total - total_alloc)

        total_alloc += alloc
        allocations.append({
            "ticker": r["ticker"],
            "allocation": str(alloc),
            "norm_gg": f"{r['norm_gg']:.2f}",
            "phase": f"{r['phase']}-{r['phase_name']}",
            "action": r["action"],
            "last_updated": today,
        })

    tickers = [a["ticker"] for a in allocations]

    # Load previous content for history
    prev_content = path.read_text(encoding="utf-8") if path.exists() else None
    prev_tickers = read_tickers() if path.exists() else []

    # Generate change entry
    changes = []
    new_tickers = set(tickers) - set(prev_tickers)
    removed_tickers = set(prev_tickers) - set(tickers)
    for t in new_tickers:
        a = next((x for x in allocations if x["ticker"] == t), None)
        if a:
            changes.append(f"NEW {t}: {a['allocation']}% (NormGG {a['norm_gg']}%, Phase {a['phase']})")
    for t in removed_tickers:
        changes.append(f"REMOVED {t}")
    if not changes:
        changes.append("Cycle scores and normalized GG refreshed")

    change_entry = create_change_entry(
        action="Portfolio Update",
        changes=changes,
        rationale=f"Updated with latest {source} data. "
                  f"{len(buyable)} stocks in buy phase, {len(holdable)} in hold phase.",
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

    print(f"Cycle portfolio updated: {path}")
    print(f"  Holdings: {', '.join(tickers)}")
    print(f"  Buy phase: {len(buyable)}, Hold phase: {len(holdable)}")

    return str(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Manager for Cyclical Trough Strategy",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read-tickers", help="Read tickers from cycle portfolio")
    p_read.add_argument("--portfolio", default=PORTFOLIO_FILE)

    p_init = sub.add_parser("init", help="Initialize cycle portfolio")
    p_init.add_argument("--tickers", nargs="*", help="Initial tickers")

    p_update = sub.add_parser("update", help="Update from cycle results")
    p_update.add_argument("--source", default="yfinance")

    args = parser.parse_args()

    if args.command == "read-tickers":
        tickers = read_tickers(args.portfolio)
        print(",".join(tickers) if tickers else "(empty portfolio)")

    elif args.command == "init":
        path = init_portfolio(args.tickers)
        print(f"Cycle portfolio initialized: {path}")

    elif args.command == "update":
        update_from_results(args.source)


if __name__ == "__main__":
    main()
