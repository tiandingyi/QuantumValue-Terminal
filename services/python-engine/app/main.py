import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from app.calculations.derived_metrics import calculate_derived_metrics
from app.calculations.valuation import calculate_valuation_section
from app.parsers.financial_metric_parser import FinancialMetricMappingError
from app.persistence.factory import build_persistence_store
from app.persistence.filing_metadata import extract_all_supported_filings
from app.providers.sec_types import CompanyDataBundle
from app.providers.us_provider import USProvider


logger = logging.getLogger(__name__)
SYNC_TASK_TYPE = "SEC_SYNC"
SCRAPE_TASK_TYPE = "SCRAPE"
PARSE_TASK_TYPE = "PARSE"
STORE_TASK_TYPE = "STORE"
HISTORICAL_REQUIRED_FIELDS = ["revenue", "net_income"]
PARSE_ERROR_SAMPLE_LIMIT = 10


class SyncResponse(BaseModel):
    ticker: str
    status: str
    message: str
    updated_at: str
    details: Optional[dict[str, Any]] = None


class SyncState:
    def __init__(self) -> None:
        self._statuses: dict[str, SyncResponse] = {}

    def get(self, ticker: str) -> Optional[SyncResponse]:
        return self._statuses.get(ticker)

    def set(
        self,
        ticker: str,
        sync_status: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> SyncResponse:
        payload = SyncResponse(
            ticker=ticker,
            status=sync_status,
            message=message,
            updated_at=datetime.now(timezone.utc).isoformat(),
            details=details,
        )
        self._statuses[ticker] = payload
        return payload


app = FastAPI(title="QuantumValue Engine", version="0.1.0")
sync_state = SyncState()
provider_factory = USProvider
persistence_store_factory = lambda: build_persistence_store(os.getenv("DATABASE_URL"))


async def finish_sync(ticker: str) -> None:
    await asyncio.sleep(0)
    provider = provider_factory()
    company = None
    store = None
    current_stage: Optional[str] = None

    try:
        store = persistence_store_factory()
        company = await asyncio.to_thread(provider.resolve_ticker, ticker)
        if store is not None:
            await asyncio.to_thread(store.upsert_sync_status, company, SYNC_TASK_TYPE, "PENDING", None)
            await asyncio.to_thread(store.upsert_sync_status, company, SYNC_TASK_TYPE, "IN_PROGRESS", None)
            await asyncio.to_thread(store.upsert_sync_status, company, SCRAPE_TASK_TYPE, "IN_PROGRESS", None)

        current_stage = SCRAPE_TASK_TYPE
        submissions = await asyncio.to_thread(provider.get_submissions, company.cik)
        archived_submissions = []
        archive_errors = []
        for archive_name in _submission_archive_names(submissions):
            try:
                archived_submissions.append(await asyncio.to_thread(provider.get_submission_file, archive_name))
            except (requests.RequestException, ValueError) as exc:
                logger.warning("Failed to fetch SEC submissions archive %s for %s: %s", archive_name, ticker, exc)
                archive_errors.append({"file": archive_name, "error": str(exc)})
        company_facts = await asyncio.to_thread(provider.get_company_facts, company.cik)
        bundle = CompanyDataBundle(company=company, submissions=submissions, company_facts=company_facts)
        if store is not None:
            await asyncio.to_thread(store.upsert_sync_status, company, SCRAPE_TASK_TYPE, "SUCCESS", None)
            await asyncio.to_thread(store.upsert_sync_status, company, PARSE_TASK_TYPE, "IN_PROGRESS", None)

        current_stage = PARSE_TASK_TYPE
        latest_assets = provider.extract_latest_metric(bundle.company_facts, "Assets")
        filing_metadatas = extract_all_supported_filings(
            bundle.submissions,
            archived_submissions,
            bundle.company.cik,
        )
        if not filing_metadatas:
            raise ValueError("No supported 10-K or 10-Q filing metadata was found in SEC submissions.")

        parsed_base_bundles = []
        parse_errors = []
        parse_exceptions = []
        for filing_metadata in sorted(filing_metadatas, key=lambda item: item.period_end_date):
            try:
                base_metrics = provider.parse_financial_metric(
                    bundle.company_facts,
                    ticker=bundle.company.ticker,
                    cik=bundle.company.cik,
                    required_fields=HISTORICAL_REQUIRED_FIELDS,
                    anchor={"end": filing_metadata.period_end_date, "form": filing_metadata.form_type},
                )
            except (FinancialMetricMappingError, ValueError) as exc:
                parse_exceptions.append(exc)
                logger.warning(
                    "Skipping unparseable SEC filing %s %s %s for %s: %s",
                    filing_metadata.form_type,
                    filing_metadata.period_end_date,
                    filing_metadata.accession_number,
                    ticker,
                    exc,
                )
                parse_errors.append(
                    {
                        "form_type": filing_metadata.form_type,
                        "period_end_date": filing_metadata.period_end_date,
                        "accession_number": filing_metadata.accession_number,
                        "error": str(exc),
                    }
                )
                continue
            parsed_base_bundles.append((filing_metadata, base_metrics))

        if not parsed_base_bundles:
            if parse_exceptions:
                raise parse_exceptions[0]
            raise ValueError("No parseable supported 10-K or 10-Q filing metrics were found in SEC companyfacts.")

        pruned_filing_count = 0
        if store is not None and hasattr(store, "prune_company_filings"):
            keep_filing_keys = {
                (filing_metadata.form_type, filing_metadata.period_end_date)
                for filing_metadata, _ in parsed_base_bundles
            }
            pruned_filing_count = await asyncio.to_thread(
                store.prune_company_filings,
                bundle.company,
                keep_filing_keys,
            )

        historical_metrics_by_period: dict[str, Any] = {}
        if store is not None:
            existing_history = await asyncio.to_thread(store.list_base_metric_history, bundle.company)
            historical_metrics_by_period.update(
                {metric.period_end: metric for metric in existing_history if metric.period_end}
            )

        parsed_filing_bundles = []
        for filing_metadata, base_metrics in parsed_base_bundles:
            historical_metrics_by_period[base_metrics.period_end or filing_metadata.period_end_date] = base_metrics
            historical_base_metrics = [
                metric
                for _, metric in sorted(
                    historical_metrics_by_period.items(),
                    key=lambda item: item[0],
                )
            ]
            derived_metrics = calculate_derived_metrics(base_metrics, historical_base_metrics)
            derived_metrics["valuation"] = calculate_valuation_section(base_metrics, historical_base_metrics)
            parsed_filing_bundles.append((filing_metadata, base_metrics, derived_metrics))

        latest_filing_metadata, latest_base_metrics, _ = max(
            parsed_filing_bundles,
            key=lambda item: item[0].period_end_date,
        )
        persistence_details: Optional[dict[str, Any]] = None

        if store is not None:
            await asyncio.to_thread(store.upsert_sync_status, company, PARSE_TASK_TYPE, "SUCCESS", None)
            await asyncio.to_thread(store.upsert_sync_status, company, STORE_TASK_TYPE, "IN_PROGRESS", None)
            current_stage = STORE_TASK_TYPE
            persisted_filings = []
            for filing_metadata, base_metrics, derived_metrics in parsed_filing_bundles:
                persisted_filings.append(
                    await asyncio.to_thread(
                        store.persist_filing_bundle,
                        bundle.company,
                        filing_metadata,
                        base_metrics,
                        derived_metrics,
                    )
                )
            persistence_details = {
                "status": "stored",
                "filing_count": len(persisted_filings),
                "pruned_filing_count": pruned_filing_count,
                "earliest_period_end": min(details["period_end_date"] for details in persisted_filings),
                "latest_filing": next(
                    (
                        details
                        for details in reversed(persisted_filings)
                        if details["period_end_date"] == latest_filing_metadata.period_end_date
                    ),
                    persisted_filings[-1],
                ),
            }
            await asyncio.to_thread(store.upsert_sync_status, bundle.company, STORE_TASK_TYPE, "SUCCESS", None)
            await asyncio.to_thread(store.upsert_sync_status, bundle.company, SYNC_TASK_TYPE, "SUCCESS", None)

        sync_state.set(
            ticker,
            "SUCCESS",
            f"Fetched SEC submissions and company facts for {bundle.company.name}.",
            details={
                "company_name": bundle.company.name,
                "cik": bundle.company.cik,
                "persistence": persistence_details or {"status": "skipped"},
                "archive_file_count": len(archived_submissions),
                "archive_error_count": len(archive_errors),
                "archive_errors": archive_errors[:PARSE_ERROR_SAMPLE_LIMIT],
                "discovered_filing_count": len(filing_metadatas),
                "parsed_filing_count": len(parsed_filing_bundles),
                "skipped_filing_count": len(parse_errors),
                "parse_errors": parse_errors[:PARSE_ERROR_SAMPLE_LIMIT],
                "earliest_period_end": min(item[0].period_end_date for item in parsed_filing_bundles),
                "latest_period_end": latest_filing_metadata.period_end_date,
                "latest_assets": {
                    "value": latest_assets["val"],
                    "unit": latest_assets["unit"],
                    "end": latest_assets["end"],
                    "filed": latest_assets.get("filed"),
                    "form": latest_assets.get("form"),
                },
            },
        )
    except Exception as exc:
        error_details = traceback.format_exc()
        if store is None:
            try:
                store = persistence_store_factory()
            except Exception:
                store = None
        if store is not None and company is not None:
            failed_stage = current_stage or SYNC_TASK_TYPE
            await asyncio.to_thread(store.upsert_sync_status, company, failed_stage, "FAILURE", error_details)
            await asyncio.to_thread(store.upsert_sync_status, company, SYNC_TASK_TYPE, "FAILURE", error_details)
        logger.exception("SEC EDGAR sync failed for %s", ticker)
        sync_state.set(
            ticker,
            "FAILED",
            f"SEC EDGAR fetch failed for {ticker}: {exc}",
        )


def _submission_archive_names(submissions: dict[str, Any]) -> list[str]:
    files = submissions.get("filings", {}).get("files", [])
    archive_names = []
    for file_info in files:
        if not isinstance(file_info, dict):
            continue
        archive_name = file_info.get("name")
        if archive_name:
            archive_names.append(archive_name)
    return archive_names


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {
        "service": "engine-py",
        "status": "ok",
        "database_url": os.getenv("DATABASE_URL", "not-configured"),
    }


@app.post("/sync/{ticker}", response_model=SyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(ticker: str) -> SyncResponse:
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ticker is required.")

    payload = sync_state.set(
        normalized_ticker,
        "IN_PROGRESS",
        f"SEC EDGAR sync started for {normalized_ticker}. Fetching submissions and company facts.",
    )
    asyncio.create_task(finish_sync(normalized_ticker))
    return payload


@app.get("/status/{ticker}", response_model=SyncResponse)
async def get_status(ticker: str) -> SyncResponse:
    normalized_ticker = ticker.strip().upper()
    payload = sync_state.get(normalized_ticker)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sync job found for {normalized_ticker}.",
        )

    if payload.status == "IN_PROGRESS":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=payload.model_dump(),
        )

    return payload
