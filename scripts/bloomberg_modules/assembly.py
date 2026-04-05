"""Data pack assembly mixin — US Equity version.

Outputs English labels matching calculate_qy_gg.py expectations.
Includes currency conversion notes and shareholder returns sections.
"""

from __future__ import annotations

import sys
from datetime import datetime

import pandas as pd

# Import format utilities from parent directory
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from format_utils import format_number, format_table, format_header
from warning_schema import detect_warnings, save_warnings_json


class AssemblyMixin:
    """Mixin for assembling the final markdown data pack in English."""

    def assemble_data_pack(self, security: str, years: int = 5) -> str:
        """Assemble complete data pack for a US-listed security.

        Handles currency detection and conversion for ADR / foreign companies.
        """
        sections = []
        ticker = security.replace(" US Equity", "").replace(" Equity", "")

        # ── Step 1: Fetch company info (includes currency detection) ─────
        print("\n=== Fetching data ===")
        company_info = self.fetch_company_info(security)

        # ── Step 2: Detect currency and fetch FX rate if needed ──────────
        reporting_ccy = getattr(self, "_reporting_currency", None) or "USD"
        fx_rate = 1.0
        needs_conversion = reporting_ccy != "USD"

        if needs_conversion:
            fx_rate = self.fetch_fx_rate(reporting_ccy)
            print(f"  *** Currency conversion active: {reporting_ccy} → USD (rate: {fx_rate:.4f}) ***")

        # ── Step 3: Fetch remaining data ─────────────────────────────────
        market_data = self.fetch_market_data(security)
        financials = self.fetch_all_financials(security, years)
        dividends = self.fetch_dividends(security, years)

        # ── Step 4: Convert financials to USD if needed ──────────────────
        if needs_conversion and fx_rate > 0:
            for key in ("income", "balance", "cashflow"):
                if key in self._store and not self._store[key].empty:
                    self._store[key] = self.convert_df_to_usd(
                        self._store[key], fx_rate
                    )
                    print(f"  Converted {key} from {reporting_ccy} to USD")

        # ── Step 5: Calculate derived metrics (on converted data) ────────
        print("\nCalculating derived metrics...")
        derived = self.calculate_all_derived_metrics()

        # ── Step 6: Assemble markdown ────────────────────────────────────
        company_name = ""
        if not company_info.empty:
            company_name = company_info.iloc[0].get("LONG_COMP_NAME", "") or \
                           company_info.iloc[0].get("NAME", ticker)

        sections.append(format_header(1, f"Data Pack: {company_name} ({ticker})"))
        sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sections.append("Data source: Bloomberg Terminal")
        sections.append(f"Data window: {years} years")
        sections.append("Currency: USD")
        sections.append("Amount unit: Millions USD")

        if needs_conversion:
            sections.append(
                f"Reporting Currency: {reporting_ccy} "
                f"(converted to USD at 1 USD = {fx_rate:.4f} {reporting_ccy})"
            )
        else:
            sections.append("Reporting Currency: USD (no conversion needed)")

        sections.append("")

        # Sections
        sections.append(self._format_company_info(company_info))
        sections.append(self._format_market_data(market_data))
        sections.append(self._format_income_statement())
        sections.append(self._format_balance_sheet())
        sections.append(self._format_cashflow_statement())
        sections.append(self._format_dividends_section())
        sections.append(self._format_share_buybacks())
        sections.append(self._format_margins(derived.get("margins")))
        sections.append(self._format_liquidity_ratios(derived.get("liquidity")))
        sections.append(self._format_leverage_ratios(derived.get("leverage")))
        sections.append(self._format_efficiency_ratios(derived.get("efficiency")))
        sections.append(self._format_risk_warnings(ticker))
        sections.append(self._format_risk_free_rate())

        return "\n\n".join(filter(None, sections))

    # ── Risk Warnings ─────────────────────────────────────────────────────────

    def _format_risk_warnings(self, ticker: str) -> str:
        """Detect warnings from Bloomberg data and save warnings.json."""
        # Build DataFrames in row-as-item format for detect_warnings
        income_df = self._store.get("income")
        balance_df = self._store.get("balance")
        cashflow_df = self._store.get("cashflow")

        # Convert Bloomberg column-oriented DFs to row-oriented (field as index)
        inc_t = income_df.set_index("date").T if income_df is not None and not income_df.empty and "date" in income_df.columns else pd.DataFrame()
        bal_t = balance_df.set_index("date").T if balance_df is not None and not balance_df.empty and "date" in balance_df.columns else pd.DataFrame()
        cf_t = cashflow_df.set_index("date").T if cashflow_df is not None and not cashflow_df.empty and "date" in cashflow_df.columns else pd.DataFrame()

        self._warnings = detect_warnings(inc_t, bal_t, cf_t, {})

        # Save warnings.json
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "output", ticker)
        os.makedirs(output_dir, exist_ok=True)
        warn_path = save_warnings_json(self._warnings, output_dir)
        print(f"  Warnings JSON: {warn_path} ({len(self._warnings)} warnings)")

        # Render markdown
        lines = [format_header(2, "12. Risk Warnings")]
        lines.append("")
        lines.append("> Anomalies auto-detected during data collection.")
        lines.append("")
        lines.append("### 12.1 Auto-Detected Warnings")
        lines.append("")
        if self._warnings:
            headers = ["#", "Type", "Category", "Severity", "Description"]
            rows = [
                [str(i + 1), w.type, w.category, w.severity, w.message]
                for i, w in enumerate(self._warnings)
            ]
            lines.append(format_table(headers, rows))
        else:
            lines.append("No anomalies detected.")
        return "\n".join(lines)

    # ── Section Formatters ───────────────────────────────────────────────────

    def _format_company_info(self, df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Company Overview")]
        row = df.iloc[0]
        items = [
            ("Company Name", "NAME"),
            ("Full Name", "LONG_COMP_NAME"),
            ("Country", "COUNTRY_ISO"),
            ("Sector", "INDUSTRY_SECTOR"),
            ("GICS Sector", "GICS_SECTOR_NAME"),
            ("GICS Industry", "GICS_INDUSTRY_NAME"),
            ("Reporting Currency", "EQY_FUND_CRNCY"),
        ]
        for label, field in items:
            if field in row and pd.notna(row[field]):
                lines.append(f"- **{label}**: {row[field]}")
        return "\n".join(lines)

    def _format_market_data(self, df: pd.DataFrame) -> str:
        """Market data section — labels match GG calculator's _MARKET_LABEL_MAP."""
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Market Data")]
        row = df.iloc[0]

        # Market cap: Bloomberg returns in local listing currency.
        # For US-listed equities (including ADRs), CUR_MKT_CAP is in USD.
        items = [
            ("Last Price", "PX_LAST", 1, 2),
            ("Market Cap", "CUR_MKT_CAP", 1e6, 2),     # → millions
            ("P/E Ratio", "PE_RATIO", 1, 2),
            ("P/B Ratio", "PX_TO_BOOK_RATIO", 1, 2),
            ("EPS (TTM)", "TRAIL_12M_EPS", 1, 2),
            ("Dividend Yield", "DIVIDEND_YIELD", 1, 2),
            ("ROA", "RETURN_ON_ASSET", 1, 2),
            ("ROE", "RETURN_COM_EQY", 1, 2),
            ("Shares Outstanding", "EQY_SH_OUT", 1, 2),  # already in millions
        ]

        for label, field, divider, decimals in items:
            if field in row and pd.notna(row[field]):
                val = format_number(row[field], divider, decimals)
                # Add % suffix for yield/ratio fields
                if field == "DIVIDEND_YIELD":
                    lines.append(f"- **{label}**: {val}%")
                else:
                    lines.append(f"- **{label}**: {val}")

        return "\n".join(lines)

    def _format_income_statement(self) -> str:
        """Income statement table with labels matching GG calculator."""
        df = self._store.get("income")
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Income Statement")]
        lines.append("(Unit: Millions USD)")
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates

        field_map = [
            ("Revenue", "SALES_REV_TURN"),
            ("Gross Profit", "GROSS_PROFIT"),
            ("Operating Income", "IS_OPER_INC"),
            ("EBITDA", "EBITDA"),
            ("Pretax Income", "IS_INC_BEF_XO_ITEM"),
            ("Net Income", "NET_INCOME"),
            ("Income Tax", "IS_INC_TAX_EXP"),
        ]

        rows = []
        alignments = ["l"] + ["r"] * len(dates)
        for label, field in field_map:
            if field in df.columns:
                row = [label] + [format_number(v, 1, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_balance_sheet(self) -> str:
        """Balance sheet table with labels matching GG calculator."""
        df = self._store.get("balance")
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Balance Sheet")]
        lines.append("(Unit: Millions USD)")
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates

        field_map = [
            ("Total Assets", "BS_TOT_ASSET"),
            ("Current Assets", "BS_CUR_ASSET_REPORT"),
            ("Cash & Equivalents", "BS_CASH_NEAR_CASH_ITEM"),
            ("Accounts Receivable", "BS_ACCT_NOTE_RCV"),
            ("Inventory", "BS_INVENTORIES"),
            ("Total Liabilities", "BS_TOT_LIAB2"),
            ("Current Liabilities", "BS_CUR_LIAB"),
            ("Short-Term Debt", "BS_ST_BORROW"),
            ("Long-Term Debt", "BS_LT_BORROW"),
            ("Shareholders' Equity", "TOT_COMMON_EQY"),
        ]

        rows = []
        alignments = ["l"] + ["r"] * len(dates)
        for label, field in field_map:
            if field in df.columns:
                row = [label] + [format_number(v, 1, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_cashflow_statement(self) -> str:
        """Cash flow table — includes capex, dividends, buybacks, SBC.

        All labels match GG calculator's _METRIC_LABEL_MAP exactly.
        """
        df = self._store.get("cashflow")
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Cash Flow")]
        lines.append("(Unit: Millions USD)")
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates

        # Core cash flow fields
        field_map = [
            ("Operating Cash Flow", "CF_CASH_FROM_OPER"),
            ("Capital Expenditure", "CAPITAL_EXPEND"),
            ("Free Cash Flow", "CF_FREE_CASH_FLOW"),
            ("Investing Cash Flow", "CF_CASH_FROM_INV_ACT"),
            ("Financing Cash Flow", "CF_CASH_FROM_FNC_ACT"),
            ("Dividends Paid", "CF_DVD_PAID"),
            ("Share Repurchases", "CF_DECR_CAP_STOCK"),
            ("Stock-Based Compensation", "CF_STOCK_BASED_COMPENSATION"),
        ]

        rows = []
        alignments = ["l"] + ["r"] * len(dates)
        for label, field in field_map:
            if field in df.columns and df[field].notna().any():
                row = [label] + [format_number(v, 1, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_dividends_section(self) -> str:
        """Dividend history section."""
        lines = [format_header(2, "Dividend History")]

        # Current metrics
        if "dividend_current" in self._store and not self._store["dividend_current"].empty:
            current = self._store["dividend_current"].iloc[0]
            if "DIVIDEND_YIELD" in current and pd.notna(current["DIVIDEND_YIELD"]):
                lines.append(f"- **Dividend Yield**: {format_number(current['DIVIDEND_YIELD'], 1, 2)}%")
            if "EQY_DVD_YLD_IND" in current and pd.notna(current["EQY_DVD_YLD_IND"]):
                lines.append(f"- **Indicated Yield**: {format_number(current['EQY_DVD_YLD_IND'], 1, 2)}%")
            lines.append("")

        # Historical table
        dvd_df = self._store.get("dividends")
        if dvd_df is not None and not dvd_df.empty and "DVD_HIST_ALL" in dvd_df.columns:
            dvd_data = dvd_df[dvd_df["DVD_HIST_ALL"].notna()].tail(20)
            if not dvd_data.empty:
                lines.append("**Dividend Payments**:")
                lines.append("")
                headers = ["Date", "Dividend per Share"]
                rows = []
                for _, row in dvd_data.iterrows():
                    date = str(row.get("date", ""))
                    amount = format_number(row["DVD_HIST_ALL"], 1, 4)
                    rows.append([date, amount])
                lines.append(format_table(headers, rows, ["l", "r"]))

        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_share_buybacks(self) -> str:
        """Separate Share Buybacks section for GG calculator compatibility.

        The GG calculator also searches for a dedicated '## Share Buybacks'
        section as a backup source for buyback data.
        """
        cf = self._store.get("cashflow")
        if cf is None or cf.empty:
            return ""

        # Only output if we have buyback data
        has_buybacks = "CF_DECR_CAP_STOCK" in cf.columns and cf["CF_DECR_CAP_STOCK"].notna().any()
        has_sbc = "CF_STOCK_BASED_COMPENSATION" in cf.columns and cf["CF_STOCK_BASED_COMPENSATION"].notna().any()

        if not has_buybacks and not has_sbc:
            return ""

        lines = [format_header(2, "Share Buybacks")]
        lines.append("(Unit: Millions USD)")
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in cf.get("date", range(len(cf)))]
        headers = ["Metric"] + dates
        alignments = ["l"] + ["r"] * len(dates)

        rows = []
        if has_buybacks:
            row = ["Share Repurchases"] + [format_number(v, 1, 2) for v in cf["CF_DECR_CAP_STOCK"]]
            rows.append(row)
        if has_sbc:
            row = ["Stock-Based Compensation"] + [format_number(v, 1, 2) for v in cf["CF_STOCK_BASED_COMPENSATION"]]
            rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_margins(self, df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Profit Margins")]
        lines.append("(Unit: %)")
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates
        alignments = ["l"] + ["r"] * len(dates)

        metrics = [
            ("Gross Margin", "gross_margin"),
            ("Operating Margin", "operating_margin"),
            ("Net Margin", "net_margin"),
            ("EBITDA Margin", "ebitda_margin"),
        ]

        rows = []
        for label, field in metrics:
            if field in df.columns:
                row = [label] + [format_number(v, 1, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_liquidity_ratios(self, df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Liquidity Ratios")]
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates
        alignments = ["l"] + ["r"] * len(dates)

        metrics = [
            ("Current Ratio", "current_ratio"),
            ("Quick Ratio", "quick_ratio"),
            ("Cash Ratio", "cash_ratio"),
        ]

        rows = []
        for label, field in metrics:
            if field in df.columns:
                row = [label] + [format_number(v, 1, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_leverage_ratios(self, df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Leverage Ratios")]
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates
        alignments = ["l"] + ["r"] * len(dates)

        metrics = [
            ("Debt / Assets", "debt_to_assets"),
            ("Debt / Equity", "debt_to_equity"),
            ("Total Debt (M)", "total_debt"),
            ("Net Debt (M)", "net_debt"),
        ]

        rows = []
        for label, field in metrics:
            if field in df.columns:
                # total_debt and net_debt are already in millions (from converted data)
                divider = 1
                row = [label] + [format_number(v, divider, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_efficiency_ratios(self, df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return ""

        lines = [format_header(2, "Efficiency Ratios")]
        lines.append("")

        dates = [str(d)[:4] if len(str(d)) >= 4 else str(d)
                 for d in df.get("date", range(len(df)))]
        headers = ["Metric"] + dates
        alignments = ["l"] + ["r"] * len(dates)

        metrics = [
            ("Asset Turnover", "asset_turnover"),
            ("Receivables Turnover", "receivables_turnover"),
            ("Days Sales Outstanding", "days_sales_outstanding"),
            ("Inventory Turnover", "inventory_turnover"),
            ("Days Inventory Outstanding", "days_inventory_outstanding"),
        ]

        rows = []
        for label, field in metrics:
            if field in df.columns:
                row = [label] + [format_number(v, 1, 2) for v in df[field]]
                rows.append(row)

        if rows:
            lines.append(format_table(headers, rows, alignments))
        return "\n".join(lines)

    def _format_risk_free_rate(self) -> str:
        """Risk-free rate section for GG calculator context."""
        lines = [format_header(2, "Risk-Free Rate")]
        lines.append("- **Benchmark**: US 10-Year Treasury")
        lines.append("- **Rate Used**: 4.3%")
        lines.append("- **Threshold II (Rf + 3%)**: 7.3%")
        return "\n".join(lines)
