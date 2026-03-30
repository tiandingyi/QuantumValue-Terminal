import asyncio

from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.providers.us_provider import CompanyDataBundle, CompanyLookup


client = TestClient(app)


def test_healthz() -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "engine-py"
    assert payload["status"] == "ok"


def test_sync_flow() -> None:
    response = client.post("/sync/AAPL")

    assert response.status_code == 202
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert payload["status"] == "IN_PROGRESS"


def test_finish_sync_populates_success_details(monkeypatch) -> None:
    class FakeProvider:
        def fetch_company_data(self, ticker: str) -> CompanyDataBundle:
            assert ticker == "NVDA"
            return CompanyDataBundle(
                company=CompanyLookup(
                    ticker="NVDA",
                    cik="0001045810",
                    name="NVIDIA CORP",
                ),
                submissions={"name": "NVIDIA CORP"},
                company_facts={},
            )

        def extract_latest_metric(self, company_facts, metric_name: str):
            assert metric_name == "Assets"
            return {
                "val": 111111,
                "unit": "USD",
                "end": "2025-01-26",
                "filed": "2025-02-21",
                "form": "10-K",
            }

    monkeypatch.setattr(main_module, "provider_factory", FakeProvider)
    asyncio.run(main_module.finish_sync("NVDA"))

    payload = main_module.sync_state.get("NVDA")
    assert payload is not None
    assert payload.status == "SUCCESS"
    assert payload.details is not None
    assert payload.details["company_name"] == "NVIDIA CORP"
    assert payload.details["latest_assets"]["value"] == 111111


def test_finish_sync_marks_failed_when_provider_errors(monkeypatch) -> None:
    class FailingProvider:
        def fetch_company_data(self, ticker: str) -> CompanyDataBundle:
            raise ValueError("Ticker BAD was not found in SEC company_tickers.json.")

    monkeypatch.setattr(main_module, "provider_factory", FailingProvider)
    asyncio.run(main_module.finish_sync("BAD"))

    payload = main_module.sync_state.get("BAD")
    assert payload is not None
    assert payload.status == "FAILED"
    assert "Ticker BAD" in payload.message
