#!/usr/bin/env python3
"""Convert US Quality Yield Strategy analysis.md to styled HTML dashboard.

Usage:
    python3 scripts/report_to_html.py \
        --input output/PYPL/analysis.md \
        --output output/PYPL/analysis.html

    # Screening summary mode:
    python3 scripts/report_to_html.py \
        --screening output/screen/final_candidates.csv \
        --output output/screen/screening.html

Optional:
    --template   Path to Jinja2 HTML template (default: templates/dashboard.html)
    --data-pack  Path to data_pack.md for header stats extraction
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import markdown
from jinja2 import Environment, BaseLoader


# ---------------------------------------------------------------------------
# Markdown → HTML conversion
# ---------------------------------------------------------------------------

def md_to_html(md_text: str) -> str:
    """Convert markdown text to HTML with tables and fenced code support."""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )


# ---------------------------------------------------------------------------
# Rating CSS mapping (English)
# ---------------------------------------------------------------------------

_RATING_MAP = {
    # Factor result
    "PASS": ("highlight", "tag-green"),
    "VETO": ("warn", "tag-red"),
    # Overall rating
    "BUY": ("highlight", "tag-green"),
    "WATCH": ("amber-hl", "tag-amber"),
    "AVOID": ("warn", "tag-red"),
    # Extrapolation credibility
    "HIGH": ("highlight", "tag-green"),
    "MEDIUM": ("amber-hl", "tag-amber"),
    "LOW": ("warn", "tag-red"),
    # Safety margin thickness
    "Thick": ("highlight", "tag-green"),
    "Thin": ("amber-hl", "tag-amber"),
    "Negative": ("warn", "tag-red"),
    # Grades
    "A+": ("highlight", "tag-green"),
    "A": ("highlight", "tag-green"),
    "A-": ("highlight", "tag-green"),
    "B+": ("highlight", "tag-green"),
    "B": ("amber-hl", "tag-amber"),
    "B-": ("amber-hl", "tag-amber"),
    "C+": ("amber-hl", "tag-amber"),
    "C": ("amber-hl", "tag-amber"),
    "D": ("warn", "tag-red"),
    # Value trap risk
    "ABSENT": ("highlight", "tag-green"),
    "PRESENT": ("warn", "tag-red"),
    # Floor price
    "BUYING IS WINNING": ("highlight", "tag-green"),
    "BARGAIN ZONE": ("highlight", "tag-green"),
    "FAIR VALUE": ("amber-hl", "tag-amber"),
    "OVERVALUED": ("warn", "tag-red"),
    # Valuation
    "CHEAP": ("highlight", "tag-green"),
    "FAIR": ("amber-hl", "tag-amber"),
    "EXPENSIVE": ("warn", "tag-red"),
}


def _rating_css(value: str) -> tuple[str, str]:
    """Return (kpi_card_class, badge_class) for a rating value."""
    val_upper = value.upper().strip()
    # Check exact matches first
    for key, classes in _RATING_MAP.items():
        if key == val_upper or key == value.strip():
            return classes
    # Partial match
    for key, classes in _RATING_MAP.items():
        if key in val_upper:
            return classes
    return ("rating-neutral", "")


def _to_card_css(value: str) -> str:
    """Map rating text to card CSS class (highlight/warn/amber-hl)."""
    val = value.strip().upper()

    # Exact-match first (for short tokens like "B", "C", "D")
    exact_positive = {"BUY", "PASS", "HIGH", "A+", "A", "A-", "B+"}
    exact_negative = {"AVOID", "VETO", "D"}
    exact_neutral = {"WATCH", "MEDIUM", "B", "B-", "C+", "C", "MODERATE"}

    if val in exact_positive:
        return "highlight"
    if val in exact_negative:
        return "warn"
    if val in exact_neutral:
        return "amber-hl"

    # Substring match for multi-word values
    positive_sub = ["BUYING IS WINNING", "BARGAIN", "CHEAP", "ABSENT",
                     "STRONG", "THICK", "EXCELLENT", "PASS"]
    negative_sub = ["OVERVALUED", "EXPENSIVE", "PRESENT", "NEGATIVE", "WEAK"]
    neutral_sub = ["FAIR", "THIN", "ADEQUATE"]

    for p in positive_sub:
        if p in val:
            return "highlight"
    for n in negative_sub:
        if n in val:
            return "warn"
    for m in neutral_sub:
        if m in val:
            return "amber-hl"
    return ""


# ---------------------------------------------------------------------------
# Report parser – splits MD into logical sections
# ---------------------------------------------------------------------------

def parse_report(md_text: str) -> dict:
    """Parse the US Quality Yield analysis report MD into structured sections."""
    result = {
        "company_name": "",
        "stock_code": "",
        "generated_date": "",
        "executive_summary": "",
        "dimensions": [],
        "conclusion": "",
        "risk_factors": "",
        "monitoring": "",
    }

    # --- Extract title metadata ---
    # Pattern: # PYPL -- Quality Yield Strategy Analysis Report
    title_match = re.search(
        r"^#\s+(\S+)\s+(?:--|—|–)\s+Quality Yield Strategy Analysis Report",
        md_text, re.MULTILINE,
    )
    if title_match:
        result["stock_code"] = title_match.group(1)
        result["company_name"] = title_match.group(1)

    date_match = re.search(r"\*\*Date\*\*:\s*(\S+)", md_text)
    if date_match:
        result["generated_date"] = date_match.group(1)

    # --- Split by ## headers ---
    sections = re.split(r"(?=^## )", md_text, flags=re.MULTILINE)

    for section in sections:
        header_match = re.match(r"## (.+?)(?:\n|$)", section)
        if not header_match:
            continue
        title = header_match.group(1).strip()
        body = section[header_match.end():]

        if title == "Summary":
            result["executive_summary"] = md_to_html(body)
        elif title == "Investment Conclusion":
            result["conclusion"] = md_to_html(body)
        elif title == "Risk Factors":
            result["risk_factors"] = md_to_html(body)
        elif title == "Monitoring Checklist":
            result["monitoring"] = md_to_html(body)
        elif re.match(r"(Factor\s+\d|1\.5\s+Financial)", title):
            # Factor sections and Financial Trend Overview
            badge = ""
            badge_class = ""

            # Try to extract result badge: **Result: PASS (Grade B+)**
            result_match = re.search(
                r"\*\*Result:\s*(\w+)", body,
            )
            if result_match:
                badge = result_match.group(1)
                _, badge_class = _rating_css(badge)

            # For Factor 4, look for the Factor 4 Decision
            if "Factor 4" in title:
                f4_match = re.search(
                    r"\*?\*?Factor 4 Decision\*?\*?\s*\|\s*\*?\*?(\w+)\*?\*?", body,
                )
                if f4_match:
                    badge = f4_match.group(1)
                    _, badge_class = _rating_css(badge)

            result["dimensions"].append({
                "title": title,
                "content": md_to_html(body),
                "badge": badge,
                "badge_class": badge_class,
            })

    return result


# ---------------------------------------------------------------------------
# KPI cards extraction from Summary table
# ---------------------------------------------------------------------------

def extract_kpi_cards(md_text: str) -> list[dict]:
    """Extract KPI values from the Summary table in the report."""
    cards = []

    def _find_metric(name: str) -> tuple[str, str]:
        """Find metric value and status from Summary table row."""
        pattern = rf"\|\s*{re.escape(name)}\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
        m = re.search(pattern, md_text)
        if m:
            return m.group(1).strip().strip("*"), m.group(2).strip()
        return "", ""

    def _find_metric_2col(name: str) -> str:
        """Find metric value from a 2-column table row."""
        pattern = rf"\|\s*{re.escape(name)}\s*\|\s*(.+?)\s*\|"
        m = re.search(pattern, md_text)
        return m.group(1).strip().strip("*") if m else ""

    # GG
    gg_val, gg_status = _find_metric("GG (Refined Penetration Return Rate)")
    if gg_val:
        cards.append({
            "label": "GG Return Rate",
            "value": gg_val,
            "css_class": _to_card_css(gg_status),
            "sub": gg_status,
        })

    # Safety Margin
    jj_val, jj_status = _find_metric("Safety Margin (JJ)")
    if jj_val:
        cards.append({
            "label": "Safety Margin",
            "value": jj_val,
            "css_class": _to_card_css(jj_status),
            "sub": jj_status,
        })

    # Rating
    rating_val, _ = _find_metric("Rating")
    if rating_val:
        cards.append({
            "label": "Rating",
            "value": rating_val,
            "css_class": _to_card_css(rating_val),
            "sub": "",
        })

    # Position Size
    pos_val, pos_note = _find_metric("Position Size")
    if pos_val:
        cards.append({
            "label": "Position Size",
            "value": pos_val,
            "css_class": "",
            "sub": pos_note,
        })

    # Value Trap Risk
    trap_val, trap_note = _find_metric("Value Trap Risk")
    if trap_val:
        cards.append({
            "label": "Value Trap Risk",
            "value": trap_val,
            "css_class": _to_card_css(trap_val),
            "sub": trap_note,
        })

    # Extrapolation Credibility (from Factor 3 or Factor 4 table)
    cred = _find_metric_2col("Extrapolation Credibility")
    if cred:
        cards.append({
            "label": "Credibility",
            "value": cred,
            "css_class": _to_card_css(cred),
            "sub": "Extrapolation",
        })

    return cards


# ---------------------------------------------------------------------------
# Data pack info extraction
# ---------------------------------------------------------------------------

def extract_data_pack_info(dp_text: str) -> dict:
    """Extract header-level info from US data_pack.md."""
    info = {
        "current_price": "",
        "market_cap": "",
        "exchange": "",
        "industry": "",
        "company_name": "",
    }

    price_m = re.search(r"\*\*Last Price\*\*:\s*([\d,.]+)", dp_text)
    if price_m:
        info["current_price"] = price_m.group(1)

    mcap_m = re.search(r"\*\*Market Cap\*\*:\s*([\d,.]+)", dp_text)
    if mcap_m:
        val = mcap_m.group(1).replace(",", "")
        try:
            v = float(val)
            if v >= 1000:
                info["market_cap"] = f"{v / 1000:.1f}B"
            else:
                info["market_cap"] = f"{v:.0f}M"
        except ValueError:
            info["market_cap"] = mcap_m.group(1)

    # Sector
    sector_m = re.search(r"\*\*GICS Industry\*\*:\s*(.+)", dp_text)
    if not sector_m:
        sector_m = re.search(r"\*\*Sector\*\*:\s*(.+)", dp_text)
    if sector_m:
        info["industry"] = sector_m.group(1).strip()

    # Company name
    name_m = re.search(r"\*\*Full Name\*\*:\s*(.+)", dp_text)
    if not name_m:
        name_m = re.search(r"\*\*Company Name\*\*:\s*(.+)", dp_text)
    if name_m:
        info["company_name"] = name_m.group(1).strip()

    # Exchange (from Country or GICS Sector)
    exchange_m = re.search(r"\*\*GICS Sector\*\*:\s*(.+)", dp_text)
    if exchange_m:
        info["exchange"] = exchange_m.group(1).strip()

    return info


# ---------------------------------------------------------------------------
# Verdict builder
# ---------------------------------------------------------------------------

def build_verdict(md_text: str) -> dict:
    """Build the verdict banner from Rating and Investment Conclusion."""
    # Extract Rating from Summary table
    rating_m = re.search(r"\|\s*Rating\s*\|\s*\*?\*?(\w+)\*?\*?\s*\|", md_text)
    rating = rating_m.group(1).strip() if rating_m else ""

    # Extract first line of Investment Conclusion
    verdict_text = ""
    conclusion_m = re.search(
        r"## Investment Conclusion\s*\n+\*?\*?(.+?)(?:\*?\*?\s*$|\n)",
        md_text, re.MULTILINE,
    )
    if conclusion_m:
        verdict_text = conclusion_m.group(1).strip().strip("*")
    elif rating:
        verdict_text = f"Rating: {rating}"

    # Determine color
    tag_map = {
        "BUY": ("tag-green", "v-green", "BUY"),
        "WATCH": ("tag-amber", "v-amber", "WATCH"),
        "AVOID": ("tag-red", "v-red", "AVOID"),
    }
    tag_class, verdict_class, tag_text = tag_map.get(
        rating.upper(), ("tag-amber", "v-amber", rating.upper() if rating else "N/A")
    )

    return {
        "verdict_class": verdict_class,
        "verdict_tag_class": tag_class,
        "verdict_tag": tag_text,
        "verdict_text": verdict_text,
    }


# ---------------------------------------------------------------------------
# Warnings extraction (from warnings.json)
# ---------------------------------------------------------------------------

_SEVERITY_DOT = {
    "HIGH": "dot-red",
    "MEDIUM": "dot-amber",
    "LOW": "dot-green",
}


def extract_warnings(output_dir: Path) -> list[dict]:
    """Read warnings.json from the output directory and return as template-ready list."""
    warnings_path = output_dir / "warnings.json"
    if not warnings_path.exists():
        return []
    try:
        data = json.loads(warnings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    result = []
    for w in data:
        result.append({
            "message": w.get("message", ""),
            "severity": w.get("severity", "LOW"),
            "category": w.get("category", ""),
            "dot_class": _SEVERITY_DOT.get(w.get("severity", ""), "dot-green"),
        })
    return result


# ---------------------------------------------------------------------------
# Factor summary extraction (progress bars)
# ---------------------------------------------------------------------------

_FACTOR_NAMES = [
    ("Factor 1", "Asset Quality"),
    ("Factor 2", "Coarse Return"),
    ("Factor 3", "Refined Return"),
    ("Factor 4", "Valuation"),
]


def extract_factor_summary(md_text: str) -> list[dict]:
    """Parse factor results from the report into progress-bar-ready dicts."""
    factors = []
    for factor_id, factor_label in _FACTOR_NAMES:
        # Look for "Factor N ... Result: PASS/VETO"
        pattern = rf"##\s*{re.escape(factor_id)}.*?(?:\*\*Result:\s*(\w+))"
        m = re.search(pattern, md_text, re.DOTALL)
        result = m.group(1).upper() if m else ""

        if result == "PASS":
            bar_pct = 100
            bar_color = "var(--green)"
        elif result == "VETO":
            bar_pct = 100
            bar_color = "var(--red)"
        else:
            bar_pct = 0
            bar_color = "var(--bg3)"

        factors.append({
            "label": f"{factor_id}: {factor_label}",
            "result": result or "—",
            "bar_pct": bar_pct,
            "bar_color": bar_color,
        })
    return factors


# ---------------------------------------------------------------------------
# Screening summary rendering
# ---------------------------------------------------------------------------

def render_screening_summary(csv_path: Path, output_path: Path):
    """Render final_candidates.csv as a styled HTML screening summary."""
    project_root = Path(__file__).resolve().parent.parent
    template_path = project_root / "templates" / "screening_summary.html"

    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    template_text = template_path.read_text(encoding="utf-8")
    env = Environment(loader=BaseLoader())
    template = env.from_string(template_text)
    html = template.render(candidates=rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Screening summary generated: {output_path}")
    print(f"  Candidates: {len(rows)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert US Quality Yield analysis.md to HTML dashboard"
    )
    parser.add_argument("--input", default=None, help="Path to analysis.md")
    parser.add_argument("--output", required=True, help="Output HTML path")
    parser.add_argument(
        "--template",
        default=None,
        help="Jinja2 template path (default: templates/dashboard.html)",
    )
    parser.add_argument(
        "--data-pack",
        default=None,
        help="Path to data_pack.md for header stats extraction",
    )
    parser.add_argument(
        "--screening",
        default=None,
        help="Path to final_candidates.csv for screening summary mode",
    )
    args = parser.parse_args()

    # --- Screening summary mode ---
    if args.screening:
        render_screening_summary(Path(args.screening), Path(args.output))
        return

    if not args.input:
        print("Error: --input is required (unless using --screening)", file=sys.stderr)
        sys.exit(1)

    # --- Resolve paths ---
    project_root = Path(__file__).resolve().parent.parent
    template_path = (
        Path(args.template)
        if args.template
        else project_root / "templates" / "dashboard.html"
    )
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not template_path.exists():
        print(f"Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    # --- Read inputs ---
    md_text = input_path.read_text(encoding="utf-8")
    template_text = template_path.read_text(encoding="utf-8")

    # --- Parse report ---
    report = parse_report(md_text)
    kpi_cards = extract_kpi_cards(md_text)
    verdict = build_verdict(md_text)
    factor_bars = extract_factor_summary(md_text)

    # --- Try to get warnings ---
    warnings_list = extract_warnings(input_path.parent)

    # --- Try to get data pack info ---
    dp_info = {
        "current_price": "",
        "market_cap": "",
        "exchange": "",
        "industry": "",
        "company_name": "",
    }
    data_pack_path = (
        Path(args.data_pack) if args.data_pack else input_path.parent / "data_pack.md"
    )
    if data_pack_path.exists():
        dp_text = data_pack_path.read_text(encoding="utf-8")
        dp_info = extract_data_pack_info(dp_text)

    # Use data_pack company name if available, otherwise fall back to ticker
    company_name = dp_info["company_name"] or report["company_name"]

    # --- Render template ---
    env = Environment(loader=BaseLoader())
    template = env.from_string(template_text)
    html = template.render(
        company_name=company_name,
        stock_code=report["stock_code"],
        generated_date=report["generated_date"],
        current_price=dp_info["current_price"],
        market_cap=dp_info["market_cap"],
        exchange=dp_info["exchange"],
        industry=dp_info["industry"],
        kpi_cards=kpi_cards,
        executive_summary=report["executive_summary"],
        dimensions=report["dimensions"],
        conclusion=report["conclusion"],
        risk_factors=report["risk_factors"],
        monitoring=report["monitoring"],
        warnings=warnings_list,
        factor_bars=factor_bars,
        **verdict,
    )

    # --- Write output ---
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML report generated: {output_path}")
    print(f"  Company: {company_name} ({report['stock_code']})")
    print(f"  Sections: {len(report['dimensions'])} factors")
    print(f"  KPI cards: {len(kpi_cards)}")
    print(f"  Has executive summary: {bool(report['executive_summary'])}")
    print(f"  Has conclusion: {bool(report['conclusion'])}")
    print(f"  Has risk factors: {bool(report['risk_factors'])}")
    print(f"  Has monitoring: {bool(report['monitoring'])}")
    print(f"  Warnings: {len(warnings_list)}")
    print(f"  Factor bars: {len(factor_bars)}")


if __name__ == "__main__":
    main()
