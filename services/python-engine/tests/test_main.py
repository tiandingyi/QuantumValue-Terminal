import asyncio

from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.models.financial_metric import FinancialMetric
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
    class FakeStore:
        def __init__(self) -> None:
            self.statuses = []

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            self.statuses.append((company.ticker, task_type, status, last_error))

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            return {
                "company_id": "company-1",
                "filing_id": "filing-1",
                "financial_metrics_id": "metrics-1",
                "form_type": filing.form_type,
                "period_end_date": filing.period_end_date,
                "accession_number": filing.accession_number,
            }

    class FakeProvider:
        def resolve_ticker(self, ticker: str) -> CompanyLookup:
            assert ticker == "NVDA"
            return CompanyLookup(
                ticker="NVDA",
                cik="0001045810",
                name="NVIDIA CORP",
            )

        def get_submissions(self, cik: str):
            assert cik == "0001045810"
            return {
                "name": "NVIDIA CORP",
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "accessionNumber": ["0001045810-26-000001"],
                        "filingDate": ["2026-02-21"],
                        "reportDate": ["2026-01-25"],
                    }
                },
            }

        def get_company_facts(self, cik: str):
            return {}

        def fetch_company_data(self, ticker: str) -> CompanyDataBundle:
            return CompanyDataBundle(
                company=self.resolve_ticker(ticker),
                submissions=self.get_submissions("0001045810"),
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

        def parse_financial_metric(self, company_facts) -> FinancialMetric:
            return FinancialMetric(
                period_end="2026-01-25",
                filed_at="2026-02-21",
                assets=111111,
                source_tags={"assets": "Assets"},
            )

        def extract_requested_financials(self, company_facts):
            return {}

    fake_store = FakeStore()
    monkeypatch.setattr(main_module, "provider_factory", FakeProvider)
    monkeypatch.setattr(main_module, "persistence_store_factory", lambda: fake_store)
    asyncio.run(main_module.finish_sync("NVDA"))

    payload = main_module.sync_state.get("NVDA")
    assert payload is not None
    assert payload.status == "SUCCESS"
    assert payload.details is not None
    assert payload.details["company_name"] == "NVIDIA CORP"
    assert payload.details["latest_assets"]["value"] == 111111
    assert payload.details["persistence"]["filing_id"] == "filing-1"
    assert fake_store.statuses == [
        ("NVDA", "SEC_SYNC", "PENDING", None),
        ("NVDA", "SEC_SYNC", "IN_PROGRESS", None),
        ("NVDA", "SCRAPE", "IN_PROGRESS", None),
        ("NVDA", "SCRAPE", "SUCCESS", None),
        ("NVDA", "PARSE", "IN_PROGRESS", None),
        ("NVDA", "PARSE", "SUCCESS", None),
        ("NVDA", "STORE", "IN_PROGRESS", None),
        ("NVDA", "STORE", "SUCCESS", None),
        ("NVDA", "SEC_SYNC", "SUCCESS", None),
    ]


def test_finish_sync_marks_failed_when_provider_errors(monkeypatch) -> None:
    class FakeStore:
        def __init__(self) -> None:
            self.statuses = []

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            self.statuses.append((company.ticker, task_type, status, last_error))

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            raise AssertionError("persist_filing_bundle should not be called on failed sync")

    class FailingProvider:
        def resolve_ticker(self, ticker: str) -> CompanyLookup:
            return CompanyLookup(ticker=ticker, cik="0000000000", name="Bad Corp")

        def get_submissions(self, cik: str):
            raise ValueError("Ticker BAD was not found in SEC company_tickers.json.")

        def get_company_facts(self, cik: str):
            raise AssertionError("get_company_facts should not be called")

        def fetch_company_data(self, ticker: str) -> CompanyDataBundle:
            raise ValueError("Ticker BAD was not found in SEC company_tickers.json.")

    fake_store = FakeStore()
    monkeypatch.setattr(main_module, "provider_factory", FailingProvider)
    monkeypatch.setattr(main_module, "persistence_store_factory", lambda: fake_store)
    asyncio.run(main_module.finish_sync("BAD"))

    payload = main_module.sync_state.get("BAD")
    assert payload is not None
    assert payload.status == "FAILED"
    assert "Ticker BAD" in payload.message
    assert fake_store.statuses[0] == ("BAD", "SEC_SYNC", "PENDING", None)
    assert fake_store.statuses[1] == ("BAD", "SEC_SYNC", "IN_PROGRESS", None)
    assert fake_store.statuses[2] == ("BAD", "SCRAPE", "IN_PROGRESS", None)
    assert fake_store.statuses[-2][1] == "SCRAPE"
    assert fake_store.statuses[-2][2] == "FAILURE"
    assert "Traceback" in fake_store.statuses[-2][3]
    assert "Ticker BAD was not found" in fake_store.statuses[-2][3]
    assert fake_store.statuses[-1][1] == "SEC_SYNC"
    assert fake_store.statuses[-1][2] == "FAILURE"


def test_finish_sync_marks_store_failure_with_traceback(monkeypatch) -> None:
    class FakeStore:
        def __init__(self) -> None:
            self.statuses = []

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            self.statuses.append((company.ticker, task_type, status, last_error))

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            raise RuntimeError("database write exploded")

    class FakeProvider:
        def resolve_ticker(self, ticker: str) -> CompanyLookup:
            return CompanyLookup(ticker="MSFT", cik="0000789019", name="MICROSOFT CORP")

        def get_submissions(self, cik: str):
            return {
                "name": "MICROSOFT CORP",
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "accessionNumber": ["0000789019-26-000001"],
                        "filingDate": ["2026-07-30"],
                        "reportDate": ["2026-06-30"],
                    }
                },
            }

        def get_company_facts(self, cik: str):
            return {}

        def extract_latest_metric(self, company_facts, metric_name: str):
            return {
                "val": 222222,
                "unit": "USD",
                "end": "2026-06-30",
                "filed": "2026-07-30",
                "form": "10-K",
            }

        def parse_financial_metric(self, company_facts) -> FinancialMetric:
            return FinancialMetric(
                period_end="2026-06-30",
                filed_at="2026-07-30",
                revenue=1,
                source_tags={"revenue": "Revenues"},
            )

        def extract_requested_financials(self, company_facts):
            return {}

    fake_store = FakeStore()
    monkeypatch.setattr(main_module, "provider_factory", FakeProvider)
    monkeypatch.setattr(main_module, "persistence_store_factory", lambda: fake_store)
    asyncio.run(main_module.finish_sync("MSFT"))

    payload = main_module.sync_state.get("MSFT")
    assert payload is not None
    assert payload.status == "FAILED"
    assert "database write exploded" in payload.message
    assert fake_store.statuses[0] == ("MSFT", "SEC_SYNC", "PENDING", None)
    assert fake_store.statuses[1] == ("MSFT", "SEC_SYNC", "IN_PROGRESS", None)
    assert fake_store.statuses[2] == ("MSFT", "SCRAPE", "IN_PROGRESS", None)
    assert fake_store.statuses[3] == ("MSFT", "SCRAPE", "SUCCESS", None)
    assert fake_store.statuses[4] == ("MSFT", "PARSE", "IN_PROGRESS", None)
    assert fake_store.statuses[5] == ("MSFT", "PARSE", "SUCCESS", None)
    assert fake_store.statuses[6] == ("MSFT", "STORE", "IN_PROGRESS", None)
    assert fake_store.statuses[-2][1] == "STORE"
    assert fake_store.statuses[-2][2] == "FAILURE"
    assert "Traceback" in fake_store.statuses[-2][3]
    assert "database write exploded" in fake_store.statuses[-2][3]
    assert fake_store.statuses[-1][1] == "SEC_SYNC"
    assert fake_store.statuses[-1][2] == "FAILURE"
