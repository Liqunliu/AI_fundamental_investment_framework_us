"""Configuration for Cyclical Trough Buying Strategy.

Separate framework that sits alongside Quality Yield. Buys cyclical stocks at
troughs using normalized (mid-cycle) valuations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CyclicalConfig:
    """Thresholds and parameters for cyclical trough analysis."""

    # --- Shared with Quality Yield (imported from config.py at runtime) ---
    # risk_free_rate and threshold_ii are read from DEFAULT_CONFIG

    # --- C1: Survival & Quality gates ---
    min_current_ratio: float = 1.0
    min_interest_coverage: float = 1.5  # at trough
    max_net_debt_mid_ebitda: float = 3.0  # Net Debt / Mid-Cycle EBITDA
    min_cash_runway_months: int = 18  # trough cash runway

    # Cyclicality confirmation
    min_revenue_cv: float = 0.15  # CV(Revenue) >= 0.15
    min_ebitda_cv: float = 0.30  # OR CV(EBITDA) >= 0.30

    # --- C2: Cycle phase scoring weights ---
    weight_company: float = 0.40
    weight_sector: float = 0.35
    weight_macro: float = 0.15
    weight_price: float = 0.10

    # Phase thresholds (composite score boundaries)
    phase_deep_trough: float = 0.80  # >= 0.80 -> Deep Trough
    phase_early_recovery: float = 0.65  # >= 0.65 -> Early Recovery
    phase_mid_cycle: float = 0.40  # >= 0.40 -> Mid-Cycle
    phase_late_cycle: float = 0.20  # >= 0.20 -> Late Cycle
    # < 0.20 -> Peak

    # --- C3: Normalized valuation ---
    normalized_gg_threshold: float = 0.073  # 7.30%
    min_discount_to_midcycle: float = 0.15  # 15%

    # Median window for OCF/CapEx
    ocf_capex_median_years: int = 5
    # Average window for buybacks/dividends/SBC
    shareholder_avg_years: int = 3

    # --- Risk management ---
    max_single_position: float = 0.15  # 15% (vs QY's 25%)
    max_sector: float = 0.35  # 35%
    max_commodity_group: float = 0.30  # 30%
    min_cash: float = 0.20  # 20%
    portfolio_stop_loss: float = -0.25  # -25% from peak

    # Position sizing by phase
    # Phase 1 (Deep Trough): 100%/80%/60% of max allocation
    # Phase 2 (Early Recovery): 70%/50%/35% of max allocation
    phase1_position_tiers: List[float] = field(
        default_factory=lambda: [1.00, 0.80, 0.60]
    )
    phase2_position_tiers: List[float] = field(
        default_factory=lambda: [0.70, 0.50, 0.35]
    )

    # --- Sector indicator tickers (yfinance symbols) ---
    sector_indicators: Dict[str, str] = field(default_factory=lambda: {
        "oil": "CL=F",
        "semis": "^SOX",
        "shipping": "^BDI",  # Baltic Dry Index (may need proxy)
        "copper": "HG=F",
        "industrials": "^GSPI",  # placeholder for ISM PMI
    })

    # Macro indicator tickers
    macro_indicators: Dict[str, str] = field(default_factory=lambda: {
        "yield_10y": "^TNX",
        "yield_2y": "^IRX",  # approximate; use FRED for exact
        "credit_spread": "HYG",  # high-yield bond ETF as proxy
        "pmi": "^GSPI",  # placeholder; fetched from FRED
    })

    # Cyclical sector mapping (Finviz sector -> commodity group)
    cyclical_sectors: Dict[str, str] = field(default_factory=lambda: {
        "Energy": "oil",
        "Basic Materials": "mining",
        "Industrials": "industrials",
        "Technology": "semis",  # filtered to semiconductor sub-industries
    })

    # Cyclical industry keywords for filtering
    cyclical_industries: List[str] = field(default_factory=lambda: [
        "Oil & Gas",
        "Integrated",
        "Exploration",
        "Refining",
        "Midstream",
        "Semiconductor",
        "Steel",
        "Aluminum",
        "Copper",
        "Mining",
        "Shipping",
        "Marine",
        "Chemicals",
        "Industrial Metals",
        "Coal",
        "Uranium",
        "Auto Manufacturers",
        "Auto Parts",
        "Building Materials",
        "Engineering & Construction",
        "Farm & Heavy Construction Machinery",
        "Trucking",
        "Railroads",
        "Airlines",
    ])

    # Screener limits
    screener_limit: int = 40
    screener_top_n: int = 15

    # Task time budgets (seconds)
    max_task_duration: int = 600  # 10 minutes


@dataclass
class CyclicalPortfolioConfig:
    """Portfolio-level settings for the cyclical strategy."""

    portfolio_file: str = "output/cycle/CYCLE_PORTFOLIO.md"
    output_base: str = "output/cycle"

    # Max holdings
    min_positions: int = 3
    max_positions: int = 10

    # Rebalance trigger
    phase_change_rebalance: bool = True


# Singletons
CYCLE_CONFIG = CyclicalConfig()
CYCLE_PORTFOLIO_CONFIG = CyclicalPortfolioConfig()

# Phase labels and actions
PHASE_LABELS = {
    1: ("Deep Trough", "BUY (max position)"),
    2: ("Early Recovery", "BUY (standard)"),
    3: ("Mid-Cycle", "HOLD only"),
    4: ("Late Cycle", "REDUCE"),
    5: ("Peak", "SELL/AVOID"),
}


def classify_phase(score: float) -> int:
    """Map a composite cycle score to a phase number (1-5)."""
    if score >= CYCLE_CONFIG.phase_deep_trough:
        return 1
    if score >= CYCLE_CONFIG.phase_early_recovery:
        return 2
    if score >= CYCLE_CONFIG.phase_mid_cycle:
        return 3
    if score >= CYCLE_CONFIG.phase_late_cycle:
        return 4
    return 5


def phase_label(phase: int) -> str:
    """Return human-readable phase label."""
    return PHASE_LABELS.get(phase, ("Unknown", "N/A"))[0]


def phase_action(phase: int) -> str:
    """Return recommended action for a phase."""
    return PHASE_LABELS.get(phase, ("Unknown", "N/A"))[1]


def get_cycle_output_dir(ticker: str) -> str:
    """Get the cycle-specific output directory for a ticker."""
    import os
    base = os.path.join(
        os.path.dirname(__file__), "..",
        CYCLE_PORTFOLIO_CONFIG.output_base, ticker,
    )
    os.makedirs(base, exist_ok=True)
    return base
