from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilingMetadata:
    """Normalized filing metadata extracted from the SEC submissions payload."""

    cik: str
    form_type: str
    period_end_date: str
    filed_at: str
    accession_number: str
