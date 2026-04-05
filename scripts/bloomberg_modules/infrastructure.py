"""Infrastructure mixin for Bloomberg API client — US Equity version.

Adds currency detection and FX conversion for ADR / foreign-domiciled companies.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    import blpapi
    _BLPAPI_AVAILABLE = True
except ImportError:
    _BLPAPI_AVAILABLE = False
    blpapi = None

try:
    import requests as _requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    _requests = None

from .constants import SERVICE_REFDATA, HAPI_BASE_URL, HAPI_AUTH_URL


class InfrastructureMixin:
    """Base infrastructure for Bloomberg API connections with currency support."""

    def __init__(self):
        self._session = None
        self._hapi_token = None
        self._hapi_catalog = None
        self._cache_dir = os.path.join("output", ".bloomberg_cache")
        self._api_mode = None  # 'terminal' or 'hapi'
        self._store: Dict[str, pd.DataFrame] = {}
        self._target_currency = "USD"
        # Currency conversion state
        self._reporting_currency: Optional[str] = None  # detected from Bloomberg
        self._fx_rate: Optional[float] = None           # units of reporting CCY per 1 USD
        os.makedirs(self._cache_dir, exist_ok=True)

    # ── Connection ───────────────────────────────────────────────────────────

    def _init_terminal_api(self, host: str = "localhost", port: int = 8194) -> bool:
        """Connect to Bloomberg Terminal via blpapi."""
        if not _BLPAPI_AVAILABLE:
            print("ERROR: blpapi not installed. Run: pip install blpapi", file=sys.stderr)
            return False

        opts = blpapi.SessionOptions()
        opts.setServerHost(host)
        opts.setServerPort(port)
        self._session = blpapi.Session(opts)

        if not self._session.start():
            print(f"FAILED: Could not connect to Bloomberg on {host}:{port}", file=sys.stderr)
            return False

        if not self._session.openService(SERVICE_REFDATA):
            print(f"FAILED: Could not open {SERVICE_REFDATA} service", file=sys.stderr)
            return False

        self._api_mode = "terminal"
        print(f"Connected to Bloomberg Terminal on {host}:{port}")
        return True

    def _init_hapi(self, client_id: str, client_secret: str) -> bool:
        """Authenticate to Bloomberg HAPI."""
        if not _REQUESTS_AVAILABLE:
            print("ERROR: requests not installed.", file=sys.stderr)
            return False

        try:
            resp = _requests.post(
                HAPI_AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            if resp.status_code != 200:
                print(f"FAILED: HAPI auth (HTTP {resp.status_code})", file=sys.stderr)
                return False

            self._hapi_token = resp.json().get("access_token")
            self._api_mode = "hapi"

            headers = {"Authorization": f"Bearer {self._hapi_token}"}
            resp = _requests.get(f"{HAPI_BASE_URL}/catalogs/", headers=headers, timeout=30)
            if resp.status_code == 200:
                catalogs = resp.json().get("contains", [])
                if catalogs:
                    self._hapi_catalog = catalogs[0].get("identifier", "")
                    print(f"Connected to Bloomberg HAPI (catalog: {self._hapi_catalog})")
            return True
        except Exception as e:
            print(f"FAILED: HAPI init error: {e}", file=sys.stderr)
            return False

    # ── Data Requests ────────────────────────────────────────────────────────

    def _terminal_reference_request(
        self,
        securities: List[str],
        fields: List[str],
        overrides: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        """Execute a ReferenceDataRequest (BDP-style)."""
        if self._api_mode != "terminal" or not self._session:
            raise RuntimeError("Terminal API not initialized")

        service = self._session.getService(SERVICE_REFDATA)
        request = service.createRequest("ReferenceDataRequest")

        for sec in securities:
            request.append("securities", sec)
        for field in fields:
            request.append("fields", field)

        if overrides:
            ov_elem = request.getElement("overrides")
            for key, val in overrides.items():
                ov = ov_elem.appendElement()
                ov.setElement("fieldId", key)
                ov.setElement("value", val)

        self._session.sendRequest(request)

        results = []
        while True:
            event = self._session.nextEvent(30000)
            if event.eventType() == blpapi.Event.TIMEOUT:
                print("WARNING: Reference request timed out", file=sys.stderr)
                break

            for msg in event:
                if msg.messageType() == blpapi.Name("ReferenceDataResponse"):
                    sec_data_array = msg.getElement("securityData")
                    for i in range(sec_data_array.numValues()):
                        sec_data = sec_data_array.getValueAsElement(i)
                        security = sec_data.getElementAsString("security")

                        if sec_data.hasElement("securityError"):
                            err_msg = sec_data.getElement("securityError").getElementAsString("message")
                            print(f"ERROR for {security}: {err_msg}", file=sys.stderr)
                            continue

                        field_data = sec_data.getElement("fieldData")
                        row = {"security": security}
                        for field in fields:
                            row[field] = self._get_field_value(field_data, field)

                        if sec_data.hasElement("fieldExceptions"):
                            fe_array = sec_data.getElement("fieldExceptions")
                            for j in range(fe_array.numValues()):
                                fe = fe_array.getValueAsElement(j)
                                bad_field = fe.getElementAsString("fieldId")
                                err_info = fe.getElement("errorInfo")
                                err_msg = err_info.getElementAsString("message")
                                print(f"WARNING: Field {bad_field} for {security}: {err_msg}", file=sys.stderr)
                                row[bad_field] = None

                        results.append(row)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame(results)

    def _terminal_historical_request(
        self,
        security: str,
        fields: List[str],
        start_date: str,
        end_date: str,
        periodicity: str = "YEARLY",
    ) -> pd.DataFrame:
        """Execute a HistoricalDataRequest (BDH-style)."""
        if self._api_mode != "terminal" or not self._session:
            raise RuntimeError("Terminal API not initialized")

        service = self._session.getService(SERVICE_REFDATA)
        request = service.createRequest("HistoricalDataRequest")

        request.append("securities", security)
        for field in fields:
            request.append("fields", field)

        request.set("startDate", start_date)
        request.set("endDate", end_date)
        request.set("periodicitySelection", periodicity)

        self._session.sendRequest(request)

        results = []
        while True:
            event = self._session.nextEvent(30000)
            if event.eventType() == blpapi.Event.TIMEOUT:
                print("WARNING: Historical request timed out", file=sys.stderr)
                break

            for msg in event:
                if msg.messageType() == blpapi.Name("HistoricalDataResponse"):
                    sec_data = msg.getElement("securityData")
                    security_name = sec_data.getElementAsString("security")
                    fd_array = sec_data.getElement("fieldData")

                    for i in range(fd_array.numValues()):
                        fd = fd_array.getValueAsElement(i)
                        row = {"security": security_name}
                        if fd.hasElement("date"):
                            row["date"] = fd.getElementAsString("date")
                        for field in fields:
                            if fd.hasElement(field):
                                elem = fd.getElement(field)
                                if not elem.isNull():
                                    dtype = elem.datatype()
                                    if dtype in (blpapi.DataType.FLOAT32, blpapi.DataType.FLOAT64):
                                        row[field] = elem.getValueAsFloat()
                                    elif dtype in (blpapi.DataType.INT32, blpapi.DataType.INT64):
                                        row[field] = elem.getValueAsInteger()
                                    else:
                                        row[field] = elem.getValueAsString()
                                else:
                                    row[field] = None
                            else:
                                row[field] = None
                        results.append(row)

            if event.eventType() == blpapi.Event.RESPONSE:
                break

        return pd.DataFrame(results)

    def _get_field_value(self, field_data, field: str) -> Any:
        """Extract a typed value from a Bloomberg fieldData element."""
        if not field_data.hasElement(field):
            return None
        elem = field_data.getElement(field)
        if elem.isNull():
            return None
        dtype = elem.datatype()
        if dtype in (blpapi.DataType.FLOAT32, blpapi.DataType.FLOAT64):
            return elem.getValueAsFloat()
        elif dtype in (blpapi.DataType.INT32, blpapi.DataType.INT64):
            return elem.getValueAsInteger()
        else:
            return elem.getValueAsString()

    # ── Currency Detection & Conversion ──────────────────────────────────────

    def detect_reporting_currency(self, security: str) -> str:
        """Detect the fundamental-data reporting currency for a security.

        Uses EQY_FUND_CRNCY (the currency Bloomberg uses for financial
        statements). Falls back to CRNCY (security price currency) and
        finally to "USD".

        Returns:
            ISO currency code, e.g. "USD", "BRL", "CNY".
        """
        if self._api_mode != "terminal":
            return "USD"

        try:
            df = self._terminal_reference_request(
                [security], ["EQY_FUND_CRNCY", "CRNCY"]
            )
            if df.empty:
                return "USD"

            row = df.iloc[0]
            fund_ccy = row.get("EQY_FUND_CRNCY")
            sec_ccy = row.get("CRNCY")

            ccy = fund_ccy or sec_ccy or "USD"
            self._reporting_currency = str(ccy).upper()
            print(f"  Reporting currency: {self._reporting_currency}")
            return self._reporting_currency

        except Exception as e:
            print(f"WARNING: Currency detection failed: {e}", file=sys.stderr)
            return "USD"

    def fetch_fx_rate(self, from_ccy: str) -> float:
        """Fetch FX rate: how many units of *from_ccy* per 1 USD.

        Uses the Bloomberg cross-rate security ``USD{from_ccy} Curncy``.
        For example, ``USDBRL Curncy`` returns ~5.7 (1 USD = 5.7 BRL).

        Returns:
            FX rate (> 0). Returns 1.0 for USD or on error.
        """
        from_ccy = from_ccy.upper()
        if from_ccy == "USD":
            self._fx_rate = 1.0
            return 1.0

        fx_security = f"USD{from_ccy} Curncy"
        print(f"  Fetching FX rate: {fx_security} ...")

        try:
            df = self._terminal_reference_request([fx_security], ["PX_LAST"])
            if df.empty:
                print(f"WARNING: No FX data for {fx_security}, defaulting to 1.0", file=sys.stderr)
                self._fx_rate = 1.0
                return 1.0

            rate = df.iloc[0].get("PX_LAST")
            if rate is None or float(rate) <= 0:
                print(f"WARNING: Invalid FX rate for {fx_security}, defaulting to 1.0", file=sys.stderr)
                self._fx_rate = 1.0
                return 1.0

            self._fx_rate = float(rate)
            print(f"  FX rate: 1 USD = {self._fx_rate:.4f} {from_ccy}")
            return self._fx_rate

        except Exception as e:
            print(f"WARNING: FX fetch failed: {e}", file=sys.stderr)
            self._fx_rate = 1.0
            return 1.0

    def convert_df_to_usd(self, df: pd.DataFrame, fx_rate: float,
                          exclude_cols: Optional[List[str]] = None) -> pd.DataFrame:
        """Convert all numeric columns in a DataFrame from reporting currency to USD.

        Args:
            df: DataFrame with values in reporting currency.
            fx_rate: Units of reporting currency per 1 USD (e.g. 5.7 for BRL).
            exclude_cols: Column names to skip (e.g. 'date', 'security').

        Returns:
            New DataFrame with converted values.
        """
        if fx_rate == 1.0 or df.empty:
            return df

        exclude = set(exclude_cols or []) | {"security", "date"}
        out = df.copy()
        for col in out.columns:
            if col in exclude:
                continue
            if pd.api.types.is_numeric_dtype(out[col]):
                out[col] = out[col] / fx_rate
        return out

    # ── Cleanup ──────────────────────────────────────────────────────────────

    def cleanup(self):
        """Stop the Bloomberg session."""
        if self._session:
            self._session.stop()
            self._session = None
