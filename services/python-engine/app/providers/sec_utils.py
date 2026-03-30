from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def normalize_ticker(ticker: str) -> str:
    """Normalize user input into the uppercase ticker format expected internally."""
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("Ticker is required.")
    return normalized


def pad_cik(cik: str | int) -> str:
    """Convert a raw SEC CIK into the zero-padded 10-digit representation."""
    digits_only = str(cik).strip()
    if not digits_only:
        raise ValueError("CIK is required.")
    return digits_only.zfill(10)


def parse_date(value: Any) -> datetime:
    """Parse SEC date strings while treating missing values as minimal dates."""
    if not value:
        return datetime.min
    return datetime.strptime(str(value), "%Y-%m-%d")


def as_float(value: Any) -> float:
    """Convert a SEC numeric payload field into a float for derived calculations."""
    return float(value)


def latest_period_end(entries: list[dict[str, Any]]) -> str:
    """Return the latest period-end date across a list of fact entries."""
    return max(str(entry["end"]) for entry in entries if entry.get("end"))


def latest_filed(entries: list[dict[str, Any]]) -> Optional[str]:
    """Return the latest filing date across a list of fact entries."""
    filed_values = [str(entry["filed"]) for entry in entries if entry.get("filed")]
    if not filed_values:
        return None
    return max(filed_values)


def is_annual_filing(entry: dict[str, Any]) -> bool:
    """Identify annual facts using the SEC form or fiscal-period markers."""
    return entry.get("form") == "10-K" or entry.get("fp") == "FY"


def score_anchor_match(
    entry: dict[str, Any],
    anchor_fy: Any,
    anchor_fp: Any,
    anchor_form: Any,
) -> int:
    """Score how closely one fact matches the chosen anchor reporting period."""
    score = 0
    if anchor_fy is not None and entry.get("fy") == anchor_fy:
        score += 2
    if anchor_fp is not None and entry.get("fp") == anchor_fp:
        score += 2
    if anchor_form is not None and entry.get("form") == anchor_form:
        score += 1
    if is_annual_filing(entry):
        score += 1
    return score
