"""TTL-based disk cache for data collection.

Caches yfinance/Bloomberg data in JSON files under ``output/.cache/``
to avoid redundant API calls during screening workflows.

Cache key format: ``output/.cache/{TICKER}/{data_type}.json``

Each cached entry stores:
  - ``timestamp``: ISO-format write time
  - ``data``: the payload (dict, list, or DataFrame-as-dict)

DataFrame serialization follows the pattern from ``qy_backtest.py``:
  ``{"index": [...], "columns": [...], "data": [...]}``
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Default TTLs (seconds) — can be overridden via config
# ---------------------------------------------------------------------------
DEFAULT_TTLS: Dict[str, int] = {
    "financials": 7 * 86400,    # 7 days
    "info": 7 * 86400,          # 7 days
    "prices": 86400,            # 1 day
    "history": 86400,           # 1 day
    "income": 7 * 86400,        # 7 days
    "balance": 7 * 86400,       # 7 days
    "cashflow": 7 * 86400,      # 7 days
}


class DataCache:
    """TTL-based disk cache with DataFrame serialization."""

    def __init__(
        self,
        cache_dir: str = "output/.cache",
        ttls: Optional[Dict[str, int]] = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttls = {**DEFAULT_TTLS, **(ttls or {})}
        # Session stats
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, ticker: str, data_type: str) -> Optional[Any]:
        """Return cached data if fresh, None if stale/missing."""
        path = self._path(ticker, data_type)
        if not path.exists():
            self._misses += 1
            return None

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._misses += 1
            return None

        ts = raw.get("timestamp")
        if ts is None:
            self._misses += 1
            return None

        age = time.time() - _parse_iso(ts)
        ttl = self.ttls.get(data_type, DEFAULT_TTLS.get(data_type, 86400))
        if age > ttl:
            self._misses += 1
            return None

        self._hits += 1
        data = raw.get("data")
        return _deserialize(data)

    def put(self, ticker: str, data_type: str, data: Any) -> None:
        """Store data with timestamp."""
        path = self._path(ticker, data_type)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker.upper(),
            "data_type": data_type,
            "data": _serialize(data),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )

    def invalidate(self, ticker: str, data_type: Optional[str] = None) -> None:
        """Remove cached data for a ticker (optionally specific type)."""
        if data_type:
            path = self._path(ticker, data_type)
            if path.exists():
                path.unlink()
        else:
            ticker_dir = self.cache_dir / ticker.upper()
            if ticker_dir.is_dir():
                for f in ticker_dir.iterdir():
                    f.unlink()
                ticker_dir.rmdir()

    def stats(self) -> dict:
        """Return cache hit/miss stats for current session."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": f"{self._hits / total:.0%}" if total > 0 else "N/A",
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _path(self, ticker: str, data_type: str) -> Path:
        return self.cache_dir / ticker.upper() / f"{data_type}.json"


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """Convert Python objects to JSON-safe structures.

    DataFrames are stored in split format for compact, lossless round-trip.
    """
    if isinstance(obj, pd.DataFrame):
        # Convert index to strings for JSON
        idx = obj.index.tolist()
        cols = obj.columns.tolist()
        # Convert Timestamps in columns to ISO strings
        cols_serial = [
            c.isoformat() if hasattr(c, "isoformat") else str(c) for c in cols
        ]
        idx_serial = [
            i.isoformat() if hasattr(i, "isoformat") else str(i) for i in idx
        ]
        return {
            "__dataframe__": True,
            "index": idx_serial,
            "columns": cols_serial,
            "data": _nan_to_none(obj.values.tolist()),
        }
    if isinstance(obj, pd.Series):
        return _serialize(obj.to_frame().T)
    return obj


def _deserialize(obj: Any) -> Any:
    """Reconstruct Python objects from JSON-safe structures."""
    if isinstance(obj, dict) and obj.get("__dataframe__"):
        df = pd.DataFrame(
            data=obj["data"],
            index=obj["index"],
            columns=obj["columns"],
        )
        # Try to parse column strings as datetime
        try:
            import warnings as _w
            with _w.catch_warnings():
                _w.simplefilter("ignore", UserWarning)
                df.columns = pd.to_datetime(df.columns)
        except (ValueError, TypeError):
            pass
        return df
    return obj


def _nan_to_none(data):
    """Recursively replace NaN/inf with None for JSON serialization."""
    if isinstance(data, list):
        return [_nan_to_none(item) for item in data]
    if isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
        return None
    return data


def _json_default(obj):
    """JSON fallback serializer for numpy/pandas types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, np.ndarray):
        return _nan_to_none(obj.tolist())
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _parse_iso(ts_str: str) -> float:
    """Parse ISO timestamp string to epoch seconds."""
    try:
        return datetime.fromisoformat(ts_str).timestamp()
    except (ValueError, TypeError):
        return 0.0
