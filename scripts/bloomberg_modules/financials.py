"""Financial data fetching mixin for Bloomberg — US Equity version.

Fetches income statement, balance sheet, and cash flow data.
Cash flow fields are expanded to include capex, dividends paid,
share repurchases, and stock-based compensation.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import pandas as pd

from .constants import (
    INCOME_FIELDS,
    BALANCE_FIELDS,
    CASHFLOW_FIELDS,
    SHAREHOLDER_FIELDS,
)


class FinancialsMixin:
    """Mixin for fetching financial statement data from Bloomberg."""

    def fetch_income_statement(self, security: str, years: int = 5) -> pd.DataFrame:
        """Fetch yearly income statement data."""
        print(f"Fetching income statement for {security}...")
        end = datetime.now()
        start = end - timedelta(days=years * 365)

        try:
            if self._api_mode == "terminal":
                df = self._terminal_historical_request(
                    security, INCOME_FIELDS,
                    start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    periodicity="YEARLY",
                )
            else:
                print("WARNING: HAPI not implemented for historicals", file=sys.stderr)
                df = pd.DataFrame()

            if not df.empty:
                self._store["income"] = df
                print(f"  Retrieved {len(df)} periods")
            else:
                print("  No income statement data returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Income statement fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_balance_sheet(self, security: str, years: int = 5) -> pd.DataFrame:
        """Fetch yearly balance sheet data."""
        print(f"Fetching balance sheet for {security}...")
        end = datetime.now()
        start = end - timedelta(days=years * 365)

        try:
            if self._api_mode == "terminal":
                df = self._terminal_historical_request(
                    security, BALANCE_FIELDS,
                    start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    periodicity="YEARLY",
                )
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["balance"] = df
                print(f"  Retrieved {len(df)} periods")
            else:
                print("  No balance sheet data returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Balance sheet fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_cashflow_statement(self, security: str, years: int = 5) -> pd.DataFrame:
        """Fetch yearly cash flow data (core fields)."""
        print(f"Fetching cash flow statement for {security}...")
        end = datetime.now()
        start = end - timedelta(days=years * 365)

        try:
            if self._api_mode == "terminal":
                df = self._terminal_historical_request(
                    security, CASHFLOW_FIELDS,
                    start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    periodicity="YEARLY",
                )
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["cashflow"] = df
                print(f"  Retrieved {len(df)} periods")
            else:
                print("  No cash flow data returned", file=sys.stderr)
            return df

        except Exception as e:
            print(f"ERROR: Cash flow fetch failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_shareholder_returns(self, security: str, years: int = 5) -> pd.DataFrame:
        """Fetch share repurchases and SBC (separate request to avoid breaking core).

        These fields may not have valid Bloomberg mnemonics; errors are
        handled gracefully and missing columns are filled with None.
        """
        print(f"Fetching shareholder return fields for {security}...")
        end = datetime.now()
        start = end - timedelta(days=years * 365)

        try:
            if self._api_mode == "terminal":
                df = self._terminal_historical_request(
                    security, SHAREHOLDER_FIELDS,
                    start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                    periodicity="YEARLY",
                )
            else:
                df = pd.DataFrame()

            if not df.empty:
                self._store["shareholder"] = df
                # Merge into cashflow store if both exist
                if "cashflow" in self._store and not self._store["cashflow"].empty:
                    cf = self._store["cashflow"]
                    for field in SHAREHOLDER_FIELDS:
                        if field in df.columns:
                            # Align by date
                            if "date" in cf.columns and "date" in df.columns:
                                mapping = dict(zip(df["date"], df[field]))
                                cf[field] = cf["date"].map(mapping)
                            else:
                                # Fallback: align by position
                                vals = df[field].tolist()
                                if len(vals) == len(cf):
                                    cf[field] = vals
                    self._store["cashflow"] = cf
                print(f"  Retrieved shareholder return data ({len(df)} periods)")

                # Report which fields have data
                for f in SHAREHOLDER_FIELDS:
                    if f in df.columns and df[f].notna().any():
                        print(f"    ✓ {f}: has data")
                    else:
                        print(f"    ✗ {f}: no data (field may not exist in Bloomberg)")
            else:
                print("  No shareholder return data (fields may not exist)", file=sys.stderr)
            return df

        except Exception as e:
            print(f"WARNING: Shareholder return fetch failed (non-fatal): {e}", file=sys.stderr)
            return pd.DataFrame()

    def fetch_all_financials(self, security: str, years: int = 5) -> dict:
        """Fetch all financial statements including shareholder returns."""
        return {
            "income": self.fetch_income_statement(security, years),
            "balance": self.fetch_balance_sheet(security, years),
            "cashflow": self.fetch_cashflow_statement(security, years),
            "shareholder": self.fetch_shareholder_returns(security, years),
        }
