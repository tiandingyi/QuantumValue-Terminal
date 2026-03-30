import asyncio
import os
from typing import Any
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from app.providers.us_provider import USProvider


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


async def finish_sync(ticker: str) -> None:
    await asyncio.sleep(0)
    provider = provider_factory()

    try:
        bundle = await asyncio.to_thread(provider.fetch_company_data, ticker)
        latest_assets = provider.extract_latest_metric(bundle.company_facts, "Assets")
        sync_state.set(
            ticker,
            "SUCCESS",
            f"Fetched SEC submissions and company facts for {bundle.company.name}.",
            details={
                "company_name": bundle.company.name,
                "cik": bundle.company.cik,
                "latest_assets": {
                    "value": latest_assets["val"],
                    "unit": latest_assets["unit"],
                    "end": latest_assets["end"],
                    "filed": latest_assets.get("filed"),
                    "form": latest_assets.get("form"),
                },
            },
        )
    except (requests.RequestException, ValueError) as exc:
        sync_state.set(
            ticker,
            "FAILED",
            f"SEC EDGAR fetch failed for {ticker}: {exc}",
        )


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
