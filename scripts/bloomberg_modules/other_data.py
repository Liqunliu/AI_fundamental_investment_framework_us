"""Market data, dividends, and company info fetching — US Equity version."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import pandas as pd

from .constants import MARKET_FIELDS, DIVIDEND_FIELDS, COMPANY_INFO_FIELDS


class OtherDataMixin:
    """Mixin for fetching market data, dividends, and company information."""

    def fetch_market_data(self, security: str) -> pd.DataFrame:
        """Fetch current market data (price, market cap, ratios)."""
        print(f"Fetching market data for {security}...")

        try:
            if self._api_mode == "terminal":
                df = self._terminal_reference_request([security], MARKET_FIELDS)
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["market"] = df
                print("  Retrieved market data")
            else:
                print("  No market data returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Market data fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_company_info(self, security: str) -> pd.DataFrame:
        """Fetch company info including reporting currency."""
        print(f"Fetching company info for {security}...")

        try:
            if self._api_mode == "terminal":
                df = self._terminal_reference_request([security], COMPANY_INFO_FIELDS)
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["company_info"] = df
                # Extract reporting currency
                row = df.iloc[0]
                fund_ccy = row.get("EQY_FUND_CRNCY")
                sec_ccy = row.get("CRNCY")
                self._reporting_currency = str(fund_ccy or sec_ccy or "USD").upper()
                print(f"  Company: {row.get('NAME', 'N/A')}")
                print(f"  Reporting currency: {self._reporting_currency}")
            else:
                print("  No company info returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Company info fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_dividends(self, security: str, years: int = 5) -> pd.DataFrame:
        """Fetch historical dividend data."""
        print(f"Fetching dividend data for {security}...")

        end = datetime.now()
        start = end - timedelta(days=years * 365)

        try:
            if self._api_mode == "terminal":
                df = self._terminal_historical_request(
                    security, ["DVD_HIST_ALL"],
                    start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    periodicity="MONTHLY",
                )
                # Also get current dividend metrics
                current_df = self._terminal_reference_request([security], DIVIDEND_FIELDS)
                if not current_df.empty:
                    self._store["dividend_current"] = current_df
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["dividends"] = df
                print(f"  Retrieved {len(df)} dividend records")
            else:
                print("  No dividend data returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Dividend fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_daily_prices(self, security: str, years: int = 5) -> pd.DataFrame:
        """Fetch daily OHLCV price history."""
        print(f"Fetching daily prices for {security}...")

        end = datetime.now()
        start = end - timedelta(days=years * 365)
        price_fields = ["PX_OPEN", "PX_HIGH", "PX_LOW", "PX_LAST", "PX_VOLUME"]

        try:
            if self._api_mode == "terminal":
                df = self._terminal_historical_request(
                    security, price_fields,
                    start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    periodicity="DAILY",
                )
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["daily_prices"] = df
                print(f"  Retrieved {len(df)} days of price data")
            else:
                print("  No price data returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Daily prices fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()
