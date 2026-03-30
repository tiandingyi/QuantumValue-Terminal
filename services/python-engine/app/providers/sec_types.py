from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class CompanyLookup:
    """Resolved company identity returned from the SEC ticker mapping file."""

    ticker: str
    cik: str
    name: str


@dataclass(frozen=True)
class CompanyDataBundle:
    """Combined SEC payloads used by higher-level sync and validation flows."""

    company: CompanyLookup
    submissions: dict[str, Any]
    company_facts: dict[str, Any]


@dataclass(frozen=True)
class DerivedMetric:
    """A normalized metric result with provenance back to the SEC source tags."""

    name: str
    value: float
    unit: str
    end: str
    filed: Optional[str]
    source: str
