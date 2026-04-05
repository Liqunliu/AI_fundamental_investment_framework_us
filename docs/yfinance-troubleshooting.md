# yfinance Troubleshooting Notes

## Common Issues in Corporate/Dev Environments

### 1. SSL Certificate Errors

**Symptoms**: `SSLError`, `CERTIFICATE_VERIFY_FAILED`, connection refused

**Root Cause**: Corporate proxy/firewall intercepts HTTPS traffic with its own certificate, which Python's SSL doesn't trust.

**Fixes applied in scripts**:
```python
import os
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["PYTHONHTTPSVERIFY"] = "0"

# For requests-based libraries:
os.environ["REQUESTS_CA_BUNDLE"] = ""

# For curl_cffi (used by newer yfinance):
from curl_cffi import requests as curl_requests
_orig = curl_requests.Session.request
def _patched(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    return _orig(self, *args, **kwargs)
curl_requests.Session.request = _patched

# Nuclear option (last resort):
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### 2. Rate Limiting (429 Too Many Requests)

**Symptoms**: `429 Client Error: Too Many Requests`, `possibly delisted; no price data found`

**Root Cause**: Yahoo Finance aggressively rate-limits API requests, especially from corporate IPs (shared IPs mean many users count against the same limit).

**Workarounds**:
- Add delays between requests: `time.sleep(0.5)` every 20 tickers
- Use in-memory caching (`_PRICE_CACHE`, `_FINANCIAL_CACHE`) to avoid redundant calls
- Use Bloomberg Terminal API as alternative data source (requires `blpapi` + SSH tunnel)
- Wait for rate limit to reset (typically 10-30 minutes)

**Impact on backtester**: If yfinance is rate-limited, the backtester cannot fetch prices. The Bloomberg mode (`--source bloomberg`) bypasses this entirely.

### 3. "Possibly Delisted" False Positives

**Symptoms**: `$AAPL: possibly delisted; no price data found` — even for active tickers

**Root Cause**: This is yfinance's generic error when it can't fetch data. Can be caused by:
- Rate limiting (429 errors, see above)
- SSL issues blocking the connection
- Network connectivity problems
- Yahoo Finance API changes/outages

**Diagnosis**: Try `yf.Ticker("AAPL").history(period="1d")` — if even this fails, it's a connectivity/rate-limit issue, not a delisting.

### 4. Data Format Differences

**yfinance column ordering**:
- Financial statements (`.financials`, `.cashflow`, `.balance_sheet`): Columns are dates, **newest first** (descending)
- Price history (`.history()`): Rows are dates, **oldest first** (ascending)

**Bloomberg column ordering (in data packs)**:
- Financial statements: Columns are years, **oldest first** (ascending, e.g., 2021, 2022, 2023)

**Fix in `calculate_qy_gg.py`**: Added `_columns_are_descending()` auto-detection:
```python
def _columns_are_descending(rows):
    """Detect if columns are newest-first (yfinance) vs oldest-first (Bloomberg)."""
    years = [int(re.match(r"(\d{4})", str(key)).group(1)) for key in rows[0] if re.match(r"(\d{4})", str(key))]
    return years[0] > years[-1] if len(years) >= 2 else False
```

### 5. Section Header Parsing (yfinance data packs)

**yfinance-generated data packs** use numbered section headers:
```
## 2. Market Data
## 3. Income Statement
```

**Bloomberg data packs** use plain headers:
```
## Market Data
## Income Statement
```

**Fix**: Made regex in `calculate_qy_gg.py` handle optional numbering:
```python
# Before:
re.match(r"^##\s+Market\s+Data", line)
# After:
re.match(r"^##\s+(?:\d+\.\s+)?Market\s+Data", line)
```

## Recommended Approach

For **production backtesting** or when yfinance is unreliable:
1. Use `--source bloomberg` with the Quality Yield backtester
2. Pre-fetch all data once: `python3 scripts/qy_backtest.py --prefetch-bloomberg`
3. Run backtest from cache: `python3 scripts/qy_backtest.py --source bloomberg ...`

For **quick analysis** when yfinance is working:
1. Use default `--source yfinance`
2. Add throttling (`time.sleep`) if rate-limited
3. Run during off-peak hours (weekends, evenings)
