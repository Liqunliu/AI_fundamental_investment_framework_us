"""Configuration for Cigar Butt Deep Value Strategy.

Separate framework that sits alongside Quality Yield and Cyclical.  Buys stocks
trading below net asset value (NAV) using a 3-pillar framework:

  Pillar 1 — Net Asset Cushion  (T0 / T1 / T2)
  Pillar 2 — Operating Maintenance (FCF + Asset Burn Rate)
  Pillar 3 — Realization Logic  (Type A / B / C)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CigarConfig:
    """Thresholds and parameters for cigar butt deep value analysis."""

    # --- T-Level NAV entry discounts ---
    # Price must be < T_NAV * (1 - discount) to qualify
    t0_entry_discount: float = 0.15  # Price < T0_NAV * 0.85
    t1_entry_discount: float = 0.20  # Price < T1_NAV * 0.80
    t2_entry_discount: float = 0.30  # Price < T2_NAV * 0.70

    # --- Asset Burn Rate (ABR) thresholds ---
    # ABR = (Cash_t - Cash_t-1) / Cash_t-1, negative = cash burning
    # PASS / WARNING / VETO levels per tier
    t0_abr_pass: float = 0.00   # T0: ABR >= 0% => PASS
    t0_abr_veto: float = -0.05  # T0: ABR < -5% => VETO
    t1_abr_pass: float = 0.05   # T1: ABR >= 5% => PASS
    t1_abr_veto: float = -0.05  # T1: ABR < -5% => VETO
    t2_abr_pass: float = 0.10   # T2: ABR >= 10% => PASS
    t2_abr_veto: float = 0.00   # T2: ABR < 0% => VETO

    # --- P/B zones ---
    pb_deep_value: float = 0.50   # P/B <= 0.50 => deep value
    pb_value: float = 0.70        # P/B <= 0.70 => value
    pb_screen_max: float = 0.60   # Screener filter: P/B < 0.60

    # --- Position sizing by tier ---
    t0_max_position: float = 0.10  # 10%
    t1_max_position: float = 0.08  # 8%
    t2_max_position: float = 0.05  # 5%
    c1_max_position: float = 0.08  # 5-8% (use 8% cap)
    c2_max_position: float = 0.05  # 2-5% (C2-) or 5-8% (C2+)

    # --- Scaled entry tranches ---
    tranche_1_pct: float = 0.40  # 40% at buy threshold
    tranche_2_pct: float = 0.30  # 30% at further 10% decline
    tranche_3_pct: float = 0.30  # 30% at another 10% decline or catalyst

    # --- Portfolio construction ---
    min_holdings: int = 12
    max_holdings: int = 20
    t0_t1_portfolio_pct: float = 0.55   # 55% in T0/T1
    t2_portfolio_pct: float = 0.20       # 20% in T2
    event_portfolio_pct: float = 0.15    # 15% in event-driven
    cash_reserve_pct: float = 0.10       # 10% cash reserve
    max_sector_pct: float = 0.25         # 25% sector cap

    # --- Exit rules ---
    hard_stop_loss: float = -0.25  # 25% decline from entry => exit

    # Profit-taking (sell 50% at level 1, rest at level 2)
    t0_profit_take_1: float = 0.95  # T0_NAV * 0.95
    t0_profit_take_2: float = 1.05  # T0_NAV * 1.05
    t1_profit_take_1: float = 0.90  # T1_NAV * 0.90
    t1_profit_take_2: float = 1.00  # T1_NAV * 1.00
    t2_profit_take_1: float = 0.80  # T2_NAV * 0.80
    t2_profit_take_2: float = 0.95  # T2_NAV * 0.95

    # Time-based exit: 5 years without thesis realization
    max_holding_years: int = 5

    # --- Type A: High-Dividend Below-Book ---
    type_a_min_div_yield: float = 0.05    # 5%
    type_a_max_pb: float = 0.50            # P/B <= 0.50
    type_a_min_div_years: int = 5          # 5 consecutive years
    type_a_max_payout_ratio: float = 0.80  # Payout < 80%
    type_a_min_fcf_coverage: float = 0.80  # FCF / Dividends > 0.80

    # --- Type B: Holding Company Discount ---
    type_b_min_discount: float = 0.30     # 30% discount to SOTP
    type_b_min_ownership: float = 0.10    # 10% minimum ownership
    type_b_profit_take_discount: float = 0.20  # Take profit at 20% discount
    type_b_exit_discount: float = 0.15    # Full exit at 15% discount

    # --- Type C1: Event-Driven ---
    c1a_min_upside: float = 0.50          # 50% upside minimum
    c1a_min_probability: str = "B"         # >= B grade (50%+)
    c1b_min_net_cash_pct: float = 0.10    # Net cash > 10% of mktcap
    c1b_max_pb: float = 0.60              # P/B < 0.60
    c1c_min_arb_spread: float = 0.05      # 5% arbitrage spread

    # --- Type C2: Regulatory/Policy Resolution ---
    c2_min_score: int = 6                  # C2 score >= 6 to qualify
    c2_plus_threshold: int = 8             # C2+ score >= 8

    # --- Fact Check ---
    # Goodwill thresholds
    goodwill_veto: float = 0.30    # Goodwill/Assets > 30% => VETO
    goodwill_warn: float = 0.15    # Goodwill/Assets 15-30% => WARNING

    # Other veto thresholds
    restricted_cash_veto: float = 0.20    # Restricted cash > 20% => VETO
    off_bs_liab_veto: float = 0.15        # Off-BS liab > 15% mktcap => VETO
    pension_deficit_veto: float = 0.10    # Pension deficit > 10% mktcap => VETO
    other_payables_veto: float = 0.30     # Other payables anomaly > 30%
    related_party_veto: float = 0.30      # Related-party > 30% revenue
    revenue_conc_veto: float = 0.60       # Top-5 customers > 60%
    q4_spike_veto: float = 0.40           # Q4 > 40% annual revenue
    subsidy_veto: float = 0.50            # Subsidies > 50% for 3 years

    # --- Inventory discount coefficients by sector ---
    inventory_discounts: Dict[str, float] = field(default_factory=lambda: {
        "consumer": 0.80,
        "retail": 0.80,
        "manufacturing": 0.70,
        "industrial": 0.70,
        "electronics": 0.50,
        "technology": 0.50,
        "pharmaceutical": 0.40,
        "default": 0.65,
    })

    # --- Screener settings ---
    screener_limit: int = 50
    screener_top_n: int = 20
    screener_min_market_cap_m: float = 300  # $300M minimum
    screener_min_daily_value_m: float = 5    # $5M daily trading value

    # --- Value sectors for Finviz screening ---
    value_sectors: List[str] = field(default_factory=lambda: [
        "Financial",
        "Energy",
        "Basic Materials",
        "Industrials",
        "Real Estate",
        "Utilities",
        "Consumer Defensive",
    ])

    # Dividend sustainability scorecard weights (Type A)
    div_scorecard_items: List[str] = field(default_factory=lambda: [
        "payout_ratio_safety",     # Payout < 80%: 2 pts
        "fcf_coverage",            # FCF/Div > 0.8: 2 pts
        "consecutive_years",       # >= 5 years: 1 pt
        "div_growth_trend",        # Growing dividends: 1 pt
        "earnings_stability",      # Stable earnings: 1 pt
        "debt_manageable",         # D/E < 1.5: 1 pt
        "industry_norm",           # In-line with sector: 1 pt
        "cash_reserves",           # Cash > 1yr dividends: 1 pt
    ])

    # Task time budgets (seconds)
    max_task_duration: int = 600  # 10 minutes


@dataclass
class CigarPortfolioConfig:
    """Portfolio-level settings for the cigar butt strategy."""

    portfolio_file: str = "output/cigar/CIGAR_PORTFOLIO.md"
    output_base: str = "output/cigar"

    # Max holdings
    min_positions: int = 12
    max_positions: int = 20

    # Monitoring frequency
    nav_update_frequency: str = "quarterly"


# Singletons
CIGAR_CONFIG = CigarConfig()
CIGAR_PORTFOLIO_CONFIG = CigarPortfolioConfig()

# Tier labels and descriptions
TIER_LABELS = {
    "T0": ("Net Cash Exceeds Market Cap", "Cash - Total Liabilities > Market Cap"),
    "T1": ("Cash Exceeds Interest-Bearing Debt", "Cash - IBD > Market Cap"),
    "T2": ("Current Assets Exceed Liabilities", "Adjusted Current Assets - Total Liabilities > Market Cap"),
    "NONE": ("Below All Tiers", "Does not qualify for any NAV tier"),
}

# Sub-type labels
SUBTYPE_LABELS = {
    "A": "High-Dividend Below-Book",
    "B": "Holding Company Discount",
    "C1a": "Asset Disposition / Spin-Off",
    "C1b": "Share Buybacks",
    "C1c": "Liquidation / Going-Private",
    "C2": "Regulatory / Policy Resolution",
}

# Fact Check rating descriptions
FACT_CHECK_RATINGS = {
    "A": "All items pass, no warnings",
    "B": "Core items pass, 1-2 warning items",
    "B+": "Base B + Bonus >= 2 points",
    "C": "3+ warning items or 1 item approaching veto",
    "D": "Any automatic-veto item triggered (irreversible)",
}


def classify_tier(
    price: float,
    t0_nav: float,
    t1_nav: float,
    t2_nav: float,
) -> str:
    """Classify stock into NAV tier based on current price.

    Returns 'T0', 'T1', 'T2', or 'NONE'.
    """
    cfg = CIGAR_CONFIG
    if t0_nav > 0 and price < t0_nav * (1 - cfg.t0_entry_discount):
        return "T0"
    if t1_nav > 0 and price < t1_nav * (1 - cfg.t1_entry_discount):
        return "T1"
    if t2_nav > 0 and price < t2_nav * (1 - cfg.t2_entry_discount):
        return "T2"
    return "NONE"


def abr_verdict(abr: float, tier: str) -> str:
    """Return ABR verdict for a given tier: 'PASS', 'WARNING', or 'VETO'.

    Args:
        abr: Asset burn rate as a decimal (e.g., -0.03 = -3%).
        tier: 'T0', 'T1', or 'T2'.
    """
    cfg = CIGAR_CONFIG
    if tier == "T0":
        if abr >= cfg.t0_abr_pass:
            return "PASS"
        if abr >= cfg.t0_abr_veto:
            return "WARNING"
        return "VETO"
    if tier == "T1":
        if abr >= cfg.t1_abr_pass:
            return "PASS"
        if abr >= cfg.t1_abr_veto:
            return "WARNING"
        return "VETO"
    # T2 or default
    if abr >= cfg.t2_abr_pass:
        return "PASS"
    if abr >= cfg.t2_abr_veto:
        return "WARNING"
    return "VETO"


def max_position_for_tier(tier: str) -> float:
    """Return maximum position size (decimal) for a given tier."""
    cfg = CIGAR_CONFIG
    return {
        "T0": cfg.t0_max_position,
        "T1": cfg.t1_max_position,
        "T2": cfg.t2_max_position,
    }.get(tier, cfg.t2_max_position)


def get_inventory_discount(sector: str) -> float:
    """Get inventory haircut coefficient for a sector."""
    cfg = CIGAR_CONFIG
    sector_lower = sector.lower()
    for key, val in cfg.inventory_discounts.items():
        if key in sector_lower:
            return val
    return cfg.inventory_discounts["default"]


def get_cigar_output_dir(ticker: str) -> str:
    """Get the cigar-specific output directory for a ticker."""
    import os
    base = os.path.join(
        os.path.dirname(__file__), "..",
        CIGAR_PORTFOLIO_CONFIG.output_base, ticker,
    )
    os.makedirs(base, exist_ok=True)
    return base
