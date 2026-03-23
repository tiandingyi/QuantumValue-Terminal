import asyncio
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel


class SyncResponse(BaseModel):
    ticker: str
    status: str
    message: str
    updated_at: str


class SyncState:
    def __init__(self) -> None:
        self._statuses: dict[str, SyncResponse] = {}

    def get(self, ticker: str) -> SyncResponse | None:
        return self._statuses.get(ticker)

    def set(self, ticker: str, sync_status: str, message: str) -> SyncResponse:
        payload = SyncResponse(
            ticker=ticker,
            status=sync_status,
            message=message,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._statuses[ticker] = payload
        return payload


app = FastAPI(title="QuantumValue Engine", version="0.1.0")
sync_state = SyncState()


async def finish_sync(ticker: str) -> None:
    await asyncio.sleep(3)
    sync_state.set(
        ticker,
        "SUCCESS",
        f"Mock filing sync completed for {ticker}. Ready for the Go gateway to fetch financials.",
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
        f"Mock sync started for {normalized_ticker}. Mining filings in the Python engine.",
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
