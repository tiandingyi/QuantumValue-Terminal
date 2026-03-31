from __future__ import annotations

from typing import Any

from app.persistence.types import FilingMetadata


SUPPORTED_FORMS = {"10-K", "10-Q"}


def extract_latest_supported_filing(submissions: dict[str, Any], cik: str) -> FilingMetadata:
    """Extract the latest 10-K or 10-Q filing metadata from the SEC submissions payload."""
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filed_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])

    for index, form_type in enumerate(forms):
        if form_type not in SUPPORTED_FORMS:
            continue

        period_end_date = report_dates[index] if index < len(report_dates) and report_dates[index] else filed_dates[index]
        return FilingMetadata(
            cik=cik,
            form_type=form_type,
            period_end_date=period_end_date,
            filed_at=filed_dates[index],
            accession_number=accession_numbers[index],
        )

    raise ValueError("No supported 10-K or 10-Q filing metadata was found in SEC submissions.")
