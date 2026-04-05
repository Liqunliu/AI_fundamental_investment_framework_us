"""Structured warning types and auto-detection for data collection.

Provides a typed Warning dataclass and detect_warnings() function that
replaces the ad-hoc markdown warnings in yfinance_collector.py §12.
Warnings are serializable to JSON for machine consumption by the
preflight agent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class Warning:
    type: str        # "data-missing", "audit-risk", "goodwill-high", etc.
    category: str    # "Data Gap", "Solvency", "Anomaly", "Cash Flow", "Asset Quality"
    severity: str    # "HIGH", "MEDIUM", "LOW"
    message: str     # Human-readable description
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def detect_warnings(
    income_df: Optional[pd.DataFrame],
    balance_df: Optional[pd.DataFrame],
    cashflow_df: Optional[pd.DataFrame],
    info_dict: Optional[dict],
) -> List[Warning]:
    """Run all warning detectors and return a list of Warning objects.

    Args:
        income_df:  Income statement DataFrame (rows = line items, cols = dates).
        balance_df: Balance sheet DataFrame.
        cashflow_df: Cash flow statement DataFrame.
        info_dict:  Ticker .info dict from yfinance (or equivalent).

    Returns:
        List of Warning objects, sorted by severity (HIGH first).
    """
    warnings: List[Warning] = []
    info = info_dict or {}

    # --- 1. data-missing: critical financial data absent ---
    for df, label in [
        (income_df, "Income statement"),
        (balance_df, "Balance sheet"),
        (cashflow_df, "Cash flow statement"),
    ]:
        if df is None or df.empty:
            warnings.append(Warning(
                type="data-missing",
                category="Data Gap",
                severity="HIGH",
                message=f"{label} data missing.",
                metadata={"field": label},
            ))

    # --- 2. audit-risk: negative equity ---
    if balance_df is not None and not balance_df.empty:
        for eq_field in [
            "Total Stockholders Equity",
            "Stockholders Equity",
            "Total Equity Gross Minority Interest",
            # Bloomberg labels
            "Total Equity",
        ]:
            if eq_field in balance_df.index:
                eq_vals = balance_df.loc[eq_field].dropna()
                if len(eq_vals) > 0 and (eq_vals < 0).any():
                    neg_years = [int(d.year) for d, v in eq_vals.items() if v < 0]
                    warnings.append(Warning(
                        type="audit-risk",
                        category="Solvency",
                        severity="HIGH",
                        message=f"Negative stockholders' equity in {', '.join(str(y) for y in neg_years)}.",
                        metadata={"years": neg_years, "field": eq_field},
                    ))
                break

    # --- 3. goodwill-high: goodwill > 50% of equity ---
    if balance_df is not None and not balance_df.empty:
        gw_val = _latest_value(balance_df, ["Goodwill", "Goodwill And Other Intangible Assets"])
        eq_val = _latest_value(balance_df, [
            "Total Stockholders Equity", "Stockholders Equity",
            "Total Equity Gross Minority Interest", "Total Equity",
        ])
        if gw_val is not None and eq_val is not None and eq_val > 0:
            ratio = gw_val / eq_val
            if ratio > 0.5:
                warnings.append(Warning(
                    type="goodwill-high",
                    category="Asset Quality",
                    severity="MEDIUM",
                    message=f"Goodwill is {ratio:.0%} of equity — impairment risk.",
                    metadata={"goodwill": float(gw_val), "equity": float(eq_val), "ratio": round(float(ratio), 3)},
                ))

    # --- 4. cash-quality: OCF < Net Income for 3+ years ---
    if (income_df is not None and not income_df.empty
            and cashflow_df is not None and not cashflow_df.empty):
        ni_vals = _row_values(income_df, ["Net Income", "Net Income Common Stockholders"])
        ocf_vals = _row_values(cashflow_df, [
            "Operating Cash Flow", "Total Cash From Operating Activities",
            "Cash Flow From Continuing Operating Activities",
        ])
        if ni_vals is not None and ocf_vals is not None:
            common = ni_vals.index.intersection(ocf_vals.index)
            if len(common) >= 3:
                below = sum(1 for d in common if ocf_vals[d] < ni_vals[d] and ni_vals[d] > 0)
                if below >= 3:
                    warnings.append(Warning(
                        type="cash-quality",
                        category="Cash Flow",
                        severity="MEDIUM",
                        message=f"OCF < Net Income for {below} of {len(common)} years — low earnings quality.",
                        metadata={"below_count": below, "total_years": len(common)},
                    ))

    # --- 5. anomaly: revenue or NI change > 100% YoY ---
    if income_df is not None and not income_df.empty:
        for field_name, readable in [
            ("Total Revenue", "Revenue"),
            ("Net Income", "Net Income"),
        ]:
            if field_name in income_df.index:
                vals = income_df.loc[field_name].dropna()
                if len(vals) >= 2:
                    # Columns may be descending (newest first) — compute
                    # max(new/old, old/new) - 1 for each adjacent pair
                    for j in range(len(vals) - 1):
                        v_new, v_old = float(vals.iloc[j]), float(vals.iloc[j + 1])
                        if v_old == 0 or v_new == 0:
                            continue
                        chg = max(abs(v_new / v_old), abs(v_old / v_new)) - 1
                        if chg > 1.0:
                            # Use the newer date for the label
                            date = vals.index[j]
                            yr = date.year if hasattr(date, "year") else date
                            sev = "HIGH" if chg > 3.0 else "MEDIUM"
                            warnings.append(Warning(
                                type="anomaly",
                                category="Anomaly",
                                severity=sev,
                                message=f"{readable} changed by {chg * 100:.0f}% in {yr}.",
                                metadata={"field": readable, "year": int(yr),
                                          "change_pct": round(float(chg * 100), 1)},
                            ))

    # --- 6. concentration-risk: low segment diversity ---
    # Only detectable from info dict if segment data available
    sector = info.get("sector", "")
    industry = info.get("industry", "")
    if sector and industry:
        # Flag single-product/single-geo companies (heuristic: info has no segment breakout)
        # This is a soft signal — LOW severity
        biz_summary = info.get("longBusinessSummary", "")
        if biz_summary and len(biz_summary) < 200:
            warnings.append(Warning(
                type="concentration-risk",
                category="Anomaly",
                severity="LOW",
                message="Limited business description — possible single-product concentration.",
                metadata={"sector": sector, "industry": industry},
            ))

    # Sort: HIGH > MEDIUM > LOW
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    warnings.sort(key=lambda w: severity_order.get(w.severity, 9))
    return warnings


def save_warnings_json(warnings_list: List[Warning], output_dir: str) -> str:
    """Save warnings to a JSON file and return the file path."""
    out_path = Path(output_dir) / "warnings.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = [w.to_dict() for w in warnings_list]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _latest_value(
    df: pd.DataFrame, candidate_fields: List[str],
) -> Optional[float]:
    """Return the most recent non-NaN value from the first matching row."""
    for f in candidate_fields:
        if f in df.index:
            vals = df.loc[f].dropna()
            if len(vals) > 0:
                return float(vals.iloc[0])
    return None


def _row_values(
    df: pd.DataFrame, candidate_fields: List[str],
) -> Optional[pd.Series]:
    """Return the full row (as Series) for the first matching field."""
    for f in candidate_fields:
        if f in df.index:
            return df.loc[f].dropna()
    return None
