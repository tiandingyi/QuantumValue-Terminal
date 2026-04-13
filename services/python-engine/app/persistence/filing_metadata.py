from __future__ import annotations

from typing import Any

from app.persistence.types import FilingMetadata


SUPPORTED_FORMS = {"10-K", "10-Q"}


def extract_latest_supported_filing(submissions: dict[str, Any], cik: str) -> FilingMetadata:
    """Extract the latest 10-K or 10-Q filing metadata from the SEC submissions payload."""
    filings = extract_supported_filings(submissions, cik, limit=1)
    if not filings:
        raise ValueError("No supported 10-K or 10-Q filing metadata was found in SEC submissions.")
    return filings[0]


def extract_supported_filings(
    submissions: dict[str, Any],
    cik: str,
    limit: int | None = 20,
) -> list[FilingMetadata]:
    """Extract 10-K and 10-Q filing metadata from SEC submissions-shaped payloads.

    The main SEC submissions endpoint nests arrays under ``filings.recent``.
    Archived submissions files listed in ``filings.files`` use the same arrays at
    the top level. This helper accepts both shapes.
    """
    payload = _filing_array_payload(submissions)
    forms = payload.get("form", [])
    accession_numbers = payload.get("accessionNumber", [])
    filed_dates = payload.get("filingDate", [])
    report_dates = payload.get("reportDate", [])
    filings: list[FilingMetadata] = []

    for index, form_type in enumerate(forms):
        if form_type not in SUPPORTED_FORMS:
            continue
        if index >= len(accession_numbers) or index >= len(filed_dates):
            continue

        period_end_date = (
            report_dates[index]
            if index < len(report_dates) and report_dates[index]
            else filed_dates[index]
        )
        filings.append(
            FilingMetadata(
                cik=cik,
                form_type=form_type,
                period_end_date=period_end_date,
                filed_at=filed_dates[index],
                accession_number=accession_numbers[index],
            )
        )
        if limit is not None and len(filings) >= limit:
            break

    return filings


def extract_all_supported_filings(
    submissions: dict[str, Any],
    archived_submissions: list[dict[str, Any]],
    cik: str,
) -> list[FilingMetadata]:
    """Merge all supported filing metadata from recent and archived submissions."""
    filings = extract_supported_filings(submissions, cik, limit=None)
    for archived_submission in archived_submissions:
        filings.extend(extract_supported_filings(archived_submission, cik, limit=None))

    return _dedupe_filings(filings)


def _filing_array_payload(submissions: dict[str, Any]) -> dict[str, Any]:
    return submissions.get("filings", {}).get("recent") or submissions


def _dedupe_filings(filings: list[FilingMetadata]) -> list[FilingMetadata]:
    seen: set[tuple[str, ...]] = set()
    unique_filings: list[FilingMetadata] = []

    for filing in filings:
        key = (
            (filing.accession_number,)
            if filing.accession_number
            else (
                filing.cik,
                filing.form_type,
                filing.period_end_date,
            )
        )
        if key in seen:
            continue
        seen.add(key)
        unique_filings.append(filing)

    return unique_filings
