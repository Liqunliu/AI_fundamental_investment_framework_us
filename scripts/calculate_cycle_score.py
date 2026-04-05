#!/usr/bin/env python3
"""Cycle Phase Scoring Engine (C2) for Cyclical Trough Strategy.

Composite score = 40% Company + 35% Sector + 15% Macro + 10% Price

Phases:
  1. Deep Trough   (>= 0.80) -> BUY (max position)
  2. Early Recovery (0.65-0.80) -> BUY (standard)
  3. Mid-Cycle     (0.40-0.65) -> HOLD only
  4. Late Cycle    (0.20-0.40) -> REDUCE
  5. Peak          (< 0.20) -> SELL/AVOID

Usage:
    python3 scripts/calculate_cycle_score.py \\
        --data-pack output/PBR/data_pack.md \\
        --indicators output/cycle/PBR/cycle_data_pack.md \\
        --code PBR
"""

from __future__ import annotations

import argparse
import logging
import re
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402
from cycle_config import (  # noqa: E402
    CYCLE_CONFIG,
    PHASE_LABELS,
    classify_phase,
    phase_label,
    phase_action,
    get_cycle_output_dir,
)
from calculate_qy_gg import (  # noqa: E402
    _extract_market_data,
    _extract_sections,
    _METRIC_LABEL_MAP,
    _columns_are_descending,
)
from calculate_normalized_gg import _all_numeric_values  # noqa: E402

logger = logging.getLogger("cycle_score")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class CycleScoreResult:
    """Container for C2 cycle phase scoring outputs."""

    stock_code: str

    # Sub-scores (each 0.0 - 1.0, higher = more trough-like)
    company_score: float
    sector_score: float
    macro_score: float
    price_score: float

    # Composite
    composite_score: float

    # Phase classification
    phase: int
    phase_name: str
    action: str

    # Component details
    company_details: Dict[str, Any] = field(default_factory=dict)
    sector_details: Dict[str, Any] = field(default_factory=dict)
    macro_details: Dict[str, Any] = field(default_factory=dict)
    price_details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Company fundamentals scoring (40%)
# ---------------------------------------------------------------------------

def _score_company(
    data_pack_content: str,
) -> Tuple[float, Dict[str, Any]]:
    """Score company fundamentals: revenue percentile, EBITDA margin, capex trend.

    Returns (score 0-1, details dict). Higher = more trough-like.
    """
    sections = _extract_sections(data_pack_content)
    details: Dict[str, Any] = {}

    # Revenue percentile in 5yr range
    inc_rows = sections.get("income", {}).get("rows", [])
    rev_series = _all_numeric_values(inc_rows, "revenue")

    rev_score = 0.5  # default mid-range
    if len(rev_series) >= 3:
        current = rev_series[-1]
        low = min(rev_series)
        high = max(rev_series)
        rng = high - low
        if rng > 0:
            # Invert: low revenue = high trough score
            rev_pct = (current - low) / rng
            rev_score = 1.0 - rev_pct  # at trough, rev_pct is low -> score is high
        details["revenue_series"] = [round(v, 2) for v in rev_series]
        details["revenue_percentile"] = round((1.0 - rev_score) * 100, 1)

    # EBITDA margin percentile
    ebitda_series = _all_numeric_values(inc_rows, "ebitda")
    margin_score = 0.5
    if ebitda_series and rev_series and len(ebitda_series) == len(rev_series):
        margins = [
            e / r * 100 if r != 0 else 0
            for e, r in zip(ebitda_series, rev_series)
        ]
        if margins and max(margins) - min(margins) > 0:
            current_margin = margins[-1]
            low = min(margins)
            high = max(margins)
            margin_pct = (current_margin - low) / (high - low)
            margin_score = 1.0 - margin_pct  # low margin = trough
        details["ebitda_margins"] = [round(m, 2) for m in margins]
        details["margin_percentile"] = round((1.0 - margin_score) * 100, 1)

    # Capex trend (declining capex = trough signal)
    cf_rows = sections.get("cashflow", {}).get("rows", [])
    capex_series = [abs(v) for v in _all_numeric_values(cf_rows, "capex")]
    capex_score = 0.5
    if len(capex_series) >= 2:
        recent_change = (capex_series[-1] - capex_series[-2]) / capex_series[-2] if capex_series[-2] != 0 else 0
        # Declining capex => trough (companies cut investment at bottoms)
        if recent_change < -0.15:
            capex_score = 0.85
        elif recent_change < -0.05:
            capex_score = 0.70
        elif recent_change < 0.05:
            capex_score = 0.50
        elif recent_change < 0.15:
            capex_score = 0.30
        else:
            capex_score = 0.15  # rapidly increasing capex = peak
        details["capex_change"] = round(recent_change * 100, 2)

    # Weighted company score
    score = (0.45 * rev_score + 0.35 * margin_score + 0.20 * capex_score)
    details["rev_score"] = round(rev_score, 3)
    details["margin_score"] = round(margin_score, 3)
    details["capex_score"] = round(capex_score, 3)

    return round(score, 4), details


# ---------------------------------------------------------------------------
# Sector indicator scoring (35%)
# ---------------------------------------------------------------------------

def _parse_indicator_md(content: str) -> Dict[str, Any]:
    """Parse cycle_data_pack.md to extract indicator data."""
    result: Dict[str, Any] = {}

    # Extract detected sector
    m = re.search(r"\*\*Detected Sector\*\*:\s*(\w+)", content)
    if m:
        result["detected_sector"] = m.group(1)

    # Extract stock price percentile
    m = re.search(r"\*\*5Y Percentile\*\*:\s*([\d.]+)%", content)
    if m:
        result["stock_percentile"] = float(m.group(1))

    # Extract sector indicator percentile from Primary Sector section
    primary_section = re.search(
        r"## Primary Sector Indicator(.+?)(?=\n## |\Z)",
        content, re.DOTALL,
    )
    if primary_section:
        sec_text = primary_section.group(1)
        m = re.search(r"\*\*5Y Percentile\*\*:\s*([\d.]+)%", sec_text)
        if m:
            result["sector_percentile"] = float(m.group(1))

        # Extract 12M change
        m = re.search(r"\*\*12M Change\*\*:\s*([+-]?[\d.]+)%", sec_text)
        if m:
            result["sector_12m_change"] = float(m.group(1))

    # Extract all sector percentiles from comparison table
    table_section = re.search(
        r"## Sector Indicators Comparison(.+?)(?=\n## |\Z)",
        content, re.DOTALL,
    )
    if table_section:
        result["all_sector_percentiles"] = {}
        for line in table_section.group(1).splitlines():
            if line.strip().startswith("|") and "---" not in line and "Indicator" not in line:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 5:
                    name = cells[0].strip()
                    pct_str = cells[4].replace("%", "").strip()
                    try:
                        result["all_sector_percentiles"][name] = float(pct_str)
                    except ValueError:
                        pass

    # Extract yield curve spread
    m = re.search(r"\*\*10Y-2Y Spread\*\*:\s*([+-]?[\d.]+)%", content)
    if m:
        result["yield_curve_spread"] = float(m.group(1))

    # Extract macro percentiles
    macro_section = re.search(
        r"## Macro Indicators(.+?)(?=\n## |\Z)",
        content, re.DOTALL,
    )
    if macro_section:
        result["macro_percentiles"] = {}
        for line in macro_section.group(1).splitlines():
            if line.strip().startswith("|") and "---" not in line and "Indicator" not in line:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 3:
                    name = cells[0].strip()
                    pct_str = cells[2].replace("%", "").strip()
                    try:
                        result["macro_percentiles"][name] = float(pct_str)
                    except ValueError:
                        pass

    return result


def _score_sector(indicator_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Score sector indicators. Low percentile = trough = high score."""
    details: Dict[str, Any] = {}

    sector_pct = indicator_data.get("sector_percentile", 50.0)
    # Invert: low commodity price = trough => high score
    sector_score = 1.0 - (sector_pct / 100.0)
    details["sector_percentile"] = sector_pct

    # 12M trend: negative change = trough
    change_12m = indicator_data.get("sector_12m_change", 0.0)
    if change_12m < -30:
        trend_score = 0.90
    elif change_12m < -15:
        trend_score = 0.75
    elif change_12m < 0:
        trend_score = 0.55
    elif change_12m < 15:
        trend_score = 0.35
    else:
        trend_score = 0.15
    details["sector_12m_change"] = change_12m
    details["trend_score"] = round(trend_score, 3)

    score = 0.65 * sector_score + 0.35 * trend_score
    return round(score, 4), details


# ---------------------------------------------------------------------------
# Macro scoring (15%)
# ---------------------------------------------------------------------------

def _score_macro(indicator_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Score macro overlay: PMI, yield curve, credit spreads."""
    details: Dict[str, Any] = {}
    scores = []

    # Yield curve: negative spread = recession signal = trough opportunity
    yield_spread = indicator_data.get("yield_curve_spread")
    if yield_spread is not None:
        if yield_spread < -0.5:
            yc_score = 0.85  # deeply inverted
        elif yield_spread < 0:
            yc_score = 0.70  # inverted
        elif yield_spread < 0.5:
            yc_score = 0.50  # flat
        elif yield_spread < 1.5:
            yc_score = 0.35  # normal
        else:
            yc_score = 0.20  # steep (expansion)
        scores.append(yc_score)
        details["yield_spread"] = yield_spread
        details["yield_curve_score"] = round(yc_score, 3)

    # Credit spreads: high HY percentile relative to IG = stress = trough
    macro_pcts = indicator_data.get("macro_percentiles", {})
    hy_names = [k for k in macro_pcts if "High Yield" in k]
    ig_names = [k for k in macro_pcts if "Investment Grade" in k]

    if hy_names and ig_names:
        hy_pct = macro_pcts[hy_names[0]]
        ig_pct = macro_pcts[ig_names[0]]
        # Low HY price (high pct down) = wide spreads = stress = trough
        credit_score = 1.0 - (hy_pct / 100.0)
        scores.append(credit_score)
        details["credit_score"] = round(credit_score, 3)

    # Treasury yield: high yield = restrictive = late cycle / trough
    tnx_names = [k for k in macro_pcts if "10-Year" in k]
    if tnx_names:
        tnx_pct = macro_pcts[tnx_names[0]]
        # High yields can signal tightening -> trough for cyclicals
        if tnx_pct > 80:
            rate_score = 0.70
        elif tnx_pct > 60:
            rate_score = 0.55
        elif tnx_pct > 40:
            rate_score = 0.40
        else:
            rate_score = 0.30  # low rates = expansion
        scores.append(rate_score)
        details["rate_score"] = round(rate_score, 3)

    score = sum(scores) / len(scores) if scores else 0.50
    return round(score, 4), details


# ---------------------------------------------------------------------------
# Price position scoring (10%)
# ---------------------------------------------------------------------------

def _score_price(indicator_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Score stock price position. Low percentile = trough = high score."""
    details: Dict[str, Any] = {}

    stock_pct = indicator_data.get("stock_percentile", 50.0)
    # Invert: low price = trough = high score
    score = 1.0 - (stock_pct / 100.0)

    details["stock_percentile"] = stock_pct
    details["score"] = round(score, 4)

    return round(score, 4), details


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def calculate_cycle_score(
    data_pack_path: Path,
    indicator_path: Path,
    stock_code: str,
) -> CycleScoreResult:
    """Calculate composite cycle score and classify phase.

    Args:
        data_pack_path: Path to ticker's data_pack.md (financial data).
        indicator_path: Path to cycle_data_pack.md (sector/macro indicators).
        stock_code: Ticker symbol.

    Returns:
        CycleScoreResult with phase classification.
    """
    # Read inputs
    if not data_pack_path.exists():
        raise FileNotFoundError(f"Data pack not found: {data_pack_path}")
    if not indicator_path.exists():
        raise FileNotFoundError(f"Indicator pack not found: {indicator_path}")

    dp_content = data_pack_path.read_text(encoding="utf-8")
    ind_content = indicator_path.read_text(encoding="utf-8")

    # Parse indicator data
    indicator_data = _parse_indicator_md(ind_content)

    # Score each component
    company_score, company_details = _score_company(dp_content)
    sector_score, sector_details = _score_sector(indicator_data)
    macro_score, macro_details = _score_macro(indicator_data)
    price_score, price_details = _score_price(indicator_data)

    # Composite score
    cfg = CYCLE_CONFIG
    composite = (
        cfg.weight_company * company_score
        + cfg.weight_sector * sector_score
        + cfg.weight_macro * macro_score
        + cfg.weight_price * price_score
    )

    # Classify phase
    phase = classify_phase(composite)

    return CycleScoreResult(
        stock_code=stock_code,
        company_score=company_score,
        sector_score=sector_score,
        macro_score=macro_score,
        price_score=price_score,
        composite_score=round(composite, 4),
        phase=phase,
        phase_name=phase_label(phase),
        action=phase_action(phase),
        company_details=company_details,
        sector_details=sector_details,
        macro_details=macro_details,
        price_details=price_details,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_report(r: CycleScoreResult) -> str:
    """Render cycle score markdown report."""
    L: List[str] = []

    L.append(f"# {r.stock_code} -- Cycle Phase Score (C2)")
    L.append("")
    L.append(f"**Calculated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append("")
    L.append("---")
    L.append("")

    # Phase result
    L.append("## Cycle Phase Classification")
    L.append("")
    L.append(f"**Composite Score**: **{r.composite_score:.4f}**")
    L.append(f"**Phase**: **{r.phase} — {r.phase_name}**")
    L.append(f"**Action**: {r.action}")
    L.append("")

    # Phase table
    L.append("| Phase | Name | Score Range | Action | Current |")
    L.append("|-------|------|------------|--------|---------|")
    for p_num, (p_name, p_act) in PHASE_LABELS.items():
        marker = " **<<**" if p_num == r.phase else ""
        if p_num == 1:
            rng = ">= 0.80"
        elif p_num == 2:
            rng = "0.65-0.80"
        elif p_num == 3:
            rng = "0.40-0.65"
        elif p_num == 4:
            rng = "0.20-0.40"
        else:
            rng = "< 0.20"
        L.append(f"| {p_num} | {p_name} | {rng} | {p_act} |{marker} |")
    L.append("")

    # Component breakdown
    L.append("## Score Breakdown")
    L.append("")
    L.append("| Component | Weight | Score | Weighted |")
    L.append("|-----------|-------:|------:|---------:|")
    cfg = CYCLE_CONFIG
    components = [
        ("Company Fundamentals", cfg.weight_company, r.company_score),
        ("Sector Indicators", cfg.weight_sector, r.sector_score),
        ("Macro Overlay", cfg.weight_macro, r.macro_score),
        ("Price Position", cfg.weight_price, r.price_score),
    ]
    for name, weight, score in components:
        weighted = weight * score
        L.append(f"| {name} | {weight:.0%} | {score:.4f} | {weighted:.4f} |")
    L.append(f"| **Composite** | **100%** | — | **{r.composite_score:.4f}** |")
    L.append("")

    # Company details
    L.append("## Company Fundamentals Details")
    L.append("")
    cd = r.company_details
    if "revenue_percentile" in cd:
        L.append(f"- Revenue percentile in 5yr range: **{cd['revenue_percentile']:.1f}%**")
    if "margin_percentile" in cd:
        L.append(f"- EBITDA margin percentile: **{cd['margin_percentile']:.1f}%**")
    if "capex_change" in cd:
        L.append(f"- Capex YoY change: **{cd['capex_change']:+.1f}%**")
    L.append(f"- Revenue sub-score: {cd.get('rev_score', 'N/A')}")
    L.append(f"- Margin sub-score: {cd.get('margin_score', 'N/A')}")
    L.append(f"- Capex sub-score: {cd.get('capex_score', 'N/A')}")
    L.append("")

    # Sector details
    L.append("## Sector Indicator Details")
    L.append("")
    sd = r.sector_details
    if "sector_percentile" in sd:
        L.append(f"- Sector commodity percentile: **{sd['sector_percentile']:.1f}%**")
    if "sector_12m_change" in sd:
        L.append(f"- Sector 12M change: **{sd['sector_12m_change']:+.1f}%**")
    L.append("")

    # Macro details
    L.append("## Macro Overlay Details")
    L.append("")
    md = r.macro_details
    if "yield_spread" in md:
        L.append(f"- Yield curve spread (10Y-2Y): **{md['yield_spread']:.2f}%**")
    if "yield_curve_score" in md:
        L.append(f"- Yield curve score: {md['yield_curve_score']}")
    if "credit_score" in md:
        L.append(f"- Credit spread score: {md['credit_score']}")
    if "rate_score" in md:
        L.append(f"- Rate environment score: {md['rate_score']}")
    L.append("")

    # Price details
    L.append("## Price Position Details")
    L.append("")
    pd_ = r.price_details
    if "stock_percentile" in pd_:
        L.append(f"- Stock price 5Y percentile: **{pd_['stock_percentile']:.1f}%**")
        L.append(f"- Price position score: {pd_['score']:.4f}")
    L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by Cyclical Trough Strategy — Cycle Phase Scoring Engine*")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cycle Phase Scoring Engine (C2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--data-pack", type=Path, required=True,
                        help="Path to data_pack.md")
    parser.add_argument("--indicators", type=Path, required=True,
                        help="Path to cycle_data_pack.md")
    parser.add_argument("--code", required=True, help="Stock ticker")
    parser.add_argument("--output", type=Path, help="Output file path")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    result = calculate_cycle_score(
        data_pack_path=args.data_pack,
        indicator_path=args.indicators,
        stock_code=args.code,
    )

    # Console summary
    w = 60
    print(f"\n{'=' * w}")
    print("Cycle Phase Scoring -- Cyclical Trough Strategy")
    print(f"{'=' * w}")
    print(f"  Ticker:     {result.stock_code}")
    print(f"  Composite:  {result.composite_score:.4f}")
    print(f"  Phase:      {result.phase} — {result.phase_name}")
    print(f"  Action:     {result.action}")
    print(f"{'=' * w}")
    print(f"  Company:    {result.company_score:.4f} (x{CYCLE_CONFIG.weight_company:.0%})")
    print(f"  Sector:     {result.sector_score:.4f} (x{CYCLE_CONFIG.weight_sector:.0%})")
    print(f"  Macro:      {result.macro_score:.4f} (x{CYCLE_CONFIG.weight_macro:.0%})")
    print(f"  Price:      {result.price_score:.4f} (x{CYCLE_CONFIG.weight_price:.0%})")
    print()

    # Write report
    report = format_report(result)
    if args.output:
        output_path = args.output
    else:
        out_dir = Path(get_cycle_output_dir(args.code))
        output_path = out_dir / "cycle_score.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"  Report saved to: {output_path}")


if __name__ == "__main__":
    main()
