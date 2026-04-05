#!/usr/bin/env python3
"""
SEC EDGAR 10-K/20-F Parser

Extracts 7 footnote sections from an HTML filing using BeautifulSoup.

Sections extracted:
  P2   - Restricted Cash
  P3   - AR Aging / Allowance for Credit Losses
  P4   - Related Party Transactions
  P6   - Commitments & Contingencies (leases, litigation)
  P13  - Non-Recurring Items (restructuring, impairment)
  MDA  - Management's Discussion & Analysis (Item 7)
  SUB  - Subsidiaries (Exhibit 21)

Parsing strategy (tiered fallback per section):
  1. Table of Contents anchors → section jump
  2. Heading tags (<h1>-<h6>) matching patterns
  3. Styled <p><b> paragraphs
  4. Full-text keyword search

Usage:
    python3 scripts/edgar_parser.py --input output/AAPL/AAPL_10K.html --ticker AAPL
    python3 scripts/edgar_parser.py --input output/AAPL/AAPL_10K.htm --ticker AAPL

Output: output/{TICKER}/filing_sections.json

Dependencies: beautifulsoup4, lxml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    print(
        "ERROR: beautifulsoup4 is required. Install with:\n"
        "  pip install beautifulsoup4 lxml",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import get_output_dir  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_SECTION_CHARS = 30_000

# Section definitions: (id, display_name, keyword_patterns, is_note)
SECTION_DEFS: List[Tuple[str, str, List[str], bool]] = [
    (
        "P2",
        "Restricted Cash",
        [r"restricted\s+cash"],
        True,
    ),
    (
        "P3",
        "Accounts Receivable & Credit Losses",
        [r"accounts?\s+receivable", r"allowance\s+for\s+(?:doubtful|credit)", r"credit\s+loss"],
        True,
    ),
    (
        "P4",
        "Related Party Transactions",
        [r"related\s+part(?:y|ies)"],
        True,
    ),
    (
        "P6",
        "Commitments & Contingencies",
        [r"commitments?\s+and\s+contingenc", r"litigation", r"legal\s+proceedings"],
        True,
    ),
    (
        "P13",
        "Non-Recurring Items",
        [r"restructuring", r"impairment", r"goodwill\s+impairment"],
        True,
    ),
    (
        "MDA",
        "Management's Discussion & Analysis",
        [r"management.s\s+discussion", r"item\s+7[^a]", r"item\s*7\.",
         r"item\s+5[^a]", r"operating\s+and\s+financial\s+review",   # 20-F
         r"item\s+2[^0-9a-z].*(?:discussion|analysis)"],             # 10-Q
        False,
    ),
    (
        "SUB",
        "Subsidiaries",
        [r"exhibit\s+21", r"significant\s+subsidiar", r"list\s+of\s+subsidiar"],
        False,
    ),
]


# ===================================================================
# HTML helpers
# ===================================================================

def _get_text(el: Tag) -> str:
    """Get clean text from an element."""
    return el.get_text(separator=" ", strip=True)


def _is_heading(el: Tag) -> bool:
    """Check if element is a heading or heading-like styled element."""
    if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return True
    # Check for bold paragraphs used as headings
    if el.name == "p":
        bold = el.find(["b", "strong"])
        if bold and len(_get_text(bold)) > 5:
            # Check if the bold text IS the paragraph (heading-like)
            para_text = _get_text(el)
            bold_text = _get_text(bold)
            if len(bold_text) / max(len(para_text), 1) > 0.7:
                return True
    return False


def _heading_text(el: Tag) -> str:
    """Get the text of a heading element."""
    if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return _get_text(el)
    bold = el.find(["b", "strong"])
    if bold:
        return _get_text(bold)
    return _get_text(el)


def _table_to_markdown(table: Tag) -> str:
    """Convert an HTML table to markdown format."""
    rows = table.find_all("tr")
    if not rows:
        return ""

    md_rows = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        cell_texts = [_get_text(c).replace("|", "/") for c in cells]
        md_rows.append("| " + " | ".join(cell_texts) + " |")

    if len(md_rows) >= 1:
        # Add separator after first row (header)
        n_cols = md_rows[0].count("|") - 1
        sep = "| " + " | ".join(["---"] * max(n_cols, 1)) + " |"
        md_rows.insert(1, sep)

    return "\n".join(md_rows)


def _extract_section_content(start_el: Tag, max_chars: int = MAX_SECTION_CHARS) -> str:
    """Extract text content starting from an element until next heading of same or higher level.

    Converts tables to markdown. Truncates at max_chars.
    """
    parts = []
    total_chars = 0

    # Determine the heading level to stop at
    stop_levels = set()
    if start_el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(start_el.name[1])
        stop_levels = {f"h{i}" for i in range(1, level + 1)}

    current = start_el.next_sibling
    while current and total_chars < max_chars:
        if isinstance(current, NavigableString):
            text = str(current).strip()
            if text:
                parts.append(text)
                total_chars += len(text)
        elif isinstance(current, Tag):
            # Stop at next heading of same or higher level
            if current.name in stop_levels:
                break
            if _is_heading(current) and stop_levels:
                break

            # Handle tables specially
            if current.name == "table":
                md_table = _table_to_markdown(current)
                parts.append(md_table)
                total_chars += len(md_table)
            else:
                text = _get_text(current)
                if text:
                    parts.append(text)
                    total_chars += len(text)

                # Also check for nested tables
                for nested_table in current.find_all("table"):
                    md_table = _table_to_markdown(nested_table)
                    parts.append(md_table)
                    total_chars += len(md_table)

        current = current.next_sibling

    result = "\n\n".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[... truncated at 30,000 chars ...]"
    return result


# ===================================================================
# Section finding strategies
# ===================================================================

def _find_by_toc(soup: BeautifulSoup, patterns: List[str]) -> Optional[Tag]:
    """Strategy 1: Find section via Table of Contents anchor links."""
    # Look for ToC links that match our patterns
    for link in soup.find_all("a", href=True):
        link_text = _get_text(link)
        for pattern in patterns:
            if re.search(pattern, link_text, re.IGNORECASE):
                href = link["href"]
                if href.startswith("#"):
                    target_id = href[1:]
                    # Find the target element
                    target = soup.find(id=target_id)
                    if target is None:
                        target = soup.find("a", {"name": target_id})
                    if target:
                        return target
    return None


def _find_by_headings(soup: BeautifulSoup, patterns: List[str]) -> Optional[Tag]:
    """Strategy 2: Find section via heading tags matching patterns."""
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = _get_text(heading)
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return heading
    return None


def _find_by_styled_paragraphs(soup: BeautifulSoup, patterns: List[str]) -> Optional[Tag]:
    """Strategy 3: Find section via bold-styled paragraphs."""
    for p in soup.find_all("p"):
        bold = p.find(["b", "strong"])
        if not bold:
            continue
        text = _get_text(bold)
        if len(text) < 5:
            continue
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return p
    return None


def _find_by_text_search(soup: BeautifulSoup, patterns: List[str]) -> Optional[Tag]:
    """Strategy 4: Full-text keyword search — find the first significant match."""
    body = soup.find("body") or soup
    # Search through block-level elements
    for el in body.find_all(["p", "div", "span", "td"], limit=5000):
        text = _get_text(el)
        if len(text) < 20:
            continue
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Walk up to find a meaningful parent block
                parent = el
                while parent.parent and parent.parent.name not in ("body", "html", "[document]"):
                    if parent.parent.name in ("div", "section", "article") and len(_get_text(parent.parent)) > len(text):
                        parent = parent.parent
                        break
                    parent = parent.parent
                return el
    return None


def _extract_section(
    soup: BeautifulSoup,
    section_id: str,
    section_name: str,
    patterns: List[str],
    is_note: bool,
) -> Dict[str, Any]:
    """Extract a section using tiered fallback strategies.

    Returns dict with: id, name, found, strategy, content, char_count
    """
    strategies = [
        ("toc_anchor", _find_by_toc),
        ("heading_tag", _find_by_headings),
        ("styled_paragraph", _find_by_styled_paragraphs),
        ("text_search", _find_by_text_search),
    ]

    for strategy_name, strategy_fn in strategies:
        start_el = strategy_fn(soup, patterns)
        if start_el:
            content = _extract_section_content(start_el)
            if content and len(content.strip()) > 50:
                return {
                    "id": section_id,
                    "name": section_name,
                    "found": True,
                    "strategy": strategy_name,
                    "content": content.strip(),
                    "char_count": len(content.strip()),
                }

    return {
        "id": section_id,
        "name": section_name,
        "found": False,
        "strategy": None,
        "content": "",
        "char_count": 0,
    }


# ===================================================================
# Main parser
# ===================================================================

def parse_filing(html_path: Path) -> Dict[str, Any]:
    """Parse an SEC filing HTML and extract all target sections.

    Args:
        html_path: Path to the downloaded 10-K/20-F HTML file.

    Returns:
        Dict with keys: filing_path, parsed_at, sections (list of section dicts),
        summary (found_count, total_count, sections_found list)
    """
    print(f"  Parsing: {html_path}")
    print(f"  File size: {html_path.stat().st_size:,} bytes")

    html_content = html_path.read_bytes()

    # Try lxml parser first (faster), fall back to html.parser
    try:
        soup = BeautifulSoup(html_content, "lxml")
    except Exception:
        soup = BeautifulSoup(html_content, "html.parser")

    sections = []
    found_ids = []

    for section_id, section_name, patterns, is_note in SECTION_DEFS:
        print(f"  [{section_id}] Searching for: {section_name}...", end=" ")
        result = _extract_section(soup, section_id, section_name, patterns, is_note)
        sections.append(result)

        if result["found"]:
            found_ids.append(section_id)
            print(f"FOUND ({result['strategy']}, {result['char_count']:,} chars)")
        else:
            print("NOT FOUND")

    return {
        "filing_path": str(html_path),
        "parsed_at": __import__("datetime").datetime.now().isoformat(),
        "sections": sections,
        "summary": {
            "found_count": len(found_ids),
            "total_count": len(SECTION_DEFS),
            "sections_found": found_ids,
            "sections_missing": [s[0] for s in SECTION_DEFS if s[0] not in found_ids],
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="SEC EDGAR 10-K/20-F Parser"
    )
    parser.add_argument("--input", required=True, help="Path to the downloaded HTML filing")
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument("--output", default=None, help="Output JSON path (default: output/{TICKER}/filing_sections.json)")
    args = parser.parse_args()

    html_path = Path(args.input)
    ticker = args.ticker.upper()

    if not html_path.exists():
        print(f"ERROR: Filing not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path(get_output_dir(ticker))
        output_path = output_dir / "filing_sections.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"SEC EDGAR Parser — {ticker}")
    print(f"{'=' * 40}")

    try:
        result = parse_filing(html_path)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        summary = result["summary"]
        print(f"\nResults: {summary['found_count']}/{summary['total_count']} sections found")
        print(f"  Found: {', '.join(summary['sections_found']) or 'none'}")
        print(f"  Missing: {', '.join(summary['sections_missing']) or 'none'}")
        print(f"\nOutput: {output_path}")

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
