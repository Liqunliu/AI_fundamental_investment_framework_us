#!/usr/bin/env python3
"""
SEC EDGAR Filing Downloader

Downloads the latest 10-K (or 20-F for foreign filers) from SEC EDGAR.

Features:
  - CIK lookup from SEC's company_tickers.json (cached 24h)
  - Filing index from SEC submissions API
  - Downloads primary HTML document
  - Rate limiting (0.15s between requests per SEC guidelines)
  - Configurable User-Agent via SEC_EDGAR_USER_AGENT env var

Usage:
    export SEC_EDGAR_USER_AGENT="Your Name your.email@example.com"
    python3 scripts/edgar_downloader.py --ticker AAPL
    python3 scripts/edgar_downloader.py --ticker AAPL --form-type 10-K
    python3 scripts/edgar_downloader.py --ticker BABA --form-type 20-F

Output:
    output/{TICKER}/{TICKER}_10K.html
    output/{TICKER}/{TICKER}_filing_meta.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Project imports
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from config import get_output_dir  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEC_BASE = "https://www.sec.gov"
SEC_EFTS = "https://efts.sec.gov"
SEC_DATA = "https://data.sec.gov"
TICKERS_URL = f"{SEC_BASE}/files/company_tickers.json"
CACHE_DIR = Path("output/.cache")
TICKERS_CACHE = CACHE_DIR / "company_tickers.json"
CACHE_TTL_HOURS = 24

# Acceptable form types for annual reports
ANNUAL_FORM_TYPES = {"10-K", "10-K/A", "20-F", "20-F/A"}

# Acceptable form types for interim/quarterly reports
INTERIM_FORM_TYPES = {"10-Q", "10-Q/A", "6-K", "6-K/A"}

# Rate limiting: SEC requires max 10 requests/second
MIN_REQUEST_INTERVAL = 0.15
_last_request_time = 0.0


def _get_user_agent() -> str:
    """Get User-Agent string. SEC requires contact info."""
    ua = os.environ.get("SEC_EDGAR_USER_AGENT")
    if ua:
        return ua
    # Fallback — SEC may reject requests without proper identification
    return "QYStrategy/1.0 (research@example.com)"


def _rate_limit():
    """Enforce rate limiting between SEC requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _sec_get(url: str, headers: Optional[Dict] = None) -> requests.Response:
    """Make a rate-limited GET request to SEC."""
    _rate_limit()
    hdrs = {"User-Agent": _get_user_agent(), "Accept-Encoding": "gzip, deflate"}
    if headers:
        hdrs.update(headers)
    resp = requests.get(url, headers=hdrs, timeout=30)
    resp.raise_for_status()
    return resp


# ===================================================================
# CIK Lookup
# ===================================================================

def _load_tickers_cache() -> Optional[Dict]:
    """Load cached company_tickers.json if fresh enough."""
    if not TICKERS_CACHE.exists():
        return None
    mtime = datetime.fromtimestamp(TICKERS_CACHE.stat().st_mtime)
    if datetime.now() - mtime > timedelta(hours=CACHE_TTL_HOURS):
        return None
    try:
        return json.loads(TICKERS_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_tickers_cache(data: Dict):
    """Save company_tickers.json to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TICKERS_CACHE.write_text(json.dumps(data), encoding="utf-8")


def lookup_cik(ticker: str) -> Tuple[str, str]:
    """Look up CIK and company name for a ticker symbol.

    Returns:
        (cik_str_padded, company_name)

    Raises:
        ValueError if ticker not found.
    """
    ticker_upper = ticker.upper()

    # Try cache first
    data = _load_tickers_cache()
    if data is None:
        print(f"  Downloading SEC company tickers list...")
        resp = _sec_get(TICKERS_URL)
        data = resp.json()
        _save_tickers_cache(data)

    # Search for ticker
    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik = str(entry["cik_str"]).zfill(10)
            name = entry.get("title", ticker_upper)
            return cik, name

    raise ValueError(
        f"Ticker '{ticker}' not found in SEC EDGAR. "
        "It may be a non-US company without SEC filings."
    )


# ===================================================================
# Filing Discovery
# ===================================================================

def find_latest_filing(
    cik: str,
    form_types: Optional[set] = None,
) -> Dict:
    """Find the latest annual filing for a CIK.

    Args:
        cik: Zero-padded 10-digit CIK string.
        form_types: Set of acceptable form types (default: 10-K, 20-F).

    Returns:
        Dict with keys: accession_number, filing_date, form_type, primary_document, url

    Raises:
        ValueError if no filing found.
    """
    if form_types is None:
        form_types = ANNUAL_FORM_TYPES

    url = f"{SEC_DATA}/submissions/CIK{cik}.json"
    print(f"  Fetching filing index: {url}")
    resp = _sec_get(url)
    submissions = resp.json()

    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    # Find the latest matching filing
    for i, form in enumerate(forms):
        if form in form_types:
            acc = accessions[i].replace("-", "")
            acc_formatted = accessions[i]
            doc = primary_docs[i] if i < len(primary_docs) else None

            if not doc:
                continue

            filing_url = f"{SEC_BASE}/Archives/edgar/data/{cik.lstrip('0')}/{acc}/{doc}"

            return {
                "accession_number": acc_formatted,
                "filing_date": dates[i] if i < len(dates) else "unknown",
                "form_type": form,
                "primary_document": doc,
                "url": filing_url,
                "cik": cik,
            }

    raise ValueError(
        f"No {'/'.join(form_types)} filing found for CIK {cik}. "
        "The company may file different form types."
    )


# ===================================================================
# Filing Download
# ===================================================================

def download_filing(filing_info: Dict, output_dir: Path) -> Path:
    """Download the filing HTML document.

    Args:
        filing_info: Dict from find_latest_filing().
        output_dir: Directory to save the file.

    Returns:
        Path to the downloaded HTML file.
    """
    url = filing_info["url"]
    print(f"  Downloading filing: {url}")
    resp = _sec_get(url)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine extension from primary document name
    doc_name = filing_info["primary_document"]
    ext = Path(doc_name).suffix or ".html"
    form_short = filing_info["form_type"].replace("-", "").replace("/", "")

    # Use a clean filename
    output_file = output_dir / f"{output_dir.name}_{form_short}{ext}"
    output_file.write_bytes(resp.content)

    return output_file


def save_filing_meta(filing_info: Dict, output_dir: Path) -> Path:
    """Save filing metadata as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_file = output_dir / f"{output_dir.name}_filing_meta.json"

    meta = {
        **filing_info,
        "downloaded_at": datetime.now().isoformat(),
    }
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta_file


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SEC EDGAR Filing Downloader"
    )
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol (e.g. AAPL)")
    parser.add_argument(
        "--form-type",
        default=None,
        help="Specific form type to look for (e.g. 10-K, 20-F). "
             "Default: searches 10-K first, then 20-F."
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: output/{TICKER}/)"
    )
    parser.add_argument(
        "--include-interim",
        action="store_true",
        default=False,
        help="Also download the latest interim filing (10-Q or 6-K)"
    )
    args = parser.parse_args()

    ticker = args.ticker.upper()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(get_output_dir(ticker))

    # Determine form types to search
    if args.form_type:
        form_types = {args.form_type, f"{args.form_type}/A"}
    else:
        form_types = ANNUAL_FORM_TYPES

    print(f"SEC EDGAR Downloader — {ticker}")
    print(f"{'=' * 40}")

    try:
        # Step 1: CIK lookup
        print(f"\n[1/3] Looking up CIK for {ticker}...")
        cik, company_name = lookup_cik(ticker)
        print(f"  Found: {company_name} (CIK: {cik})")

        # Step 2: Find latest filing
        print(f"\n[2/3] Finding latest annual filing...")
        filing_info = find_latest_filing(cik, form_types)
        print(f"  Form: {filing_info['form_type']}")
        print(f"  Date: {filing_info['filing_date']}")
        print(f"  Accession: {filing_info['accession_number']}")

        # Step 3: Download
        print(f"\n[3/3] Downloading filing...")
        html_path = download_filing(filing_info, output_dir)
        meta_path = save_filing_meta(filing_info, output_dir)

        file_size = html_path.stat().st_size
        print(f"\n  Filing saved: {html_path} ({file_size:,} bytes)")
        print(f"  Metadata saved: {meta_path}")

        # Verify
        if file_size < 1000:
            print(f"\n  WARNING: Filing is unusually small ({file_size} bytes).", file=sys.stderr)

        # Step 4 (optional): Download interim filing
        if args.include_interim:
            try:
                print(f"\n[4/4] Finding latest interim filing (10-Q/6-K)...")
                interim_info = find_latest_filing(cik, INTERIM_FORM_TYPES)
                print(f"  Form: {interim_info['form_type']}")
                print(f"  Date: {interim_info['filing_date']}")
                print(f"  Accession: {interim_info['accession_number']}")

                interim_html = download_filing(interim_info, output_dir)
                # Save interim metadata separately
                interim_meta_file = output_dir / f"{output_dir.name}_interim_meta.json"
                interim_meta = {
                    **interim_info,
                    "downloaded_at": datetime.now().isoformat(),
                }
                interim_meta_file.write_text(
                    json.dumps(interim_meta, indent=2), encoding="utf-8"
                )

                interim_size = interim_html.stat().st_size
                print(f"  Interim filing saved: {interim_html} ({interim_size:,} bytes)")
                print(f"  Interim metadata saved: {interim_meta_file}")
            except Exception as e:
                print(f"\n  WARNING: Interim filing download failed: {e}", file=sys.stderr)
                print(f"  Continuing without interim filing.", file=sys.stderr)

        print(f"\nDone.")

    except ValueError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"\nERROR: Network error — {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
