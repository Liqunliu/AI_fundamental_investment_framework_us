#!/usr/bin/env python3
"""Bloomberg data collector for US Equity Quality Yield Strategy.

Collects financial data from Bloomberg Terminal API, handles currency
conversion for ADR / foreign companies, and outputs English-language
markdown data packs compatible with calculate_qy_gg.py.

Features over the Chinese version:
  - Currency detection (EQY_FUND_CRNCY) and automatic FX conversion to USD
  - Expanded cash flow fields: capex, dividends paid, buybacks, SBC
  - English labels matching GG calculator's _METRIC_LABEL_MAP
  - Shareholder returns section (buybacks + SBC)

Usage:
    # Basic — single ticker
    python3 scripts/bloomberg_collector.py --security "AAPL US Equity" \\
        --output output/AAPL/data_pack.md

    # ADR with automatic currency conversion
    python3 scripts/bloomberg_collector.py --security "PBR US Equity" \\
        --output output/PBR/data_pack.md

    # Override detected currency (e.g., force USD for testing)
    python3 scripts/bloomberg_collector.py --security "PDD US Equity" \\
        --currency USD --output output/PDD/data_pack.md

    # Check which fields Bloomberg supports
    python3 scripts/bloomberg_collector.py --security "AAPL US Equity" --field-check

Requires:
    - blpapi (pip install blpapi)
    - SSH tunnel to Bloomberg Terminal: ssh -L 8194:127.0.0.1:8194 user@vm
"""

from __future__ import annotations

import argparse
import os
import sys

# Add scripts directory to path for format_utils import
sys.path.insert(0, os.path.dirname(__file__))

from bloomberg_modules import (
    InfrastructureMixin,
    FinancialsMixin,
    OtherDataMixin,
    DerivedMetricsMixin,
    AssemblyMixin,
    CASHFLOW_FIELDS,
    SHAREHOLDER_FIELDS,
    INCOME_FIELDS,
    BALANCE_FIELDS,
)


class BloombergClient(
    InfrastructureMixin,
    FinancialsMixin,
    OtherDataMixin,
    DerivedMetricsMixin,
    AssemblyMixin,
):
    """Bloomberg data client for US Equity Quality Yield Strategy."""

    def __init__(self, api_mode: str = "terminal", **kwargs):
        InfrastructureMixin.__init__(self)

        if api_mode == "terminal":
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 8194)
            if not self._init_terminal_api(host, port):
                raise ConnectionError(
                    f"Cannot connect to Bloomberg on {host}:{port}. "
                    "Ensure Terminal is running and SSH tunnel is active: "
                    "ssh -L 8194:127.0.0.1:8194 user@vm"
                )
        elif api_mode == "hapi":
            cid = kwargs.get("client_id", "")
            csecret = kwargs.get("client_secret", "")
            if not self._init_hapi(cid, csecret):
                raise ConnectionError("HAPI authentication failed")
        else:
            raise ValueError(f"Unknown api_mode: {api_mode}")


def field_check(client: BloombergClient, security: str):
    """Test which Bloomberg fields return data for a given security."""
    from datetime import datetime, timedelta

    end = datetime.now()
    start = end - timedelta(days=2 * 365)  # 2 years for quick check

    all_fields = {
        "Income": INCOME_FIELDS,
        "Balance": BALANCE_FIELDS,
        "Cash Flow": CASHFLOW_FIELDS,
        "Shareholder": SHAREHOLDER_FIELDS,
    }

    print(f"\n{'='*60}")
    print(f"Field Check: {security}")
    print(f"{'='*60}")

    for group_name, fields in all_fields.items():
        print(f"\n--- {group_name} Fields ---")
        try:
            df = client._terminal_historical_request(
                security, fields,
                start.strftime("%Y%m%d"), end.strftime("%Y%m%d"),
                periodicity="YEARLY",
            )
            for field in fields:
                if field in df.columns and df[field].notna().any():
                    sample = df[field].dropna().iloc[-1]
                    print(f"  ✓ {field:30s} = {sample}")
                else:
                    print(f"  ✗ {field:30s} = (no data)")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Reference fields
    print(f"\n--- Reference Fields ---")
    try:
        ref_fields = ["EQY_FUND_CRNCY", "CRNCY", "CUR_MKT_CAP", "EQY_SH_OUT"]
        df = client._terminal_reference_request([security], ref_fields)
        if not df.empty:
            row = df.iloc[0]
            for f in ref_fields:
                val = row.get(f, "(missing)")
                print(f"  ✓ {f:30s} = {val}")
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Bloomberg data collector for US Equity Quality Yield Strategy"
    )
    parser.add_argument(
        "--security", required=True,
        help='Bloomberg security ID (e.g., "AAPL US Equity")',
    )
    parser.add_argument(
        "--api", default="terminal", choices=["terminal", "hapi"],
        help="API mode (default: terminal)",
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8194)
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument(
        "--output", default=None,
        help="Output file path (default: output/{TICKER}/data_pack.md)",
    )
    parser.add_argument(
        "--currency", default=None,
        help="Override reporting currency (e.g., USD to skip conversion)",
    )
    parser.add_argument(
        "--field-check", action="store_true",
        help="Test which Bloomberg fields return data, then exit",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse args only, do not connect to Bloomberg",
    )

    args = parser.parse_args()

    if args.dry_run:
        print(f"Security: {args.security}")
        print(f"API mode: {args.api}")
        print(f"Output: {args.output}")
        return

    # Connect
    try:
        client = BloombergClient(
            api_mode=args.api, host=args.host, port=args.port,
        )
    except ConnectionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Field check mode
        if args.field_check:
            field_check(client, args.security)
            return

        # Override currency if specified
        if args.currency:
            client._reporting_currency = args.currency.upper()
            print(f"Currency override: {client._reporting_currency}")

        # Assemble data pack
        data_pack = client.assemble_data_pack(args.security, args.years)

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            ticker = args.security.replace(" US Equity", "").replace(" Equity", "")
            output_path = os.path.join("output", ticker, "data_pack.md")

        # Write output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(data_pack)

        print(f"\n{'='*60}")
        print(f"Data pack written to: {output_path}")
        print(f"{'='*60}")

    finally:
        client.cleanup()


if __name__ == "__main__":
    main()
