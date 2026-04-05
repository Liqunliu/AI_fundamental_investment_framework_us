"""Bloomberg data collector modules for US Equity Quality Yield Strategy.

Mixin classes for BloombergClient:
- InfrastructureMixin: API connection, currency detection, FX conversion
- FinancialsMixin: Income statement, balance sheet, cash flow, shareholder returns
- OtherDataMixin: Market data, dividends, company info
- DerivedMetricsMixin: Margins, ratios, growth rates
- AssemblyMixin: English markdown data pack assembly
"""

from .constants import (
    INCOME_FIELDS,
    BALANCE_FIELDS,
    CASHFLOW_FIELDS,
    SHAREHOLDER_FIELDS,
    MARKET_FIELDS,
    COMPANY_INFO_FIELDS,
    DIVIDEND_FIELDS,
    ALL_FINANCIAL_FIELDS,
    FIELD_DISPLAY_NAMES,
    SERVICE_REFDATA,
    SERVICE_MKTDATA,
    HAPI_BASE_URL,
    HAPI_AUTH_URL,
)

from .infrastructure import InfrastructureMixin
from .financials import FinancialsMixin
from .other_data import OtherDataMixin
from .derived_metrics import DerivedMetricsMixin
from .assembly import AssemblyMixin

__all__ = [
    # Constants
    "INCOME_FIELDS",
    "BALANCE_FIELDS",
    "CASHFLOW_FIELDS",
    "SHAREHOLDER_FIELDS",
    "MARKET_FIELDS",
    "COMPANY_INFO_FIELDS",
    "DIVIDEND_FIELDS",
    "ALL_FINANCIAL_FIELDS",
    "FIELD_DISPLAY_NAMES",
    "SERVICE_REFDATA",
    "SERVICE_MKTDATA",
    "HAPI_BASE_URL",
    "HAPI_AUTH_URL",
    # Mixins
    "InfrastructureMixin",
    "FinancialsMixin",
    "OtherDataMixin",
    "DerivedMetricsMixin",
    "AssemblyMixin",
]
