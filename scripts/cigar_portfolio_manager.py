#!/usr/bin/env python3
"""Portfolio Manager for Cigar Butt Deep Value Strategy.

Manages CIGAR_PORTFOLIO.md separately from US_PORTFOLIO.md (Quality Yield)
and CYCLE_PORTFOLIO.md (Cyclical). Enforces cigar-specific rules:
  - Position sizing by NAV tier: T0=10%, T1=8%, T2=5%
  - Sector cap 25%
  - Cash reserve 10%
  - 12-20 holdings

Usage:
    python3 scripts/cigar_portfolio_manager.py read-tickers
    python3 scripts/cigar_portfolio_manager.py update --source yfinance
    python3 scripts/cigar_portfolio_manager.py init
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
from cigar_config import (  # noqa: E402
    CIGAR_CONFIG,
    CIGAR_PORTFOLIO_CONFIG,
    TIER_LABELS,
    SUBTYPE_LABELS,
    max_position_for_tier,
)


_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PORTFOLIO_FILE = os.path.join(_PROJECT_ROOT, CIGAR_PORTFOLIO_CONFIG.portfolio_file)


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
    if "no holdings" in holdings_text.lower() or "empty" in holdings_text.lower():
        return []
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
        if len(cells) >= 8 and cells[0] != "Rank":
            try:
                rows.append({
                    "rank": int(cells[0]) if cells[0].isdigit() else 0,
                    "ticker": cells[1].replace("**", ""),
                    "allocation": cells[2].replace("%", ""),
                    "tier": cells[3],
                    "sub_type": cells[4],
                    "nav_discount": cells[5].replace("%", ""),
                    "pb": cells[6],
                    "div_yield": cells[7].replace("%", ""),
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
    """Generate CIGAR_PORTFOLIO.md content."""
    today = datetime.now().strftime("%Y-%m-%d")
    cfg = CIGAR_CONFIG

    L = []
    L.append("# Cigar Butt Deep Value Portfolio")
    L.append("")
    L.append(f"**Last Updated**: {today}")
    L.append(f"**Strategy**: Cigar Butt Deep Value (separate from Quality Yield & Cyclical)")
    L.append(f"**Max Position**: T0={cfg.t0_max_position:.0%}, T1={cfg.t1_max_position:.0%}, T2={cfg.t2_max_position:.0%}")
    L.append(f"**Cash Reserve**: {cfg.cash_reserve_pct:.0%}")
    L.append(f"**Sector Cap**: {cfg.max_sector_pct:.0%}")
    L.append(f"**Target Holdings**: {cfg.min_holdings}-{cfg.max_holdings}")
    L.append("")

    # Holdings
    L.append("## Holdings")
    L.append(", ".join(tickers) if tickers else "_No holdings_")
    L.append("")

    # Current Allocation
    L.append("## Current Allocation")
    L.append("")
    L.append("| Rank | Ticker | Allocation | Tier | Sub-Type | NAV Discount | P/B | Div Yield |")
    L.append("|------|--------|-----------|------|----------|-------------|-----|-----------|")

    if allocations:
        sorted_allocs = sorted(
            allocations,
            key=lambda x: float(x.get("nav_discount", 0) or 0),
            reverse=True,
        )
        for i, a in enumerate(sorted_allocs, 1):
            ticker = a.get("ticker", "—")
            alloc = a.get("allocation", "—")
            tier = a.get("tier", "—")
            sub_type = a.get("sub_type", "—")
            nav_disc = a.get("nav_discount", "—")
            pb = a.get("pb", "—")
            div_y = a.get("div_yield", "—")
            L.append(f"| {i} | **{ticker}** | {alloc}% | {tier} | {sub_type} | {nav_disc}% | {pb} | {div_y}% |")
    else:
        L.append("| — | _Empty_ | — | — | — | — | — | — |")
    L.append("")

    # Portfolio Metrics
    L.append("## Portfolio Metrics")
    L.append("")
    if allocations:
        total_alloc = sum(float(a.get("allocation", 0) or 0) for a in allocations)
        cash_pct = max(0, 100 - total_alloc)

        # Count by tier
        t0_count = sum(1 for a in allocations if a.get("tier") == "T0")
        t1_count = sum(1 for a in allocations if a.get("tier") == "T1")
        t2_count = sum(1 for a in allocations if a.get("tier") == "T2")

        # Weighted NAV discount
        weighted_disc = sum(
            float(a.get("allocation", 0) or 0) / 100 * float(a.get("nav_discount", 0) or 0)
            for a in allocations
        )

        L.append("| Metric | Value |")
        L.append("|--------|-------|")
        L.append(f"| Weighted NAV Discount | {weighted_disc:.1f}% |")
        L.append(f"| Number of Holdings | {len(tickers)} |")
        L.append(f"| T0 Positions | {t0_count} |")
        L.append(f"| T1 Positions | {t1_count} |")
        L.append(f"| T2 Positions | {t2_count} |")
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
        total_alloc = sum(float(a.get("allocation", 0) or 0) for a in allocations)
        cash_pct = max(0, 100 - total_alloc)
        max_tier_pos = max(
            cfg.t0_max_position if a.get("tier") == "T0" else
            cfg.t1_max_position if a.get("tier") == "T1" else
            cfg.t2_max_position
            for a in allocations
        ) * 100
        pos_ok = max_pos <= max_tier_pos
        L.append(f"| Max Position (tier-based) | {max_tier_pos:.0f}% | {max_pos:.1f}% | {'OK' if pos_ok else 'BREACH'} |")
        L.append(f"| Min Cash Reserve | {cfg.cash_reserve_pct:.0%} | {cash_pct:.1f}% | {'OK' if cash_pct >= cfg.cash_reserve_pct * 100 else 'BREACH'} |")
        L.append(f"| Max Sector Concentration | {cfg.max_sector_pct:.0%} | — | — |")
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
        L.append(f"- **{t}**: `output/cigar/{t}/cigar_nav.md`")
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
    """Initialize empty cigar butt portfolio."""
    path = get_portfolio_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    tickers = tickers or []
    content = generate_portfolio_md(
        tickers=tickers,
        allocations=[],
        change_entry=create_change_entry(
            action="Portfolio Initialized",
            changes=["Created new Cigar Butt Deep Value portfolio"] + (
                [f"Added tickers: {', '.join(tickers)}"] if tickers else []
            ),
            rationale="Initial setup of Cigar Butt Deep Value Strategy.",
            source="Manual",
        ),
    )

    path.write_text(content, encoding="utf-8")
    return str(path)


def update_from_results(source: str = "yfinance") -> str:
    """Update portfolio from NAV calculation results."""
    path = get_portfolio_path()
    cigar_dir = Path(_PROJECT_ROOT) / "output" / "cigar"

    results = []
    for ticker_dir in sorted(cigar_dir.iterdir()):
        if not ticker_dir.is_dir() or ticker_dir.name == "screen":
            continue

        ticker = ticker_dir.name

        # Read NAV result
        nav_file = ticker_dir / "cigar_nav.md"
        if not nav_file.exists():
            continue

        content = nav_file.read_text(encoding="utf-8")

        # Extract tier
        tier_m = re.search(r"\| NAV Tier \| \*\*(\w+)\*\*", content)
        tier = tier_m.group(1) if tier_m else "NONE"

        # Extract NAV discount
        disc_m = re.search(r"\| NAV Discount \| ([\d.]+)%", content)
        nav_discount = float(disc_m.group(1)) if disc_m else 0.0

        # Extract P/B
        pb_m = re.search(r"\| P/B Ratio \| ([\d.]+)", content)
        pb = float(pb_m.group(1)) if pb_m else 0.0

        # Extract div yield
        div_m = re.search(r"\| Div Yield \| ([\d.]+)%", content)
        div_yield = float(div_m.group(1)) if div_m else 0.0

        # Extract ABR verdict
        abr_m = re.search(r"\| ABR \| .+? \((\w+)\)", content)
        abr_v = abr_m.group(1) if abr_m else "N/A"

        if tier == "NONE" or abr_v == "VETO":
            continue

        # Determine sub-type (basic heuristic from available data)
        sub_type = "—"
        if div_yield >= CIGAR_CONFIG.type_a_min_div_yield * 100 and pb <= CIGAR_CONFIG.type_a_max_pb:
            sub_type = "A"

        results.append({
            "ticker": ticker,
            "tier": tier,
            "nav_discount": nav_discount,
            "pb": pb,
            "div_yield": div_yield,
            "sub_type": sub_type,
            "abr_verdict": abr_v,
        })

    if not results:
        print("No cigar NAV results found.", file=sys.stderr)
        return str(path)

    # Sort by NAV discount descending (biggest discount first)
    results.sort(key=lambda x: x["nav_discount"], reverse=True)

    # Position sizing
    max_total = (1 - CIGAR_CONFIG.cash_reserve_pct) * 100  # 90%

    today = datetime.now().strftime("%Y-%m-%d")
    allocations = []
    total_alloc = 0.0

    for r in results:
        if total_alloc >= max_total:
            break
        if len(allocations) >= CIGAR_CONFIG.max_holdings:
            break

        max_pos = max_position_for_tier(r["tier"]) * 100

        # Scale position by NAV discount magnitude
        if r["nav_discount"] >= 50:
            pos_mult = 1.00
        elif r["nav_discount"] >= 30:
            pos_mult = 0.80
        else:
            pos_mult = 0.60

        alloc = round(max_pos * pos_mult, 1)
        alloc = min(alloc, max_total - total_alloc)

        total_alloc += alloc
        allocations.append({
            "ticker": r["ticker"],
            "allocation": str(alloc),
            "tier": r["tier"],
            "sub_type": r["sub_type"],
            "nav_discount": f"{r['nav_discount']:.1f}",
            "pb": f"{r['pb']:.2f}",
            "div_yield": f"{r['div_yield']:.1f}",
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
            changes.append(f"NEW {t}: {a['allocation']}% ({a['tier']}, Disc {a['nav_discount']}%)")
    for t in removed_tickers:
        changes.append(f"REMOVED {t}")
    if not changes:
        changes.append("NAV calculations and tier classifications refreshed")

    change_entry = create_change_entry(
        action="Portfolio Update",
        changes=changes,
        rationale=f"Updated with latest {source} data. "
                  f"{len(allocations)} positions across NAV tiers.",
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

    print(f"Cigar portfolio updated: {path}")
    print(f"  Holdings: {', '.join(tickers)}")
    print(f"  Total allocated: {total_alloc:.1f}%")

    return str(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Manager for Cigar Butt Deep Value Strategy",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read-tickers", help="Read tickers from cigar portfolio")
    p_read.add_argument("--portfolio", default=PORTFOLIO_FILE)

    p_init = sub.add_parser("init", help="Initialize cigar portfolio")
    p_init.add_argument("--tickers", nargs="*", help="Initial tickers")

    p_update = sub.add_parser("update", help="Update from NAV results")
    p_update.add_argument("--source", default="yfinance")

    args = parser.parse_args()

    if args.command == "read-tickers":
        tickers = read_tickers(args.portfolio)
        print(",".join(tickers) if tickers else "(empty portfolio)")

    elif args.command == "init":
        path = init_portfolio(args.tickers)
        print(f"Cigar portfolio initialized: {path}")

    elif args.command == "update":
        update_from_results(args.source)


if __name__ == "__main__":
    main()
