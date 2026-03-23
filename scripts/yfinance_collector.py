#!/usr/bin/env python3
"""Turtle Investment Framework (US Equity) - yFinance Data Collector.

Collects financial data from Yahoo Finance and outputs a structured
data_pack.md file for the US Equity Turtle Investment Strategy.

All monetary values are in millions USD unless otherwise noted.

Usage:
    python3 scripts/yfinance_collector.py --ticker AAPL
    python3 scripts/yfinance_collector.py --ticker AAPL --output output/AAPL/data_pack.md
    python3 scripts/yfinance_collector.py --ticker MSFT --years 5
"""

from __future__ import annotations

import argparse
import os
import ssl
import sys
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# SSL workaround: needed in some corporate / dev environments where
# internal CAs are not trusted by Python's default cert bundle.
# ---------------------------------------------------------------------------
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["PYTHONHTTPSVERIFY"] = "0"

try:
    from curl_cffi import requests as curl_requests

    _orig_curl_request = curl_requests.Session.request

    def _patched_request(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        return _orig_curl_request(self, *args, **kwargs)

    curl_requests.Session.request = _patched_request
except Exception:
    pass

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance is not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Local imports (from scripts/ package)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from config import validate_us_ticker, get_output_dir, DEFAULT_CONFIG  # noqa: E402
from format_utils import (  # noqa: E402
    format_number,
    format_usd,
    format_pct,
    format_table,
    format_header,
)
from datetime import datetime  # noqa: E402


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class YFinanceCollector:
    """Collect financial data from Yahoo Finance for the US Equity Turtle Framework."""

    def __init__(self, ticker_symbol: str, years: int = 5):
        """
        Args:
            ticker_symbol: US stock ticker (e.g. 'AAPL', 'MSFT').
            years: Number of years of historical data to collect.
        """
        self.symbol = validate_us_ticker(ticker_symbol)
        self.years = years
        self.ticker = yf.Ticker(self.symbol)

        # Lazy-loaded data caches
        self._info: dict | None = None
        self._income: pd.DataFrame | None = None
        self._balance: pd.DataFrame | None = None
        self._cashflow: pd.DataFrame | None = None
        self._history: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------

    def _get_info(self) -> dict:
        """Return ticker.info dict (cached)."""
        if self._info is None:
            try:
                self._info = self.ticker.info or {}
            except Exception as exc:
                print(f"WARNING: Could not fetch info for {self.symbol}: {exc}", file=sys.stderr)
                self._info = {}
        return self._info

    def _get_financials(self) -> None:
        """Fetch income statement, balance sheet and cash-flow statement."""
        print(f"Fetching financial statements for {self.symbol} ...")

        for attr, label in [
            ("financials", "Income Statement"),
            ("balance_sheet", "Balance Sheet"),
            ("cashflow", "Cash Flow"),
        ]:
            try:
                df = getattr(self.ticker, attr)
                setattr(self, f"_{attr.replace('balance_sheet', 'balance').replace('financials', 'income')}", df)
                shape = df.shape if df is not None else "N/A"
                print(f"  {label}: {shape}")
            except Exception as exc:
                print(f"  {label} failed: {exc}", file=sys.stderr)

        # Ensure DataFrames are never None for downstream code
        if self._income is None:
            self._income = pd.DataFrame()
        if self._balance is None:
            self._balance = pd.DataFrame()
        if self._cashflow is None:
            self._cashflow = pd.DataFrame()

    def _get_history(self) -> None:
        """Fetch historical OHLCV price data."""
        print(f"Fetching price history (10 years weekly) ...")
        try:
            self._history = self.ticker.history(period="10y", interval="1wk")
            if self._history is not None:
                print(f"  History: {len(self._history)} weekly bars")
            else:
                self._history = pd.DataFrame()
        except Exception as exc:
            print(f"  History failed: {exc}", file=sys.stderr)
            self._history = pd.DataFrame()

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_get(d: dict, key: str, default="—"):
        """Safely retrieve a value from *d*, returning *default* for None/NaN."""
        val = d.get(key)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
        return val

    @staticmethod
    def _fmt(val, divider: float = 1e6, decimals: int = 2) -> str:
        """Format a raw number into millions with commas."""
        return format_number(val, divider, decimals)

    @staticmethod
    def _fmt_usd(val, divider: float = 1e6, decimals: int = 2) -> str:
        """Format a raw number as USD millions (e.g. $1,234.56M)."""
        return format_usd(val, divider, decimals)

    @staticmethod
    def _fmt_pct(val) -> str:
        """Format as percentage."""
        return format_pct(val)

    def _fmt_row(self, label: str, df: pd.DataFrame, field_names: list[str]) -> list[str] | None:
        """Extract a labelled row from a financial statement DataFrame.

        yfinance returns statements with dates as columns and field names as
        the index.  We search *field_names* in order and return the first hit.
        """
        if df is None or df.empty:
            return None
        for name in field_names:
            if name in df.index:
                values = df.loc[name]
                return [label] + [self._fmt(v) for v in values]
        return None

    def _fmt_row_eps(self, label: str, df: pd.DataFrame, field_names: list[str]) -> list[str] | None:
        """Like _fmt_row but formats as plain number (no division by 1M)."""
        if df is None or df.empty:
            return None
        for name in field_names:
            if name in df.index:
                values = df.loc[name]
                formatted = []
                for v in values:
                    try:
                        formatted.append(f"{float(v):.2f}")
                    except (TypeError, ValueError):
                        formatted.append("—")
                return [label] + formatted
        return None

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def assemble_data_pack(self) -> str:
        """Assemble the full data pack and return as a single markdown string."""
        info = self._get_info()
        self._get_financials()
        self._get_history()

        sections: list[str] = []

        # Title / header
        company_name = self._safe_get(info, "longName", self.symbol)
        sections.append(format_header(1, f"Data Pack: {company_name} ({self.symbol})"))
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append(f"Data source: Yahoo Finance (yfinance)")
        sections.append(f"Data window: {self.years} years")
        sections.append(f"Currency: {DEFAULT_CONFIG.currency}")
        sections.append(f"Amount unit: {DEFAULT_CONFIG.amount_unit} {DEFAULT_CONFIG.currency}")
        sections.append("")

        # Build each section
        sections.append(self._section_01_company_overview(info))
        sections.append(self._section_02_market_data(info))
        sections.append(self._section_03_income_statement())
        sections.append(self._section_04_balance_sheet())
        sections.append(self._section_05_cash_flow())
        sections.append(self._section_06_dividend_history(info))
        sections.append(self._section_placeholder(
            "7. Governance & Management",
            "To be filled by Agent WebSearch (executive team, board composition, insider ownership)."))
        sections.append(self._section_placeholder(
            "8. Industry & Competition",
            "To be filled by Agent WebSearch (market share, competitive landscape, TAM)."))
        sections.append(self._section_placeholder(
            "9. Subsidiaries & Segments",
            "To be filled by Agent WebSearch (business segments, geographic breakdown)."))
        sections.append(self._section_10_historical_prices())
        sections.append(self._section_11_financial_ratios(info))
        sections.append(self._section_12_risk_warnings())
        sections.append(self._section_13_risk_free_rate())
        sections.append(self._section_14_share_buybacks())
        sections.append(self._section_15_derived_metrics(info))

        return "\n\n".join(s for s in sections if s)

    # ---- §1 Company Overview ----

    def _section_01_company_overview(self, info: dict) -> str:
        lines = [format_header(2, "1. Company Overview")]

        mcap = self._safe_get(info, "marketCap", None)
        shares = self._safe_get(info, "sharesOutstanding", None)

        items = [
            ("Company Name", self._safe_get(info, "longName")),
            ("Ticker", self.symbol),
            ("Exchange", self._safe_get(info, "exchange")),
            ("Currency", self._safe_get(info, "currency")),
            ("Country", self._safe_get(info, "country")),
            ("Sector", self._safe_get(info, "sector")),
            ("Industry", self._safe_get(info, "industry")),
            ("Market Cap", self._fmt_usd(mcap) if mcap != "—" else "—"),
            ("Shares Outstanding", self._fmt(shares) if shares != "—" else "—"),
            ("Full-Time Employees", self._safe_get(info, "fullTimeEmployees")),
            ("Website", self._safe_get(info, "website")),
        ]
        for label, val in items:
            lines.append(f"- **{label}**: {val}")

        summary = self._safe_get(info, "longBusinessSummary", None)
        if summary and summary != "—":
            lines.append("")
            truncated = summary[:800] + ("..." if len(summary) > 800 else "")
            lines.append(f"**Business Summary**: {truncated}")

        return "\n".join(lines)

    # ---- §2 Market Data ----

    def _section_02_market_data(self, info: dict) -> str:
        lines = [format_header(2, "2. Market Data")]

        price = self._safe_get(info, "currentPrice",
                               self._safe_get(info, "regularMarketPrice"))

        hi52 = self._safe_get(info, "fiftyTwoWeekHigh")
        lo52 = self._safe_get(info, "fiftyTwoWeekLow")

        items = [
            ("Current Price", f"${price}" if price != "—" else "—"),
            ("52-Week High", f"${hi52}" if hi52 != "—" else "—"),
            ("52-Week Low", f"${lo52}" if lo52 != "—" else "—"),
            ("50-Day MA", self._safe_get(info, "fiftyDayAverage")),
            ("200-Day MA", self._safe_get(info, "twoHundredDayAverage")),
            ("Market Cap", self._fmt_usd(self._safe_get(info, "marketCap", None))),
            ("Enterprise Value", self._fmt_usd(self._safe_get(info, "enterpriseValue", None))),
            ("PE (TTM)", self._safe_get(info, "trailingPE")),
            ("PE (Forward)", self._safe_get(info, "forwardPE")),
            ("PB", self._safe_get(info, "priceToBook")),
            ("PS (TTM)", self._safe_get(info, "priceToSalesTrailing12Months")),
            ("EV/EBITDA", self._safe_get(info, "enterpriseToEbitda")),
            ("EV/Revenue", self._safe_get(info, "enterpriseToRevenue")),
            ("Dividend Yield", self._fmt_pct(self._safe_get(info, "dividendYield", None))),
            ("Beta", self._safe_get(info, "beta")),
        ]
        for label, val in items:
            lines.append(f"- **{label}**: {val}")

        return "\n".join(lines)

    # ---- §3 Income Statement ----

    def _section_03_income_statement(self) -> str:
        if self._income is None or self._income.empty:
            return format_header(2, "3. Income Statement") + "\n\nNo data available."

        lines = [format_header(2, "3. Income Statement")]
        lines.append(f"(Unit: {DEFAULT_CONFIG.amount_unit} {DEFAULT_CONFIG.currency})")
        lines.append("")

        dates = [d.strftime("%Y") for d in self._income.columns]
        headers = ["Metric"] + dates

        field_map = [
            ("Revenue", ["Total Revenue"]),
            ("Cost of Revenue", ["Cost Of Revenue"]),
            ("Gross Profit", ["Gross Profit"]),
            ("Operating Expenses", ["Operating Expense", "Total Operating Expenses"]),
            ("Operating Income", ["Operating Income", "Operating Revenue"]),
            ("EBITDA", ["EBITDA", "Normalized EBITDA"]),
            ("Interest Expense", ["Interest Expense", "Interest Expense Non Operating"]),
            ("Pretax Income", ["Pretax Income"]),
            ("Income Tax", ["Tax Provision"]),
            ("Net Income", ["Net Income", "Net Income Common Stockholders"]),
        ]

        rows = []
        for label, names in field_map:
            row = self._fmt_row(label, self._income, names)
            if row:
                rows.append(row)

        # EPS rows (not divided by 1M)
        for label, names in [
            ("Basic EPS", ["Basic EPS"]),
            ("Diluted EPS", ["Diluted EPS"]),
        ]:
            row = self._fmt_row_eps(label, self._income, names)
            if row:
                rows.append(row)

        if rows:
            alignments = ["l"] + ["r"] * len(dates)
            lines.append(format_table(headers, rows, alignments))
        else:
            lines.append("Could not parse income statement fields.")

        return "\n".join(lines)

    # ---- §4 Balance Sheet ----

    def _section_04_balance_sheet(self) -> str:
        if self._balance is None or self._balance.empty:
            return format_header(2, "4. Balance Sheet") + "\n\nNo data available."

        lines = [format_header(2, "4. Balance Sheet")]
        lines.append(f"(Unit: {DEFAULT_CONFIG.amount_unit} {DEFAULT_CONFIG.currency})")
        lines.append("")

        dates = [d.strftime("%Y") for d in self._balance.columns]
        headers = ["Metric"] + dates

        field_map = [
            ("Total Assets", ["Total Assets"]),
            ("Current Assets", ["Current Assets"]),
            ("Cash & Equivalents", ["Cash And Cash Equivalents",
                                     "Cash Cash Equivalents And Short Term Investments"]),
            ("Accounts Receivable", ["Accounts Receivable", "Net Receivables", "Receivables"]),
            ("Inventory", ["Inventory"]),
            ("Non-Current Assets", ["Total Non Current Assets"]),
            ("Net PP&E", ["Net PPE", "Net Property Plant And Equipment"]),
            ("Goodwill", ["Goodwill"]),
            ("Intangible Assets", ["Intangible Assets", "Goodwill And Other Intangible Assets"]),
            ("Total Liabilities", ["Total Liabilities Net Minority Interest", "Total Liab"]),
            ("Current Liabilities", ["Current Liabilities"]),
            ("Current Debt", ["Current Debt", "Short Long Term Debt"]),
            ("Long-Term Debt", ["Long Term Debt"]),
            ("Stockholders' Equity", ["Total Stockholders Equity", "Stockholders Equity",
                                       "Total Equity Gross Minority Interest"]),
        ]

        rows = []
        for label, names in field_map:
            row = self._fmt_row(label, self._balance, names)
            if row:
                rows.append(row)

        if rows:
            alignments = ["l"] + ["r"] * len(dates)
            lines.append(format_table(headers, rows, alignments))
        else:
            lines.append("Could not parse balance sheet fields.")

        return "\n".join(lines)

    # ---- §5 Cash Flow ----

    def _section_05_cash_flow(self) -> str:
        if self._cashflow is None or self._cashflow.empty:
            return format_header(2, "5. Cash Flow Statement") + "\n\nNo data available."

        lines = [format_header(2, "5. Cash Flow Statement")]
        lines.append(f"(Unit: {DEFAULT_CONFIG.amount_unit} {DEFAULT_CONFIG.currency})")
        lines.append("")

        dates = [d.strftime("%Y") for d in self._cashflow.columns]
        headers = ["Metric"] + dates

        field_map = [
            ("Operating Cash Flow", ["Operating Cash Flow", "Total Cash From Operating Activities"]),
            ("Capital Expenditure", ["Capital Expenditure", "Capital Expenditures"]),
            ("Free Cash Flow", ["Free Cash Flow"]),
            ("Investing Cash Flow", ["Investing Cash Flow", "Total Cashflows From Investing Activities"]),
            ("Financing Cash Flow", ["Financing Cash Flow", "Total Cash From Financing Activities"]),
            ("Depreciation & Amortization", ["Depreciation And Amortization", "Depreciation"]),
            ("Share Buybacks", ["Repurchase Of Capital Stock", "Common Stock Repurchased"]),
            ("Dividends Paid", ["Common Stock Dividend Paid", "Cash Dividends Paid"]),
        ]

        rows = []
        for label, names in field_map:
            row = self._fmt_row(label, self._cashflow, names)
            if row:
                rows.append(row)

        # Compute FCF if not directly available from yfinance
        if not any(r[0] == "Free Cash Flow" for r in rows):
            ocf_row = next((r for r in rows if r[0] == "Operating Cash Flow"), None)
            capex_row = next((r for r in rows if r[0] == "Capital Expenditure"), None)
            if ocf_row and capex_row:
                fcf = ["Free Cash Flow"]
                for i in range(1, len(ocf_row)):
                    try:
                        o = float(ocf_row[i].replace(",", "")) if ocf_row[i] != "—" else None
                        c = float(capex_row[i].replace(",", "")) if capex_row[i] != "—" else None
                        if o is not None and c is not None:
                            fcf.append(f"{o + c:,.2f}")
                        else:
                            fcf.append("—")
                    except (ValueError, TypeError):
                        fcf.append("—")
                # Insert after Capital Expenditure
                capex_idx = next(i for i, r in enumerate(rows) if r[0] == "Capital Expenditure")
                rows.insert(capex_idx + 1, fcf)

        if rows:
            alignments = ["l"] + ["r"] * len(dates)
            lines.append(format_table(headers, rows, alignments))
        else:
            lines.append("Could not parse cash flow fields.")

        return "\n".join(lines)

    # ---- §6 Dividend History ----

    def _section_06_dividend_history(self, info: dict) -> str:
        lines = [format_header(2, "6. Dividend History")]

        div_yield = self._safe_get(info, "dividendYield", None)
        div_rate = self._safe_get(info, "dividendRate", None)
        payout = self._safe_get(info, "payoutRatio", None)

        lines.append(f"- **Dividend Yield**: {self._fmt_pct(div_yield) if div_yield and div_yield != '—' else '—'}")
        lines.append(f"- **Annual Dividend Rate**: ${div_rate}" if div_rate and div_rate != "—" else f"- **Annual Dividend Rate**: —")
        lines.append(f"- **Payout Ratio**: {self._fmt_pct(payout) if payout and payout != '—' else '—'}")

        try:
            dividends = self.ticker.dividends
            if dividends is not None and len(dividends) > 0:
                # Filter to last 5 years
                cutoff = pd.Timestamp.now() - pd.DateOffset(years=5)
                recent = dividends[dividends.index >= cutoff]
                if len(recent) == 0:
                    recent = dividends.tail(20)

                lines.append("")
                lines.append("**Dividend Payments (Last 5 Years)**:")
                lines.append("")
                headers = ["Date", "Dividend per Share"]
                rows = [[d.strftime("%Y-%m-%d"), f"${v:.4f}"] for d, v in recent.items()]
                lines.append(format_table(headers, rows))
            else:
                lines.append("\nNo dividend history found.")
        except Exception:
            lines.append("\nDividend data could not be retrieved.")

        return "\n".join(lines)

    # ---- §7-§9 Placeholders ----

    @staticmethod
    def _section_placeholder(title: str, msg: str) -> str:
        return f"{format_header(2, title)}\n\n*[{msg}]*"

    # ---- §10 Historical Prices (10 years weekly) ----

    def _section_10_historical_prices(self) -> str:
        if self._history is None or self._history.empty:
            return format_header(2, "10. Historical Prices") + "\n\nNo data available."

        lines = [format_header(2, "10. Historical Prices (10-Year Weekly)")]

        h = self._history
        lines.append(f"- **Date Range**: {h.index[0].strftime('%Y-%m-%d')} to {h.index[-1].strftime('%Y-%m-%d')}")
        lines.append(f"- **Data Points**: {len(h)} weekly bars")
        lines.append(f"- **All-Time High**: ${h['High'].max():.2f}")
        lines.append(f"- **All-Time Low**: ${h['Low'].min():.2f}")

        first_close = h["Close"].iloc[0]
        last_close = h["Close"].iloc[-1]
        total_return = ((last_close / first_close) - 1) * 100 if first_close else 0
        lines.append(f"- **Period Return**: {total_return:.2f}%")
        lines.append("")

        # Annual summary table
        yearly = h.resample("YE").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }).dropna()

        if not yearly.empty:
            lines.append("**Annual Price Summary**:")
            lines.append("")
            headers = ["Year", "Open", "High", "Low", "Close", "Change (%)"]
            rows = []
            prev_close = None
            for date, row in yearly.iterrows():
                yr = date.strftime("%Y")
                chg = f"{((row['Close'] / prev_close) - 1) * 100:.2f}" if prev_close else "—"
                rows.append([
                    yr,
                    f"${row['Open']:.2f}",
                    f"${row['High']:.2f}",
                    f"${row['Low']:.2f}",
                    f"${row['Close']:.2f}",
                    chg,
                ])
                prev_close = row["Close"]
            alignments = ["l"] + ["r"] * 5
            lines.append(format_table(headers, rows, alignments))

        return "\n".join(lines)

    # ---- §11 Financial Ratios ----

    def _section_11_financial_ratios(self, info: dict) -> str:
        lines = [format_header(2, "11. Financial Ratios")]

        items = [
            ("ROE", self._fmt_pct(self._safe_get(info, "returnOnEquity", None))),
            ("ROA", self._fmt_pct(self._safe_get(info, "returnOnAssets", None))),
            ("Gross Margin", self._fmt_pct(self._safe_get(info, "grossMargins", None))),
            ("Operating Margin", self._fmt_pct(self._safe_get(info, "operatingMargins", None))),
            ("Net Margin", self._fmt_pct(self._safe_get(info, "profitMargins", None))),
            ("Current Ratio", self._safe_get(info, "currentRatio")),
            ("Quick Ratio", self._safe_get(info, "quickRatio")),
            ("Debt / Equity", self._safe_get(info, "debtToEquity")),
            ("Revenue Growth", self._fmt_pct(self._safe_get(info, "revenueGrowth", None))),
            ("Earnings Growth", self._fmt_pct(self._safe_get(info, "earningsGrowth", None))),
            ("Book Value / Share", f"${self._safe_get(info, 'bookValue')}"
                if self._safe_get(info, "bookValue") != "—" else "—"),
            ("Shares Outstanding", self._fmt(self._safe_get(info, "sharesOutstanding", None))),
            ("Float Shares", self._fmt(self._safe_get(info, "floatShares", None))),
        ]
        for label, val in items:
            lines.append(f"- **{label}**: {val}")

        return "\n".join(lines)

    # ---- §12 Risk Warnings ----

    def _section_12_risk_warnings(self) -> str:
        lines = [format_header(2, "12. Risk Warnings")]
        lines.append("")
        lines.append("> Anomalies auto-detected during data collection for use in Phase 3 analysis.")
        lines.append("")

        warnings_list: list[tuple[str, str, str]] = []

        # Missing data checks
        if self._income is None or self._income.empty:
            warnings_list.append(("Data Gap", "High", "Income statement data missing."))
        if self._balance is None or self._balance.empty:
            warnings_list.append(("Data Gap", "High", "Balance sheet data missing."))
        if self._cashflow is None or self._cashflow.empty:
            warnings_list.append(("Data Gap", "High", "Cash flow statement data missing."))

        # Year-over-year anomaly checks in income statement
        if self._income is not None and not self._income.empty:
            for field, readable in [
                ("Total Revenue", "Revenue"),
                ("Net Income", "Net Income"),
            ]:
                if field in self._income.index:
                    vals = self._income.loc[field].dropna()
                    if len(vals) >= 2:
                        pct_changes = vals.pct_change().dropna().abs()
                        for date, chg in pct_changes.items():
                            if chg > 3.0:
                                warnings_list.append((
                                    "Anomaly", "High",
                                    f"{readable} changed by {chg * 100:.0f}% in {date.year}."))
                            elif chg > 1.0:
                                warnings_list.append((
                                    "Anomaly", "Medium",
                                    f"{readable} changed by {chg * 100:.0f}% in {date.year}."))

        # Negative equity check
        if self._balance is not None and not self._balance.empty:
            for eq_field in ["Total Stockholders Equity", "Stockholders Equity",
                             "Total Equity Gross Minority Interest"]:
                if eq_field in self._balance.index:
                    eq_vals = self._balance.loc[eq_field].dropna()
                    if len(eq_vals) > 0 and (eq_vals < 0).any():
                        neg_years = [d.year for d, v in eq_vals.items() if v < 0]
                        warnings_list.append((
                            "Solvency", "High",
                            f"Negative stockholders' equity in {', '.join(str(y) for y in neg_years)}."))
                    break

        # Declining OCF check
        if self._cashflow is not None and not self._cashflow.empty:
            for ocf_field in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                if ocf_field in self._cashflow.index:
                    ocf = self._cashflow.loc[ocf_field].dropna()
                    if len(ocf) >= 3:
                        # Check if OCF has been declining for 3+ consecutive periods
                        diffs = ocf.diff()
                        if (diffs.dropna() > 0).all():
                            # yfinance columns are descending; diff > 0 means earlier > later = decline
                            warnings_list.append((
                                "Cash Flow", "Medium",
                                "Operating cash flow has declined for 3+ consecutive years."))
                    break

        lines.append("### 12.1 Auto-Detected Warnings")
        lines.append("")
        if warnings_list:
            headers = ["#", "Category", "Severity", "Description"]
            rows = [[str(i + 1), cat, sev, desc]
                    for i, (cat, sev, desc) in enumerate(warnings_list)]
            lines.append(format_table(headers, rows))
        else:
            lines.append("No anomalies detected.")

        lines.append("")
        lines.append("### 12.2 WebSearch Warnings")
        lines.append("")
        lines.append("*[To be filled by Agent WebSearch — lawsuits, SEC filings, analyst downgrades.]*")

        return "\n".join(lines)

    # ---- §13 Risk-Free Rate ----

    def _section_13_risk_free_rate(self) -> str:
        rf = DEFAULT_CONFIG.risk_free_rate
        threshold = DEFAULT_CONFIG.threshold_ii
        lines = [format_header(2, "13. Risk-Free Rate")]
        lines.append("")
        lines.append(f"- **Benchmark**: US 10-Year Treasury")
        lines.append(f"- **Rate Used**: {rf * 100:.1f}%")
        lines.append(f"- **Threshold II (Rf + 3%)**: {threshold * 100:.1f}%")
        lines.append("")
        lines.append("*Note: Update the risk-free rate in config.py or fetch a live rate before analysis.*")
        return "\n".join(lines)

    # ---- §14 Share Buybacks ----

    def _section_14_share_buybacks(self) -> str:
        lines = [format_header(2, "14. Share Buybacks")]
        lines.append("")

        if self._cashflow is None or self._cashflow.empty:
            lines.append("No cash flow data available for buyback analysis.")
            return "\n".join(lines)

        dates = [d.strftime("%Y") for d in self._cashflow.columns]
        headers = ["Metric"] + dates

        buyback_fields = [
            ("Share Repurchases", ["Repurchase Of Capital Stock", "Common Stock Repurchased"]),
            ("Share Issuance", ["Common Stock Issuance", "Issuance Of Capital Stock"]),
        ]

        rows = []
        for label, names in buyback_fields:
            row = self._fmt_row(label, self._cashflow, names)
            if row:
                rows.append(row)

        # Net buyback = repurchase + issuance (both are usually negative/positive)
        if len(rows) >= 2:
            net = ["Net Buyback"]
            for i in range(1, len(rows[0])):
                try:
                    rep = float(rows[0][i].replace(",", "")) if rows[0][i] != "—" else 0
                    iss = float(rows[1][i].replace(",", "")) if rows[1][i] != "—" else 0
                    net.append(f"{rep + iss:,.2f}")
                except (ValueError, TypeError):
                    net.append("—")
            rows.append(net)

        # Shares outstanding trend from info
        shares = self._safe_get(self._get_info(), "sharesOutstanding", None)
        if shares and shares != "—":
            lines.append(f"- **Current Shares Outstanding**: {self._fmt(shares)} million")
            lines.append("")

        if rows:
            alignments = ["l"] + ["r"] * len(dates)
            lines.append(format_table(headers, rows, alignments))
        else:
            lines.append("No buyback data found in cash flow statement.")

        return "\n".join(lines)

    # ---- §15 Derived Metrics ----

    def _section_15_derived_metrics(self, info: dict) -> str:
        lines = [format_header(2, "15. Derived Metrics (Pre-computed)")]
        lines.append("")

        has_income = self._income is not None and not self._income.empty
        has_balance = self._balance is not None and not self._balance.empty
        has_cashflow = self._cashflow is not None and not self._cashflow.empty

        # --- Revenue YoY Growth ---
        if has_income and "Total Revenue" in self._income.index:
            rev = self._income.loc["Total Revenue"]
            dates = [d.strftime("%Y") for d in self._income.columns]
            growth = rev.pct_change(periods=-1) * 100  # descending order
            headers = ["Metric"] + dates
            row = ["Revenue YoY Growth (%)"] + [
                f"{v:.2f}" if pd.notna(v) else "—" for v in growth
            ]
            lines.append("**Revenue Growth**:")
            lines.append("")
            lines.append(format_table(headers, [row]))
            lines.append("")

        # --- Margin Trends ---
        if has_income:
            rev_key = "Total Revenue"
            margin_rows = []
            dates = [d.strftime("%Y") for d in self._income.columns]

            if rev_key in self._income.index:
                rev = self._income.loc[rev_key]
                for label, field in [
                    ("Gross Margin (%)", "Gross Profit"),
                    ("Operating Margin (%)", "Operating Income"),
                    ("Net Margin (%)", "Net Income"),
                ]:
                    if field in self._income.index:
                        margin = self._income.loc[field] / rev * 100
                        margin_rows.append(
                            [label] + [f"{v:.2f}" if pd.notna(v) else "—" for v in margin]
                        )

            if margin_rows:
                lines.append("**Margin Trends**:")
                lines.append("")
                headers = ["Metric"] + dates
                lines.append(format_table(headers, margin_rows))
                lines.append("")

        # --- ROE / ROA Trends from statements ---
        if has_income and has_balance:
            ni_field = None
            eq_field = None
            ta_field = None

            for f in ["Net Income", "Net Income Common Stockholders"]:
                if f in self._income.index:
                    ni_field = f
                    break
            for f in ["Total Stockholders Equity", "Stockholders Equity",
                      "Total Equity Gross Minority Interest"]:
                if f in self._balance.index:
                    eq_field = f
                    break
            for f in ["Total Assets"]:
                if f in self._balance.index:
                    ta_field = f
                    break

            re_rows = []
            if ni_field and eq_field:
                ni = self._income.loc[ni_field]
                eq = self._balance.loc[eq_field]
                common = ni.index.intersection(eq.index)
                if len(common) > 0:
                    roe = ni[common] / eq[common] * 100
                    dates_common = [d.strftime("%Y") for d in common]
                    re_rows.append(
                        ["ROE (%)"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in roe]
                    )

            if ni_field and ta_field:
                ni = self._income.loc[ni_field]
                ta = self._balance.loc[ta_field]
                common = ni.index.intersection(ta.index)
                if len(common) > 0:
                    roa = ni[common] / ta[common] * 100
                    if not re_rows:
                        dates_common = [d.strftime("%Y") for d in common]
                    re_rows.append(
                        ["ROA (%)"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in roa]
                    )

            if re_rows:
                lines.append("**Return Trends**:")
                lines.append("")
                headers = ["Metric"] + dates_common
                lines.append(format_table(headers, re_rows))
                lines.append("")

        # --- Cash Flow Quality Metrics ---
        if has_income and has_cashflow:
            ocf_field = None
            ni_field = None
            capex_field = None

            for f in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                if f in self._cashflow.index:
                    ocf_field = f
                    break
            for f in ["Net Income", "Net Income Common Stockholders"]:
                if f in self._income.index:
                    ni_field = f
                    break
            for f in ["Capital Expenditure", "Capital Expenditures"]:
                if f in self._cashflow.index:
                    capex_field = f
                    break

            cf_rows = []
            common_dates = None

            if ocf_field and ni_field:
                ocf = self._cashflow.loc[ocf_field]
                ni = self._income.loc[ni_field]
                common = ocf.index.intersection(ni.index)
                if len(common) > 0:
                    common_dates = common
                    ratio = ocf[common] / ni[common].replace(0, np.nan)
                    cf_rows.append(
                        ["OCF / Net Income"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in ratio]
                    )

            if ocf_field and capex_field:
                ocf = self._cashflow.loc[ocf_field]
                capex = self._cashflow.loc[capex_field]
                common = ocf.index.intersection(capex.index)
                if len(common) > 0:
                    if common_dates is None:
                        common_dates = common
                    # Capex is typically negative; ratio = |capex| / OCF
                    capex_ratio = capex[common].abs() / ocf[common].replace(0, np.nan)
                    cf_rows.append(
                        ["CapEx / OCF"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in capex_ratio]
                    )

            # FCF Yield = FCF / Market Cap
            mcap = self._safe_get(info, "marketCap", None)
            if ocf_field and capex_field and mcap and mcap != "—":
                ocf = self._cashflow.loc[ocf_field]
                capex = self._cashflow.loc[capex_field]
                common = ocf.index.intersection(capex.index)
                if len(common) > 0:
                    fcf = ocf[common] + capex[common]  # capex is negative
                    fcf_yield = fcf / float(mcap) * 100
                    cf_rows.append(
                        ["FCF Yield (%)"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in fcf_yield]
                    )

            if cf_rows and common_dates is not None:
                dates_cf = [d.strftime("%Y") for d in common_dates]
                lines.append("**Cash Flow Quality**:")
                lines.append("")
                headers = ["Metric"] + dates_cf
                lines.append(format_table(headers, cf_rows))
                lines.append("")

        # --- Debt Metrics ---
        if has_balance:
            eq_field = None
            debt_field = None
            ta_field = None

            for f in ["Total Stockholders Equity", "Stockholders Equity",
                      "Total Equity Gross Minority Interest"]:
                if f in self._balance.index:
                    eq_field = f
                    break
            for f in ["Total Liabilities Net Minority Interest", "Total Liab"]:
                if f in self._balance.index:
                    debt_field = f
                    break
            for f in ["Total Assets"]:
                if f in self._balance.index:
                    ta_field = f
                    break

            debt_rows = []
            if debt_field and eq_field:
                liab = self._balance.loc[debt_field]
                eq = self._balance.loc[eq_field]
                common = liab.index.intersection(eq.index)
                if len(common) > 0:
                    ratio = liab[common] / eq[common].replace(0, np.nan)
                    dates_b = [d.strftime("%Y") for d in common]
                    debt_rows.append(
                        ["Debt / Equity"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in ratio]
                    )

            if debt_field and ta_field:
                liab = self._balance.loc[debt_field]
                ta = self._balance.loc[ta_field]
                common = liab.index.intersection(ta.index)
                if len(common) > 0:
                    ratio = liab[common] / ta[common].replace(0, np.nan)
                    if not debt_rows:
                        dates_b = [d.strftime("%Y") for d in common]
                    debt_rows.append(
                        ["Debt / Assets"] + [f"{v:.2f}" if pd.notna(v) else "—" for v in ratio]
                    )

            if debt_rows:
                lines.append("**Leverage Trends**:")
                lines.append("")
                headers = ["Metric"] + dates_b
                lines.append(format_table(headers, debt_rows))

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect US equity financial data from Yahoo Finance for the Turtle Framework.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ticker AAPL
  %(prog)s --ticker AAPL --output output/AAPL/data_pack.md
  %(prog)s --ticker MSFT --years 5
  %(prog)s --ticker GOOGL --dry-run
        """,
    )
    parser.add_argument(
        "--ticker", required=True,
        help="US stock ticker symbol (e.g., AAPL, MSFT, GOOGL)")
    parser.add_argument(
        "--years", type=int, default=5,
        help="Years of financial statement data (default: 5)")
    parser.add_argument(
        "--output", default=None,
        help="Output file path (default: output/<TICKER>/data_pack.md)")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print configuration and exit without fetching data")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Validate and normalize ticker
    try:
        ticker = validate_us_ticker(args.ticker)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_dir = get_output_dir(ticker)
        output_path = os.path.join(output_dir, "data_pack.md")

    if args.dry_run:
        print("=== Dry Run ===")
        print(f"  Ticker : {ticker}")
        print(f"  Years  : {args.years}")
        print(f"  Output : {output_path}")
        print(f"  Currency: {DEFAULT_CONFIG.currency}")
        print(f"  Unit   : {DEFAULT_CONFIG.amount_unit}")
        print(f"  Rf     : {DEFAULT_CONFIG.risk_free_rate * 100:.1f}%")
        return

    print(f"Collecting data for {ticker} from Yahoo Finance ...")
    collector = YFinanceCollector(ticker, args.years)
    data_pack = collector.assemble_data_pack()

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(data_pack)

    file_size = os.path.getsize(output_path)
    print(f"\nOutput written to {output_path}")
    print(f"File size: {file_size:,} bytes")
    print("Done!")


if __name__ == "__main__":
    main()
