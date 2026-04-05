#!/usr/bin/env python3
"""Cigar Butt NAV Calculator — T0/T1/T2 NAV + ABR + Dividend Sustainability.

Computes three levels of net asset value per share and classifies entry
tier from a Bloomberg/yFinance data pack:

    T0_NAV = (Cash - Total Liabilities) / Shares
    T1_NAV = (Cash - Interest-Bearing Debt) / Shares
    T2_NAV = (Cash*1.0 + AR*0.85 + Inv*discount + Other*0.5
              - Total Liabilities) / Shares

Single-ticker:
    python3 scripts/calculate_cigar_nav.py \\
        --input output/VLO/data_pack.md --code VLO

Batch:
    python3 scripts/calculate_cigar_nav.py \\
        --batch output/cigar/screen/cigar_candidates.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Local imports (reuse QY parsers)
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import DEFAULT_CONFIG  # noqa: E402
from cigar_config import (  # noqa: E402
    CIGAR_CONFIG,
    CIGAR_PORTFOLIO_CONFIG,
    TIER_LABELS,
    classify_tier,
    abr_verdict,
    max_position_for_tier,
    get_inventory_discount,
    get_cigar_output_dir,
)
from calculate_qy_gg import (  # noqa: E402
    _parse_numeric,
    _parse_markdown_table,
    _extract_market_data,
    _extract_sections,
    _columns_are_descending,
    _METRIC_LABEL_MAP,
)

logger = logging.getLogger("cigar_nav")

# ---------------------------------------------------------------------------
# Extended label map for balance sheet items needed by cigar strategy
# ---------------------------------------------------------------------------
_CIGAR_BALANCE_MAP: Dict[str, str] = {
    # Cash & equivalents
    "Cash & Equivalents": "cash",
    "Cash and Equivalents": "cash",
    "Cash & Short-Term Investments": "cash",
    "Cash and Short-Term Investments": "cash",
    "Total Cash": "cash",
    # Current assets
    "Total Current Assets": "current_assets",
    "Current Assets": "current_assets",
    # Accounts receivable
    "Accounts Receivable": "accounts_receivable",
    "Net Receivables": "accounts_receivable",
    "Trade Receivables": "accounts_receivable",
    # Inventory
    "Inventory": "inventory",
    "Inventories": "inventory",
    # Other current assets
    "Other Current Assets": "other_current_assets",
    # Goodwill
    "Goodwill": "goodwill",
    # Total assets
    "Total Assets": "total_assets",
    # Total liabilities
    "Total Liabilities": "total_liabilities",
    "Total Liabilities & Equity": "total_liab_equity",
    # Interest-bearing debt
    "Total Debt": "total_debt",
    "Total Borrowings": "total_debt",
    "Long-Term Debt": "long_term_debt",
    "Long Term Debt": "long_term_debt",
    "Short-Term Debt": "short_term_debt",
    "Short Term Debt": "short_term_debt",
    "Current Debt": "short_term_debt",
    "Current Portion of Long-Term Debt": "current_lt_debt",
    # Equity
    "Shareholders Equity": "equity",
    "Shareholders' Equity": "equity",
    "Stockholders' Equity": "equity",
    "Total Equity": "equity",
    # Shares outstanding
    "Shares Outstanding": "shares_outstanding",
    "Basic Shares Outstanding": "shares_outstanding",
    "Diluted Shares Outstanding": "diluted_shares",
    # Intangibles
    "Intangible Assets": "intangibles",
    "Other Intangible Assets": "intangibles",
}

# Extended market data label map (covers yfinance data pack labels not in QY)
_CIGAR_MARKET_LABEL_MAP: Dict[str, str] = {
    "Market Cap": "market_cap",
    "Market Capitalization": "market_cap",
    "Last Price": "price",
    "Close Price": "price",
    "Current Price": "price",
    "Price": "price",
    "P/E Ratio": "pe_ratio",
    "PE Ratio": "pe_ratio",
    "PE (TTM)": "pe_ratio",
    "P/B Ratio": "pb_ratio",
    "PB Ratio": "pb_ratio",
    "PB": "pb_ratio",
    "Dividend Yield": "dividend_yield",
    "Shares Outstanding": "shares_outstanding",
}


def _extract_extended_market_data(content: str) -> Dict[str, float]:
    """Extract market data from data pack, scanning all bullet-point sections.

    Extends the QY _extract_market_data to handle yfinance-specific labels
    (e.g., 'Current Price', 'PB') and scan both '## Market Data' and
    '## Company Overview' sections.
    """
    import re

    result: Dict[str, float] = {}
    # Scan all lines for bullet-point key-value pairs
    for line in content.splitlines():
        m = re.match(r"-\s*\*\*(.+?)\*\*\s*:\s*(.+)", line)
        if not m:
            continue
        label, raw_val = m.group(1).strip(), m.group(2).strip()
        canonical = _CIGAR_MARKET_LABEL_MAP.get(label)
        if canonical is None:
            continue
        num = _parse_numeric(raw_val)
        if num is not None:
            result[canonical] = num

    return result


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class CigarNAVResult:
    """Container for cigar NAV calculation outputs."""

    stock_code: str
    price: float
    market_cap: float
    shares_outstanding: float

    # Balance sheet inputs (in millions USD)
    cash: float
    current_assets: float
    accounts_receivable: float
    inventory: float
    other_current_assets: float
    goodwill: float
    total_assets: float
    total_liabilities: float
    interest_bearing_debt: float  # Short-term + Long-term debt
    equity: float

    # NAV per share
    t0_nav_per_share: float  # (Cash - Total Liab) / Shares
    t1_nav_per_share: float  # (Cash - IBD) / Shares
    t2_nav_per_share: float  # (Adjusted Current Assets - Total Liab) / Shares

    # NAV totals (millions)
    t0_nav_total: float
    t1_nav_total: float
    t2_nav_total: float

    # Entry thresholds (price must be below these)
    t0_entry_price: float
    t1_entry_price: float
    t2_entry_price: float

    # Classification
    tier: str  # T0, T1, T2, or NONE
    tier_description: str

    # Asset burn rate
    abr: float  # decimal
    abr_verdict: str  # PASS / WARNING / VETO
    prev_year_cash: float

    # Valuation
    pb_ratio: float
    pb_zone: str  # "deep_value", "value", "neutral"
    nav_discount_pct: float  # how far below best qualifying NAV

    # Profit-taking levels
    profit_take_1: float
    profit_take_2: float

    # Position sizing
    max_position: float

    # Quality flags
    goodwill_ratio: float
    goodwill_flag: str  # OK / WARNING / VETO
    ibd_to_assets: float

    # Dividend sustainability (Type A, 0-10 score)
    div_yield: float
    div_sustainability_score: int
    div_sustainability_details: List[str]

    # FCF metrics
    fcf: float
    fcf_yield: float
    ocf_positive_years: int

    # Manual verification flags
    manual_flags: List[str]

    # Sector (for inventory discount)
    sector: str
    inventory_discount: float


# ---------------------------------------------------------------------------
# Balance sheet extraction
# ---------------------------------------------------------------------------

def _extract_balance_sheet(
    sections: Dict[str, Dict[str, Any]],
) -> Dict[str, float]:
    """Extract latest balance sheet values using the cigar label map."""
    bs = sections.get("balance", {})
    rows = bs.get("rows", [])
    if not rows:
        return {}

    descending = _columns_are_descending(rows)
    result: Dict[str, float] = {}

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

        label = label_cell.strip()
        # Try cigar map first, then QY map
        canonical = _CIGAR_BALANCE_MAP.get(label) or _METRIC_LABEL_MAP.get(label)
        if canonical is None:
            continue

        # Get the latest value (last col if ascending, first col if descending)
        numeric_vals = [
            (k, v) for k, v in row.items()
            if k != first_header and isinstance(v, (int, float))
        ]
        if not numeric_vals:
            continue

        if descending:
            latest = numeric_vals[0][1]  # first data col = most recent
        else:
            latest = numeric_vals[-1][1]  # last data col = most recent

        result[canonical] = float(latest)

    return result


def _extract_multi_year_values(
    sections: Dict[str, Dict[str, Any]],
    section_key: str,
    metric_key: str,
) -> List[float]:
    """Extract all year values for a metric in chronological order."""
    sec = sections.get(section_key, {})
    rows = sec.get("rows", [])
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

        label = label_cell.strip()
        canonical = (_CIGAR_BALANCE_MAP.get(label)
                     or _METRIC_LABEL_MAP.get(label))
        if canonical == metric_key:
            values = [
                float(v) for k, v in row.items()
                if k != first_header and isinstance(v, (int, float))
            ]
            if descending:
                values.reverse()
            return values

    return []


# ---------------------------------------------------------------------------
# Dividend sustainability scorecard (Type A)
# ---------------------------------------------------------------------------

def _compute_div_sustainability(
    div_yield: float,
    payout_ratio: float,
    fcf: float,
    dividends_paid: float,
    consecutive_div_years: int,
    div_growth: bool,
    earnings_stable: bool,
    debt_equity: float,
    cash: float,
) -> tuple[int, List[str]]:
    """Compute dividend sustainability score (0-10) for Type A candidates."""
    score = 0
    details: List[str] = []

    # 1. Payout ratio safety (2 pts)
    if 0 < payout_ratio < CIGAR_CONFIG.type_a_max_payout_ratio:
        score += 2
        details.append(f"Payout ratio {payout_ratio:.0%} < 80%: +2 pts")
    elif payout_ratio > 0:
        details.append(f"Payout ratio {payout_ratio:.0%} >= 80%: +0 pts")
    else:
        details.append("Payout ratio unavailable: +0 pts")

    # 2. FCF coverage (2 pts)
    if dividends_paid > 0 and fcf > 0:
        coverage = fcf / dividends_paid
        if coverage >= CIGAR_CONFIG.type_a_min_fcf_coverage:
            score += 2
            details.append(f"FCF/Div coverage {coverage:.2f}x >= 0.80: +2 pts")
        else:
            details.append(f"FCF/Div coverage {coverage:.2f}x < 0.80: +0 pts")
    else:
        details.append("FCF coverage unavailable: +0 pts")

    # 3. Consecutive dividend years (1 pt)
    if consecutive_div_years >= CIGAR_CONFIG.type_a_min_div_years:
        score += 1
        details.append(f"Consecutive div years {consecutive_div_years} >= 5: +1 pt")
    else:
        details.append(f"Consecutive div years {consecutive_div_years} < 5: +0 pts")

    # 4. Dividend growth trend (1 pt)
    if div_growth:
        score += 1
        details.append("Dividend growth trend: +1 pt")
    else:
        details.append("No dividend growth trend: +0 pts")

    # 5. Earnings stability (1 pt)
    if earnings_stable:
        score += 1
        details.append("Earnings stability: +1 pt")
    else:
        details.append("Earnings not stable: +0 pts")

    # 6. Debt manageable (1 pt)
    if 0 <= debt_equity < 1.5:
        score += 1
        details.append(f"D/E {debt_equity:.2f} < 1.5: +1 pt")
    else:
        details.append(f"D/E {debt_equity:.2f} >= 1.5 or unavailable: +0 pts")

    # 7. Industry norm (1 pt) — simplified: if div yield > 3% in value sector
    if div_yield >= 0.03:
        score += 1
        details.append(f"Div yield {div_yield:.1%} >= 3% (sector norm): +1 pt")
    else:
        details.append(f"Div yield {div_yield:.1%} < 3%: +0 pts")

    # 8. Cash reserves > 1 year dividends (1 pt)
    if dividends_paid > 0 and cash > abs(dividends_paid):
        score += 1
        details.append(f"Cash ${cash:,.0f}M > 1yr dividends ${abs(dividends_paid):,.0f}M: +1 pt")
    else:
        details.append("Cash reserves insufficient or unavailable: +0 pts")

    return score, details


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def calculate_cigar_nav(
    input_file: Path,
    stock_code: str,
    sector: str = "",
) -> CigarNAVResult:
    """Calculate T0/T1/T2 NAV from a data-pack markdown file.

    Args:
        input_file: Path to data_pack.md.
        stock_code: Ticker symbol.
        sector: Sector for inventory discount lookup.

    Returns:
        CigarNAVResult with all calculation outputs.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Data pack not found: {input_file}")

    content = input_file.read_text(encoding="utf-8")

    # Parse data pack (use extended extractor for yfinance compatibility)
    market_data = _extract_extended_market_data(content)
    # Fallback to QY extractor for Bloomberg format
    if not market_data.get("price"):
        turtle_md = _extract_market_data(content)
        for k, v in turtle_md.items():
            if k not in market_data or market_data[k] == 0.0:
                market_data[k] = v
    sections = _extract_sections(content)

    # Market data
    price = market_data.get("price", 0.0)
    market_cap = market_data.get("market_cap", 0.0)
    div_yield = market_data.get("dividend_yield", 0.0)
    if div_yield > 1:
        div_yield = div_yield / 100.0  # convert from percentage

    shares = market_data.get("shares_outstanding", 0.0)
    if shares <= 0 and market_cap > 0 and price > 0:
        shares = market_cap / price  # derive from market cap / price

    if market_cap <= 0:
        raise ValueError(f"Market cap not found or zero in {input_file}")

    # Extract balance sheet
    bs = _extract_balance_sheet(sections)

    cash = bs.get("cash", 0.0)
    current_assets = bs.get("current_assets", 0.0)
    accounts_receivable = bs.get("accounts_receivable", 0.0)
    inventory = bs.get("inventory", 0.0)
    other_current_assets = bs.get("other_current_assets", 0.0)
    goodwill = bs.get("goodwill", 0.0)
    total_assets = bs.get("total_assets", 0.0)
    total_liabilities = bs.get("total_liabilities", 0.0)
    long_term_debt = bs.get("long_term_debt", 0.0)
    short_term_debt = bs.get("short_term_debt", 0.0)
    total_debt = bs.get("total_debt", 0.0)
    equity = bs.get("equity", 0.0)

    # Interest-bearing debt = total_debt if available, else sum components
    ibd = total_debt if total_debt > 0 else (long_term_debt + short_term_debt)

    # Inventory discount
    inv_discount = get_inventory_discount(sector) if sector else 0.65

    # --- T0 NAV: (Cash - Total Liabilities) / Shares ---
    t0_nav_total = cash - total_liabilities
    t0_nav_per_share = t0_nav_total / shares if shares > 0 else 0.0

    # --- T1 NAV: (Cash - IBD) / Shares ---
    t1_nav_total = cash - ibd
    t1_nav_per_share = t1_nav_total / shares if shares > 0 else 0.0

    # --- T2 NAV: (Cash*1.0 + AR*0.85 + Inv*discount + OtherCA*0.5
    #              - Total Liabilities) / Shares ---
    t2_nav_total = (
        cash * 1.0
        + accounts_receivable * 0.85
        + inventory * inv_discount
        + other_current_assets * 0.50
        - total_liabilities
    )
    t2_nav_per_share = t2_nav_total / shares if shares > 0 else 0.0

    # Entry thresholds
    cfg = CIGAR_CONFIG
    t0_entry = t0_nav_per_share * (1 - cfg.t0_entry_discount)
    t1_entry = t1_nav_per_share * (1 - cfg.t1_entry_discount)
    t2_entry = t2_nav_per_share * (1 - cfg.t2_entry_discount)

    # Tier classification
    tier = classify_tier(price, t0_nav_per_share, t1_nav_per_share, t2_nav_per_share)
    tier_desc = TIER_LABELS.get(tier, ("Unknown", ""))[0]

    # Asset burn rate (YoY cash change)
    cash_series = _extract_multi_year_values(sections, "balance", "cash")
    prev_year_cash = 0.0
    abr_val = 0.0
    if len(cash_series) >= 2:
        prev_year_cash = cash_series[-2]
        if prev_year_cash > 0:
            abr_val = (cash - prev_year_cash) / prev_year_cash

    abr_v = abr_verdict(abr_val, tier) if tier != "NONE" else "N/A"

    # P/B ratio
    pb = 0.0
    if equity > 0 and shares > 0:
        bvps = equity / shares
        pb = price / bvps if bvps > 0 else 0.0
    pb_from_market = market_data.get("pb_ratio", 0.0)
    if pb <= 0 and pb_from_market > 0:
        pb = pb_from_market

    pb_zone = "neutral"
    if pb > 0:
        if pb <= cfg.pb_deep_value:
            pb_zone = "deep_value"
        elif pb <= cfg.pb_value:
            pb_zone = "value"

    # NAV discount
    nav_discount = 0.0
    best_nav = 0.0
    if tier == "T0" and t0_nav_per_share > 0:
        best_nav = t0_nav_per_share
    elif tier == "T1" and t1_nav_per_share > 0:
        best_nav = t1_nav_per_share
    elif tier == "T2" and t2_nav_per_share > 0:
        best_nav = t2_nav_per_share
    if best_nav > 0 and price > 0:
        nav_discount = (best_nav - price) / best_nav

    # Profit-taking levels
    if tier == "T0":
        pt1 = t0_nav_per_share * cfg.t0_profit_take_1
        pt2 = t0_nav_per_share * cfg.t0_profit_take_2
    elif tier == "T1":
        pt1 = t1_nav_per_share * cfg.t1_profit_take_1
        pt2 = t1_nav_per_share * cfg.t1_profit_take_2
    else:
        pt1 = t2_nav_per_share * cfg.t2_profit_take_1
        pt2 = t2_nav_per_share * cfg.t2_profit_take_2

    max_pos = max_position_for_tier(tier)

    # Goodwill ratio
    gw_ratio = goodwill / total_assets if total_assets > 0 else 0.0
    gw_flag = "OK"
    if gw_ratio >= cfg.goodwill_veto:
        gw_flag = "VETO"
    elif gw_ratio >= cfg.goodwill_warn:
        gw_flag = "WARNING"

    ibd_to_assets = ibd / total_assets if total_assets > 0 else 0.0

    # --- Cash flow metrics ---
    cf_rows = sections.get("cashflow", {}).get("rows", [])

    # Extract OCF series
    ocf_series = _extract_multi_year_values(sections, "cashflow", "ocf")
    ocf_positive_years = sum(1 for v in ocf_series if v > 0)

    # FCF
    fcf_series = _extract_multi_year_values(sections, "cashflow", "fcf")
    fcf = fcf_series[-1] if fcf_series else 0.0
    fcf_yield = (fcf / market_cap) if market_cap > 0 else 0.0

    # Dividends paid
    div_series = _extract_multi_year_values(sections, "cashflow", "dividends")
    dividends_paid = abs(div_series[-1]) if div_series else 0.0
    consecutive_div_years = 0
    for v in reversed(div_series):
        if abs(v) > 0:
            consecutive_div_years += 1
        else:
            break

    # Net income for payout ratio
    ni_series = _extract_multi_year_values(sections, "income", "net_income")
    net_income = ni_series[-1] if ni_series else 0.0
    payout_ratio = dividends_paid / net_income if net_income > 0 else 0.0

    # Dividend growth check
    div_growth = False
    if len(div_series) >= 3:
        recent = [abs(v) for v in div_series[-3:]]
        div_growth = all(recent[i] >= recent[i - 1] for i in range(1, len(recent)))

    # Earnings stability
    earnings_stable = False
    if len(ni_series) >= 3:
        earnings_stable = all(v > 0 for v in ni_series[-3:])

    # Debt/equity
    debt_equity = ibd / equity if equity > 0 else 999.0

    # Dividend sustainability scorecard
    div_score, div_details = _compute_div_sustainability(
        div_yield=div_yield,
        payout_ratio=payout_ratio,
        fcf=fcf,
        dividends_paid=dividends_paid,
        consecutive_div_years=consecutive_div_years,
        div_growth=div_growth,
        earnings_stable=earnings_stable,
        debt_equity=debt_equity,
        cash=cash,
    )

    # Manual verification flags
    manual_flags = [
        "[MANUAL] Restricted cash ratio — requires 10-K footnote review",
        "[MANUAL] Pledged assets — requires 10-K footnote review",
        "[MANUAL] AR aging analysis — requires 10-K/10-Q footnote",
        "[MANUAL] Off-balance-sheet liabilities — requires footnote review",
        "[MANUAL] Related-party transactions — requires DEF 14A / 10-K",
        "[MANUAL] Revenue concentration — requires 10-K segment data",
        "[MANUAL] Audit opinion — requires 10-K auditor report",
        "[MANUAL] Management integrity — requires proxy statement review",
        "[MANUAL] Subsidiary holdings value — requires ownership research",
        "[MANUAL] Activist/institutional presence — requires 13F/13D filings",
    ]

    return CigarNAVResult(
        stock_code=stock_code,
        price=price,
        market_cap=market_cap,
        shares_outstanding=shares,
        cash=cash,
        current_assets=current_assets,
        accounts_receivable=accounts_receivable,
        inventory=inventory,
        other_current_assets=other_current_assets,
        goodwill=goodwill,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        interest_bearing_debt=ibd,
        equity=equity,
        t0_nav_per_share=t0_nav_per_share,
        t1_nav_per_share=t1_nav_per_share,
        t2_nav_per_share=t2_nav_per_share,
        t0_nav_total=t0_nav_total,
        t1_nav_total=t1_nav_total,
        t2_nav_total=t2_nav_total,
        t0_entry_price=t0_entry,
        t1_entry_price=t1_entry,
        t2_entry_price=t2_entry,
        tier=tier,
        tier_description=tier_desc,
        abr=abr_val,
        abr_verdict=abr_v,
        prev_year_cash=prev_year_cash,
        pb_ratio=pb,
        pb_zone=pb_zone,
        nav_discount_pct=nav_discount,
        profit_take_1=pt1,
        profit_take_2=pt2,
        max_position=max_pos,
        goodwill_ratio=gw_ratio,
        goodwill_flag=gw_flag,
        ibd_to_assets=ibd_to_assets,
        div_yield=div_yield,
        div_sustainability_score=div_score,
        div_sustainability_details=div_details,
        fcf=fcf,
        fcf_yield=fcf_yield,
        ocf_positive_years=ocf_positive_years,
        manual_flags=manual_flags,
        sector=sector,
        inventory_discount=inv_discount,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def _fmt(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def format_report(r: CigarNAVResult) -> str:
    """Render cigar NAV markdown report."""
    L: List[str] = []

    L.append(f"# {r.stock_code} -- Cigar Butt NAV Analysis")
    L.append("")
    L.append(f"**Calculated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    L.append(f"**Sector**: {r.sector or 'Not specified'}")
    L.append("")
    L.append("---")
    L.append("")

    # Executive Summary
    L.append("## Executive Summary")
    L.append("")
    L.append(f"| Metric | Value |")
    L.append(f"|--------|------:|")
    L.append(f"| Price | ${_fmt(r.price)} |")
    L.append(f"| Market Cap | ${_fmt(r.market_cap)}M |")
    L.append(f"| P/B Ratio | {_fmt(r.pb_ratio)} ({r.pb_zone}) |")
    L.append(f"| NAV Tier | **{r.tier}** — {r.tier_description} |")
    L.append(f"| NAV Discount | {_fmt(r.nav_discount_pct * 100)}% |")
    L.append(f"| ABR | {_fmt(r.abr * 100)}% ({r.abr_verdict}) |")
    L.append(f"| Max Position | {_fmt(r.max_position * 100)}% |")
    L.append(f"| Div Yield | {_fmt(r.div_yield * 100)}% |")
    L.append(f"| FCF Yield | {_fmt(r.fcf_yield * 100)}% |")
    L.append(f"| Goodwill/Assets | {_fmt(r.goodwill_ratio * 100)}% ({r.goodwill_flag}) |")
    L.append("")

    # NAV Calculation
    L.append("## NAV Calculation (Pillar 1: Net Asset Cushion)")
    L.append("")
    L.append("### Balance Sheet Inputs (millions USD)")
    L.append("")
    L.append("| Item | Value |")
    L.append("|------|------:|")
    L.append(f"| Cash & Equivalents | ${_fmt(r.cash)} |")
    L.append(f"| Accounts Receivable | ${_fmt(r.accounts_receivable)} |")
    L.append(f"| Inventory | ${_fmt(r.inventory)} |")
    L.append(f"| Other Current Assets | ${_fmt(r.other_current_assets)} |")
    L.append(f"| Total Current Assets | ${_fmt(r.current_assets)} |")
    L.append(f"| Goodwill | ${_fmt(r.goodwill)} |")
    L.append(f"| Total Assets | ${_fmt(r.total_assets)} |")
    L.append(f"| Interest-Bearing Debt | ${_fmt(r.interest_bearing_debt)} |")
    L.append(f"| Total Liabilities | ${_fmt(r.total_liabilities)} |")
    L.append(f"| Shareholders' Equity | ${_fmt(r.equity)} |")
    L.append(f"| Shares Outstanding | {_fmt(r.shares_outstanding)}M |")
    L.append("")

    # T0/T1/T2 Formulas
    L.append("### T-Level NAV Formulas")
    L.append("")
    L.append("```")
    L.append(f"T0_NAV = (Cash - Total Liabilities) / Shares")
    L.append(f"       = ({_fmt(r.cash)} - {_fmt(r.total_liabilities)}) / {_fmt(r.shares_outstanding)}")
    L.append(f"       = ${_fmt(r.t0_nav_per_share)} per share  (Total: ${_fmt(r.t0_nav_total)}M)")
    L.append("")
    L.append(f"T1_NAV = (Cash - IBD) / Shares")
    L.append(f"       = ({_fmt(r.cash)} - {_fmt(r.interest_bearing_debt)}) / {_fmt(r.shares_outstanding)}")
    L.append(f"       = ${_fmt(r.t1_nav_per_share)} per share  (Total: ${_fmt(r.t1_nav_total)}M)")
    L.append("")
    L.append(f"T2_NAV = (Cash*1.0 + AR*0.85 + Inv*{r.inventory_discount:.2f} + OtherCA*0.50 - TotalLiab) / Shares")
    L.append(f"       = ({_fmt(r.cash)}*1.0 + {_fmt(r.accounts_receivable)}*0.85 + "
             f"{_fmt(r.inventory)}*{r.inventory_discount:.2f} + {_fmt(r.other_current_assets)}*0.50 "
             f"- {_fmt(r.total_liabilities)}) / {_fmt(r.shares_outstanding)}")
    L.append(f"       = ${_fmt(r.t2_nav_per_share)} per share  (Total: ${_fmt(r.t2_nav_total)}M)")
    L.append("```")
    L.append("")

    # Entry / Exit Levels
    L.append("### Entry & Exit Price Levels")
    L.append("")
    L.append("| Level | NAV/Share | Entry Price | Current Price | Qualifies? |")
    L.append("|-------|----------:|------------:|--------------:|:----------:|")
    t0_q = "YES" if r.tier == "T0" else "NO"
    t1_q = "YES" if r.tier in ("T0", "T1") else "NO"
    t2_q = "YES" if r.tier != "NONE" else "NO"
    L.append(f"| T0 (85%) | ${_fmt(r.t0_nav_per_share)} | ${_fmt(r.t0_entry_price)} | ${_fmt(r.price)} | {t0_q} |")
    L.append(f"| T1 (80%) | ${_fmt(r.t1_nav_per_share)} | ${_fmt(r.t1_entry_price)} | ${_fmt(r.price)} | {t1_q} |")
    L.append(f"| T2 (70%) | ${_fmt(r.t2_nav_per_share)} | ${_fmt(r.t2_entry_price)} | ${_fmt(r.price)} | {t2_q} |")
    L.append("")

    if r.tier != "NONE":
        L.append("### Profit-Taking Levels")
        L.append("")
        L.append(f"| Action | Price |")
        L.append(f"|--------|------:|")
        L.append(f"| Sell 50% | ${_fmt(r.profit_take_1)} |")
        L.append(f"| Sell remaining | ${_fmt(r.profit_take_2)} |")
        L.append(f"| Hard stop-loss | ${_fmt(r.price * (1 + CIGAR_CONFIG.hard_stop_loss))} (25% decline) |")
        L.append("")

    # Pillar 2: Operating Maintenance
    L.append("## Pillar 2: Operating Maintenance")
    L.append("")
    L.append("| Check | Value | Status |")
    L.append("|-------|------:|:------:|")
    fcf_status = "PASS" if r.fcf > 0 else "WARNING"
    L.append(f"| Latest FCF > 0 | ${_fmt(r.fcf)}M | {fcf_status} |")
    L.append(f"| ABR meets tier threshold | {_fmt(r.abr * 100)}% | {r.abr_verdict} |")
    ocf_status = "PASS" if r.ocf_positive_years >= 3 else "WARNING"
    L.append(f"| 3+ years positive OCF | {r.ocf_positive_years} years | {ocf_status} |")
    L.append(f"| FCF Yield | {_fmt(r.fcf_yield * 100)}% | — |")
    L.append("")

    # Dividend Sustainability (Type A)
    L.append("## Dividend Sustainability Scorecard (Type A)")
    L.append("")
    L.append(f"**Score**: {r.div_sustainability_score}/10")
    type_a_qual = (r.div_yield >= CIGAR_CONFIG.type_a_min_div_yield
                   and r.pb_ratio > 0
                   and r.pb_ratio <= CIGAR_CONFIG.type_a_max_pb)
    L.append(f"**Type A Candidate**: {'YES' if type_a_qual else 'NO'} "
             f"(Div Yield {_fmt(r.div_yield * 100)}% {'>=5%' if r.div_yield >= 0.05 else '<5%'}, "
             f"P/B {_fmt(r.pb_ratio)} {'<=0.50' if r.pb_ratio <= 0.50 else '>0.50'})")
    L.append("")
    for detail in r.div_sustainability_details:
        L.append(f"- {detail}")
    L.append("")

    # Quality Flags
    L.append("## Quality Flags (Automated Fact Check Items)")
    L.append("")
    L.append("| Item | Value | Status |")
    L.append("|------|------:|:------:|")
    L.append(f"| #3 Goodwill/Assets | {_fmt(r.goodwill_ratio * 100)}% | {r.goodwill_flag} |")
    L.append(f"| IBD/Assets | {_fmt(r.ibd_to_assets * 100)}% | {'OK' if r.ibd_to_assets < 0.50 else 'WARNING'} |")
    L.append("")

    # Manual Verification
    L.append("## Manual Verification Required")
    L.append("")
    for flag in r.manual_flags:
        L.append(f"- {flag}")
    L.append("")

    L.append("---")
    L.append("")
    L.append("*Generated by Cigar Butt Deep Value Strategy — NAV Calculator*")

    return "\n".join(L)


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def _print_summary(r: CigarNAVResult) -> None:
    w = 70
    print(f"\n{'=' * w}")
    print("Cigar Butt NAV Calculator — Deep Value Strategy")
    print(f"{'=' * w}")
    print(f"  Ticker:          {r.stock_code}")
    print(f"  Price:           ${_fmt(r.price)}")
    print(f"  Market Cap:      ${_fmt(r.market_cap)}M")
    print(f"  P/B Ratio:       {_fmt(r.pb_ratio)} ({r.pb_zone})")
    print(f"{'=' * w}")
    print(f"\n  T0 NAV/Share:    ${r.t0_nav_per_share:>10.2f}  (Entry < ${r.t0_entry_price:.2f})")
    print(f"  T1 NAV/Share:    ${r.t1_nav_per_share:>10.2f}  (Entry < ${r.t1_entry_price:.2f})")
    print(f"  T2 NAV/Share:    ${r.t2_nav_per_share:>10.2f}  (Entry < ${r.t2_entry_price:.2f})")
    print(f"\n  NAV Tier:        {r.tier} — {r.tier_description}")
    print(f"  NAV Discount:    {r.nav_discount_pct:>8.1%}")
    print(f"  ABR:             {r.abr:>+8.1%} ({r.abr_verdict})")
    print(f"  Max Position:    {r.max_position:>8.0%}")
    print(f"  Goodwill/Assets: {r.goodwill_ratio:>8.1%} ({r.goodwill_flag})")
    print(f"  Div Yield:       {r.div_yield:>8.1%}")
    print(f"  Div Score:       {r.div_sustainability_score}/10")
    print()


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def run_batch(csv_path: Path, sector: str = "") -> List[Dict[str, Any]]:
    """Run NAV calculation for every ticker in csv_path."""
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

    print(f"\nBatch NAV calculation: {len(tickers)} tickers from {csv_path}\n")

    for ticker in tickers:
        data_pack = project_root / "output" / ticker / "data_pack.md"
        if not data_pack.exists():
            data_pack = project_root / "output" / "cigar" / ticker / "data_pack.md"
        if not data_pack.exists():
            logger.warning("  [SKIP] %s -- data_pack.md not found", ticker)
            failures += 1
            results.append({"ticker": ticker, "status": "SKIP", "reason": "no data pack"})
            continue

        try:
            r = calculate_cigar_nav(data_pack, ticker, sector=sector)

            out_dir = Path(get_cigar_output_dir(ticker))
            report_path = out_dir / "cigar_nav.md"
            report_path.write_text(format_report(r), encoding="utf-8")

            print(f"  [{r.tier:>4s}] {ticker:>6s}  T0=${r.t0_nav_per_share:8.2f}  "
                  f"T1=${r.t1_nav_per_share:8.2f}  T2=${r.t2_nav_per_share:8.2f}  "
                  f"P/B={r.pb_ratio:.2f}  ABR={r.abr:+.1%}  -> {report_path}")

            successes += 1
            results.append({
                "ticker": ticker,
                "status": r.tier,
                "t0_nav": round(r.t0_nav_per_share, 2),
                "t1_nav": round(r.t1_nav_per_share, 2),
                "t2_nav": round(r.t2_nav_per_share, 2),
                "price": round(r.price, 2),
                "pb": round(r.pb_ratio, 2),
                "nav_discount": round(r.nav_discount_pct * 100, 1),
                "abr": round(r.abr * 100, 1),
                "div_yield": round(r.div_yield * 100, 1),
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
        summary_csv = csv_path.parent / "cigar_nav_results.csv"
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
        description="Cigar Butt NAV Calculator (Deep Value Strategy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--input", type=Path, help="Path to data_pack.md")
    parser.add_argument("--code", help="Stock ticker (e.g. VLO)")
    parser.add_argument("--batch", type=Path, help="CSV with tickers for batch")
    parser.add_argument("--sector", default="", help="Sector for inventory discount")
    parser.add_argument("--output", type=Path, help="Output file path")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.batch:
        run_batch(args.batch, sector=args.sector)
        return

    if not args.input or not args.code:
        parser.error("Single-ticker mode requires --input and --code.")

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    result = calculate_cigar_nav(
        input_file=args.input,
        stock_code=args.code,
        sector=args.sector,
    )

    _print_summary(result)

    report = format_report(result)
    if args.output:
        output_file = args.output
    else:
        out_dir = Path(get_cigar_output_dir(args.code))
        output_file = out_dir / "cigar_nav.md"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding="utf-8")
    print(f"  Report saved to: {output_file}")


if __name__ == "__main__":
    main()
