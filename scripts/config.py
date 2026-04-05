"""Configuration and utility functions for US Equity Quality Yield Strategy."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional


# --- US Market Defaults ---

@dataclass
class USMarketConfig:
    """US equity market configuration for Quality Yield Strategy."""

    # Risk-free rate (US 10-Year Treasury)
    risk_free_rate: float = 0.043  # 4.3%

    # Threshold II = Rf + 3%
    threshold_premium: float = 0.03

    @property
    def threshold_ii(self) -> float:
        return self.risk_free_rate + self.threshold_premium

    # Dividend tax rate (qualified dividends for US residents)
    dividend_tax_rate: float = 0.15

    # ROE gate (higher for US market)
    min_roe: float = 0.10  # 10%

    # Screening defaults
    min_market_cap_b: float = 1.0  # $1B minimum
    max_pe: float = 30.0
    max_pb: float = 5.0
    min_gross_margin: float = 15.0  # %
    max_debt_equity: float = 2.0

    # Portfolio constraints
    max_single_position: float = 0.25  # 25% max per stock
    max_sector_concentration: float = 0.40  # 40% max per sector
    min_positions: int = 5
    max_positions: int = 15

    # Data units
    currency: str = "USD"
    amount_unit: str = "Millions"
    amount_divider: float = 1e6

    # Benchmark
    benchmark_ticker: str = "SPY"

    # Screener settings
    tier1_limit: int = 50  # Finviz → top 50
    tier2_limit: int = 10  # Deep analysis on top 10

    # Task time budgets (seconds)
    max_task_duration: int = 600  # 10 minutes
    max_tickers_per_collection_batch: int = 5
    max_tickers_per_analysis_batch: int = 2

    # Scheduling
    daily_alert_budget: int = 30  # seconds
    weekly_refresh_budget: int = 300  # 5 minutes
    monthly_screen_budget: int = 1800  # 30 minutes (split into sub-tasks)

    # Alert thresholds
    alert_price_change_pct: float = 5.0  # Alert if price moves > 5%
    alert_gg_proximity_pct: float = 1.0  # Warn if GG within 1 pct of threshold

    # Cache TTLs (seconds)
    cache_ttl_financials: int = 7 * 86400   # 7 days
    cache_ttl_info: int = 7 * 86400         # 7 days
    cache_ttl_prices: int = 86400           # 1 day
    cache_ttl_history: int = 86400          # 1 day

    # Pipeline settings
    pipeline_top_n: int = 10
    pipeline_with_edgar: bool = True
    pipeline_parallel_tickers: int = 1  # Sequential for rate limiting


# Singleton config
DEFAULT_CONFIG = USMarketConfig()


def _load_env_file() -> None:
    """Load .env file from project root if it exists."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    env_path = os.path.normpath(env_path)
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value


def get_bloomberg_credentials() -> dict:
    """Get Bloomberg HAPI credentials from environment or .env file.

    Returns:
        dict with 'client_id' and 'client_secret' keys.

    Raises:
        RuntimeError: If credentials are not configured.
    """
    _load_env_file()
    client_id = os.environ.get("BLOOMBERG_CLIENT_ID", "")
    client_secret = os.environ.get("BLOOMBERG_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Bloomberg HAPI credentials not set.\n"
            "Option 1: Set BLOOMBERG_CLIENT_ID and BLOOMBERG_CLIENT_SECRET in .env\n"
            "Option 2: export BLOOMBERG_CLIENT_ID='...' && export BLOOMBERG_CLIENT_SECRET='...'\n"
            "Option 3: Use --source yfinance instead"
        )
    return {"client_id": client_id, "client_secret": client_secret}


def validate_us_ticker(ticker: str) -> str:
    """Validate and normalize a US stock ticker.

    Args:
        ticker: Ticker string (e.g., 'AAPL', 'aapl', 'AAPL.US').

    Returns:
        Normalized uppercase ticker without suffix (e.g., 'AAPL').

    Raises:
        ValueError: If the ticker format is not recognized.
    """
    ticker = ticker.strip().upper()

    # Remove .US suffix if present
    if ticker.endswith(".US"):
        ticker = ticker[:-3]

    # Validate: 1-5 uppercase letters
    if not re.match(r"^[A-Z]{1,5}$", ticker):
        raise ValueError(
            f"Invalid US ticker format: '{ticker}'. "
            "Expected 1-5 letters (e.g., 'AAPL', 'MSFT', 'GOOGL')."
        )

    return ticker


def get_output_dir(ticker: str) -> str:
    """Get the output directory for a ticker's analysis files.

    Args:
        ticker: Normalized ticker (e.g., 'AAPL').

    Returns:
        Path string like 'output/AAPL/'.
    """
    base = os.path.join(os.path.dirname(__file__), "..", "output", ticker)
    os.makedirs(base, exist_ok=True)
    return base


def get_risk_free_rate() -> float:
    """Get current US 10-Year Treasury rate.

    For now returns the default. Can be enhanced to fetch live rate
    from FRED API or yfinance.
    """
    return DEFAULT_CONFIG.risk_free_rate
