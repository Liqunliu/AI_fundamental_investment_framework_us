"""Derived metrics calculation mixin — US Equity version.

Fixes IS_TOT_REV bug from Chinese version (uses SALES_REV_TURN instead).
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd


class DerivedMetricsMixin:
    """Mixin for calculating derived financial metrics."""

    def calculate_growth_rates(self, df: pd.DataFrame, field: str) -> pd.Series:
        """Year-over-year growth rates (%)."""
        if df.empty or field not in df.columns:
            return pd.Series(dtype=float)
        return df[field].astype(float).pct_change() * 100

    def calculate_margins(self) -> pd.DataFrame:
        """Profit margins from income statement data."""
        if "income" not in self._store or self._store["income"].empty:
            return pd.DataFrame()

        inc = self._store["income"]
        out = pd.DataFrame()

        if "date" in inc.columns:
            out["date"] = inc["date"]

        rev_col = "SALES_REV_TURN"  # fixed from IS_TOT_REV
        if rev_col not in inc.columns:
            return out

        if "GROSS_PROFIT" in inc.columns:
            out["gross_margin"] = inc["GROSS_PROFIT"] / inc[rev_col] * 100
        if "IS_OPER_INC" in inc.columns:
            out["operating_margin"] = inc["IS_OPER_INC"] / inc[rev_col] * 100
        if "NET_INCOME" in inc.columns:
            out["net_margin"] = inc["NET_INCOME"] / inc[rev_col] * 100
        if "EBITDA" in inc.columns:
            out["ebitda_margin"] = inc["EBITDA"] / inc[rev_col] * 100

        return out

    def calculate_liquidity_ratios(self) -> pd.DataFrame:
        """Current, quick, and cash ratios from balance sheet."""
        if "balance" not in self._store or self._store["balance"].empty:
            return pd.DataFrame()

        bal = self._store["balance"]
        out = pd.DataFrame()

        if "date" in bal.columns:
            out["date"] = bal["date"]

        if "BS_CUR_ASSET_REPORT" in bal.columns and "BS_CUR_LIAB" in bal.columns:
            out["current_ratio"] = bal["BS_CUR_ASSET_REPORT"] / bal["BS_CUR_LIAB"]

        if all(c in bal.columns for c in ["BS_CUR_ASSET_REPORT", "BS_INVENTORIES", "BS_CUR_LIAB"]):
            out["quick_ratio"] = (
                (bal["BS_CUR_ASSET_REPORT"] - bal["BS_INVENTORIES"]) / bal["BS_CUR_LIAB"]
            )

        if "BS_CASH_NEAR_CASH_ITEM" in bal.columns and "BS_CUR_LIAB" in bal.columns:
            out["cash_ratio"] = bal["BS_CASH_NEAR_CASH_ITEM"] / bal["BS_CUR_LIAB"]

        return out

    def calculate_leverage_ratios(self) -> pd.DataFrame:
        """Debt ratios from balance sheet."""
        if "balance" not in self._store or self._store["balance"].empty:
            return pd.DataFrame()

        bal = self._store["balance"]
        out = pd.DataFrame()

        if "date" in bal.columns:
            out["date"] = bal["date"]

        if "BS_TOT_LIAB2" in bal.columns and "TOT_COMMON_EQY" in bal.columns:
            out["debt_to_equity"] = bal["BS_TOT_LIAB2"] / bal["TOT_COMMON_EQY"]

        if "BS_TOT_LIAB2" in bal.columns and "BS_TOT_ASSET" in bal.columns:
            out["debt_to_assets"] = bal["BS_TOT_LIAB2"] / bal["BS_TOT_ASSET"]

        if "BS_LT_BORROW" in bal.columns and "BS_ST_BORROW" in bal.columns:
            total_debt = bal["BS_LT_BORROW"].fillna(0) + bal["BS_ST_BORROW"].fillna(0)
            out["total_debt"] = total_debt
            if "BS_CASH_NEAR_CASH_ITEM" in bal.columns:
                out["net_debt"] = total_debt - bal["BS_CASH_NEAR_CASH_ITEM"].fillna(0)

        return out

    def calculate_efficiency_ratios(self) -> pd.DataFrame:
        """Asset turnover and related ratios."""
        if "income" not in self._store or "balance" not in self._store:
            return pd.DataFrame()

        inc = self._store["income"]
        bal = self._store["balance"]
        if inc.empty or bal.empty:
            return pd.DataFrame()

        out = pd.DataFrame()

        if "date" in inc.columns:
            out["date"] = inc["date"].values

        rev_col = "SALES_REV_TURN"

        if rev_col in inc.columns and "BS_TOT_ASSET" in bal.columns:
            out["asset_turnover"] = inc[rev_col] / bal["BS_TOT_ASSET"]

        if rev_col in inc.columns and "BS_ACCT_NOTE_RCV" in bal.columns:
            out["receivables_turnover"] = inc[rev_col] / bal["BS_ACCT_NOTE_RCV"]
            out["days_sales_outstanding"] = 365 / out["receivables_turnover"]

        if rev_col in inc.columns and "BS_INVENTORIES" in bal.columns:
            out["inventory_turnover"] = inc[rev_col] / bal["BS_INVENTORIES"]
            out["days_inventory_outstanding"] = 365 / out["inventory_turnover"]

        return out

    def calculate_all_derived_metrics(self) -> dict:
        """Calculate all derived metrics."""
        return {
            "margins": self.calculate_margins(),
            "liquidity": self.calculate_liquidity_ratios(),
            "leverage": self.calculate_leverage_ratios(),
            "efficiency": self.calculate_efficiency_ratios(),
        }
