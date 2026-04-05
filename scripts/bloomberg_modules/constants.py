"""Bloomberg field mappings and constants for US Equity Quality Yield Strategy.

All display names match the GG calculator's _METRIC_LABEL_MAP for seamless parsing.
"""

# ── Income Statement Fields ──────────────────────────────────────────────────
INCOME_FIELDS = [
    "SALES_REV_TURN",        # Revenue
    "IS_COGS_TO_FE_AND_PP_AND_G",  # Cost of Revenue
    "IS_OPER_INC",           # Operating Income
    "NET_INCOME",            # Net Income
    "EBITDA",                # EBITDA
    "GROSS_PROFIT",          # Gross Profit
    "IS_INC_BEF_XO_ITEM",   # Pretax Income
    "IS_INC_TAX_EXP",        # Income Tax Expense
    "IS_INT_EXPENSE",        # Interest Expense
]

# ── Balance Sheet Fields ─────────────────────────────────────────────────────
BALANCE_FIELDS = [
    "BS_TOT_ASSET",            # Total Assets
    "BS_TOT_LIAB2",            # Total Liabilities
    "TOT_COMMON_EQY",          # Shareholders' Equity
    "BS_CUR_ASSET_REPORT",     # Current Assets
    "BS_CUR_LIAB",             # Current Liabilities
    "BS_CASH_NEAR_CASH_ITEM",  # Cash & Equivalents
    "BS_ACCT_NOTE_RCV",        # Accounts Receivable
    "BS_INVENTORIES",          # Inventory
    "BS_ACCT_NOTE_PAY",        # Accounts Payable
    "BS_GOODWILL",             # Goodwill
    "BS_INTANG_FIXED_ASSETS",  # Intangible Assets
    "BS_LT_BORROW",            # Long-Term Debt
    "BS_ST_BORROW",            # Short-Term Debt
]

# ── Cash Flow Fields (expanded for GG calculation) ───────────────────────────
CASHFLOW_FIELDS = [
    "CF_CASH_FROM_OPER",       # Operating Cash Flow
    "CF_CASH_FROM_INV_ACT",    # Investing Cash Flow
    "CF_FREE_CASH_FLOW",       # Free Cash Flow
    "CF_CASH_FROM_FNC_ACT",    # Financing Cash Flow
    "CAPITAL_EXPEND",          # Capital Expenditures
    "CF_DEPR_AMORT",           # Depreciation & Amortization
    "CF_DVD_PAID",             # Dividends Paid (cash flow)
]

# ── Shareholder Return Fields (fetched in separate request) ──────────────────
# Verified via blp_field_search.py — these are the correct Bloomberg mnemonics.
SHAREHOLDER_FIELDS = [
    "CF_DECR_CAP_STOCK",           # Share Repurchases (Cash Flow/Financing Activities)
    "CF_STOCK_BASED_COMPENSATION", # Stock-Based Compensation (Cash Flow/Operating Activities)
]

# ── Market Data Fields ───────────────────────────────────────────────────────
MARKET_FIELDS = [
    "PX_LAST",               # Last Price
    "CUR_MKT_CAP",           # Market Cap (always in local listing currency)
    "PE_RATIO",              # P/E Ratio
    "PX_TO_BOOK_RATIO",      # P/B Ratio
    "TRAIL_12M_EPS",         # EPS (TTM)
    "DIVIDEND_YIELD",        # Dividend Yield
    "RETURN_ON_ASSET",       # ROA
    "RETURN_COM_EQY",        # ROE
    "EQY_SH_OUT",            # Shares Outstanding
]

# ── Company Info Fields (includes currency detection) ────────────────────────
COMPANY_INFO_FIELDS = [
    "NAME",
    "LONG_COMP_NAME",
    "COUNTRY_ISO",
    "INDUSTRY_SECTOR",
    "GICS_SECTOR_NAME",
    "GICS_INDUSTRY_NAME",
    "EQY_FUND_CRNCY",         # Fundamental data reporting currency
    "CRNCY",                   # Security price currency
]

# ── Dividend Fields ──────────────────────────────────────────────────────────
DIVIDEND_FIELDS = [
    "DIVIDEND_YIELD",
    "EQY_DVD_YLD_IND",
]

# ── Combined ─────────────────────────────────────────────────────────────────
ALL_FINANCIAL_FIELDS = INCOME_FIELDS + BALANCE_FIELDS + CASHFLOW_FIELDS

# ── Display Names (English) ──────────────────────────────────────────────────
# These labels MUST match the aliases in calculate_qy_gg.py's
# _METRIC_LABEL_MAP so the GG calculator can parse the output.
FIELD_DISPLAY_NAMES = {
    # Income Statement
    "SALES_REV_TURN":       "Revenue",
    "IS_COGS_TO_FE_AND_PP_AND_G": "Cost of Revenue",
    "IS_OPER_INC":          "Operating Income",
    "NET_INCOME":           "Net Income",
    "EBITDA":               "EBITDA",
    "GROSS_PROFIT":         "Gross Profit",
    "IS_INC_BEF_XO_ITEM":  "Pretax Income",
    "IS_INC_TAX_EXP":       "Income Tax",
    "IS_INT_EXPENSE":       "Interest Expense",
    # Balance Sheet
    "BS_TOT_ASSET":            "Total Assets",
    "BS_TOT_LIAB2":            "Total Liabilities",
    "TOT_COMMON_EQY":          "Shareholders' Equity",
    "BS_CUR_ASSET_REPORT":     "Current Assets",
    "BS_CUR_LIAB":             "Current Liabilities",
    "BS_CASH_NEAR_CASH_ITEM":  "Cash & Equivalents",
    "BS_ACCT_NOTE_RCV":        "Accounts Receivable",
    "BS_INVENTORIES":          "Inventory",
    "BS_ACCT_NOTE_PAY":        "Accounts Payable",
    "BS_GOODWILL":             "Goodwill",
    "BS_INTANG_FIXED_ASSETS":  "Intangible Assets",
    "BS_LT_BORROW":            "Long-Term Debt",
    "BS_ST_BORROW":            "Short-Term Debt",
    # Cash Flow
    "CF_CASH_FROM_OPER":       "Operating Cash Flow",
    "CF_CASH_FROM_INV_ACT":    "Investing Cash Flow",
    "CF_FREE_CASH_FLOW":       "Free Cash Flow",
    "CF_CASH_FROM_FNC_ACT":    "Financing Cash Flow",
    "CAPITAL_EXPEND":          "Capital Expenditure",
    "CF_DEPR_AMORT":           "Depreciation & Amortization",
    "CF_DVD_PAID":             "Dividends Paid",
    "CF_DECR_CAP_STOCK":           "Share Repurchases",
    "CF_STOCK_BASED_COMPENSATION": "Stock-Based Compensation",
    # Market Data
    "PX_LAST":               "Last Price",
    "CUR_MKT_CAP":           "Market Cap",
    "PE_RATIO":              "P/E Ratio",
    "PX_TO_BOOK_RATIO":      "P/B Ratio",
    "TRAIL_12M_EPS":         "EPS (TTM)",
    "DIVIDEND_YIELD":        "Dividend Yield",
    "RETURN_ON_ASSET":       "ROA",
    "RETURN_COM_EQY":        "ROE",
    "EQY_SH_OUT":            "Shares Outstanding",
}

# ── Bloomberg API ────────────────────────────────────────────────────────────
SERVICE_REFDATA = "//blp/refdata"
SERVICE_MKTDATA = "//blp/mktdata"

HAPI_BASE_URL = "https://api.bloomberg.com/eap"
HAPI_AUTH_URL = "https://bsso.blpprofessional.com/ext/api/as/token.oauth2"
