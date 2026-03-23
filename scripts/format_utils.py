"""Markdown output formatting utilities for US Equity Turtle Strategy.

All financial amounts are in millions USD.
"""

from __future__ import annotations

from typing import List, Optional


def format_number(value, divider: float = 1e6, decimals: int = 2,
                  prefix: str = "") -> str:
    """Format a number: divide by divider, then comma-separate with decimals.

    Args:
        value: Raw number (e.g., 96886000000 from API).
        divider: Divisor (default 1e6 to convert to millions).
        decimals: Decimal places (default 2).
        prefix: Optional prefix (e.g., '$').

    Returns:
        Formatted string, e.g., '$96,886.00'.
        Returns '—' for None/NaN values.
    """
    if value is None:
        return "—"
    try:
        num = float(value) / divider
    except (TypeError, ValueError):
        return "—"
    # Check for NaN
    if num != num:
        return "—"
    return f"{prefix}{num:,.{decimals}f}"


def format_usd(value, divider: float = 1e6, decimals: int = 2) -> str:
    """Format a number as USD in millions.

    Args:
        value: Raw number from API.
        divider: Divisor (default 1e6).
        decimals: Decimal places.

    Returns:
        Formatted string like '$96,886.00M'.
    """
    if value is None:
        return "—"
    try:
        num = float(value) / divider
    except (TypeError, ValueError):
        return "—"
    if num != num:
        return "—"
    return f"${num:,.{decimals}f}M"


def format_pct(value, decimals: int = 2) -> str:
    """Format a number as percentage.

    Args:
        value: Number (e.g., 0.1234 or 12.34).
        decimals: Decimal places.

    Returns:
        Formatted string like '12.34%'.
    """
    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    if num != num:
        return "—"
    # If value looks like a ratio (< 1 and > -1), convert to percentage
    if -1 < num < 1 and num != 0:
        num *= 100
    return f"{num:.{decimals}f}%"


def format_table(headers: List[str], rows: List[List[str]],
                 alignments: Optional[List[str]] = None) -> str:
    """Generate a markdown table string.

    Args:
        headers: Column header strings.
        rows: List of rows, each a list of cell strings.
        alignments: Per-column alignment ('l', 'r', 'c'). Defaults to left.

    Returns:
        Markdown table string.
    """
    if not headers:
        return ""

    n_cols = len(headers)
    if alignments is None:
        alignments = ["l"] * n_cols

    sep_parts = []
    for a in alignments:
        if a == "r":
            sep_parts.append("---:")
        elif a == "c":
            sep_parts.append(":---:")
        else:
            sep_parts.append("---")

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(sep_parts) + " |")
    for row in rows:
        padded = list(row) + [""] * (n_cols - len(row))
        lines.append("| " + " | ".join(
            str(c) if c is not None else "—" for c in padded[:n_cols]
        ) + " |")

    return "\n".join(lines)


def format_header(level: int, text: str) -> str:
    """Generate a markdown header.

    Args:
        level: Header level (1-6).
        text: Header text.

    Returns:
        Markdown header string, e.g., '## Section Title'.
    """
    level = max(1, min(6, level))
    return "#" * level + " " + text
