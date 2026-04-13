import asyncio

from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.models.financial_metric import FinancialMetric
from app.parsers.financial_metric_parser import FinancialMetricMappingError
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
            self.persisted_derived_metrics = None

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            self.statuses.append((company.ticker, task_type, status, last_error))

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            self.persisted_derived_metrics = derived_metrics
            return {
                "company_id": "company-1",
                "filing_id": "filing-1",
                "financial_metrics_id": "metrics-1",
                "form_type": filing.form_type,
                "period_end_date": filing.period_end_date,
                "accession_number": filing.accession_number,
            }

        def list_base_metric_history(self, company):
            return [
                FinancialMetric(period_end="2016-01-25", revenue=100, net_income=100),
            ]

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

        def parse_financial_metric(self, company_facts, **kwargs) -> FinancialMetric:
            return FinancialMetric(
                period_end="2026-01-25",
                filed_at="2026-02-21",
                revenue=2000,
                gross_profit=800,
                net_income=300,
                operating_cash_flow=420,
                capex=-90,
                depreciation_and_amortization=40,
                shareholders_equity=1500,
                assets=111111,
                source_tags={
                    "assets": "Assets",
                    "revenue": "Revenues",
                    "gross_profit": "GrossProfit",
                    "net_income": "NetIncomeLoss",
                    "operating_cash_flow": "NetCashProvidedByUsedInOperatingActivities",
                    "capex": "PaymentsToAcquirePropertyPlantAndEquipment",
                    "depreciation_and_amortization": "DepreciationAndAmortization",
                    "shareholders_equity": "StockholdersEquity",
                },
            )

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
    assert payload.details["persistence"]["latest_filing"]["filing_id"] == "filing-1"
    assert payload.details["persistence"]["filing_count"] == 1
    assert fake_store.persisted_derived_metrics is not None
    assert fake_store.persisted_derived_metrics["free_cash_flow"].value == 330
    assert fake_store.persisted_derived_metrics["owner_earnings"].value == 250
    assert fake_store.persisted_derived_metrics["roe"].value == 0.2
    assert fake_store.persisted_derived_metrics["gross_margin"].value == 0.4
    assert round(fake_store.persisted_derived_metrics["revenue_10y_cagr"].value, 3) == round(
        (2000 / 100) ** (1 / 10) - 1,
        3,
    )
    assert fake_store.persisted_derived_metrics["valuation"]["status"] == "skipped"
    assert "current_static_pe" in fake_store.persisted_derived_metrics["valuation"]["missing_inputs"]
    assert "net_income_10y_history" not in fake_store.persisted_derived_metrics["valuation"]["missing_inputs"]
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


def test_finish_sync_fetches_archived_submission_history_and_skips_unparseable_period(monkeypatch) -> None:
    class FakeStore:
        def __init__(self) -> None:
            self.persisted_periods = []
            self.keep_filing_keys = None

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            return None

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            self.persisted_periods.append(filing.period_end_date)
            return {
                "company_id": "company-1",
                "filing_id": f"filing-{filing.period_end_date}",
                "financial_metrics_id": f"metrics-{filing.period_end_date}",
                "form_type": filing.form_type,
                "period_end_date": filing.period_end_date,
                "accession_number": filing.accession_number,
            }

        def list_base_metric_history(self, company):
            return []

        def prune_company_filings(self, company, keep_filing_keys):
            self.keep_filing_keys = keep_filing_keys
            return 2

    class FakeProvider:
        def resolve_ticker(self, ticker: str) -> CompanyLookup:
            return CompanyLookup(ticker="HIST", cik="0000000003", name="HISTORY CORP")

        def get_submissions(self, cik: str):
            return {
                "filings": {
                    "recent": {
                        "form": ["10-K", "10-Q"],
                        "accessionNumber": ["recent-k", "recent-q"],
                        "filingDate": ["2026-02-20", "2025-11-20"],
                        "reportDate": ["2025-12-31", "2025-09-30"],
                    },
                    "files": [{"name": "CIK0000000003-submissions-001.json"}],
                },
            }

        def get_submission_file(self, file_name: str):
            assert file_name == "CIK0000000003-submissions-001.json"
            return {
                "form": ["10-K", "8-K", "10-K"],
                "accessionNumber": ["old-k", "old-8k", "too-old-k"],
                "filingDate": ["2018-02-20", "2017-11-20", "2008-02-20"],
                "reportDate": ["2017-12-31", "2017-09-30", "2007-12-31"],
            }

        def get_company_facts(self, cik: str):
            return {}

        def extract_latest_metric(self, company_facts, metric_name: str):
            return {
                "val": 123,
                "unit": "USD",
                "end": "2025-12-31",
                "filed": "2026-02-20",
                "form": "10-K",
            }

        def parse_financial_metric(self, company_facts, **kwargs) -> FinancialMetric:
            anchor = kwargs["anchor"]
            if anchor["end"] == "2007-12-31":
                raise FinancialMetricMappingError(
                    field_name="revenue",
                    candidate_tags=["Revenues"],
                    ticker=kwargs.get("ticker"),
                    cik=kwargs.get("cik"),
                    period_context=anchor,
                )
            return FinancialMetric(
                period_end=anchor["end"],
                filed_at="2026-02-20",
                revenue=1000,
                net_income=100,
                operating_cash_flow=120,
                capex=-20,
                source_tags={"revenue": "Revenues", "net_income": "NetIncomeLoss"},
            )

    fake_store = FakeStore()
    monkeypatch.setattr(main_module, "provider_factory", FakeProvider)
    monkeypatch.setattr(main_module, "persistence_store_factory", lambda: fake_store)
    asyncio.run(main_module.finish_sync("HIST"))

    payload = main_module.sync_state.get("HIST")
    assert payload is not None
    assert payload.status == "SUCCESS"
    assert payload.details is not None
    assert payload.details["archive_file_count"] == 1
    assert payload.details["discovered_filing_count"] == 4
    assert payload.details["parsed_filing_count"] == 3
    assert payload.details["skipped_filing_count"] == 1
    assert payload.details["earliest_period_end"] == "2017-12-31"
    assert payload.details["latest_period_end"] == "2025-12-31"
    assert payload.details["persistence"]["filing_count"] == 3
    assert payload.details["persistence"]["pruned_filing_count"] == 2
    assert payload.details["persistence"]["earliest_period_end"] == "2017-12-31"
    assert fake_store.persisted_periods == ["2017-12-31", "2025-09-30", "2025-12-31"]
    assert fake_store.keep_filing_keys == {
        ("10-K", "2017-12-31"),
        ("10-Q", "2025-09-30"),
        ("10-K", "2025-12-31"),
    }


def test_finish_sync_marks_failed_when_provider_errors(monkeypatch) -> None:
    class FakeStore:
        def __init__(self) -> None:
            self.statuses = []

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            self.statuses.append((company.ticker, task_type, status, last_error))

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            raise AssertionError("persist_filing_bundle should not be called on failed sync")

        def list_base_metric_history(self, company):
            raise AssertionError("list_base_metric_history should not be called on failed scrape")

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

        def list_base_metric_history(self, company):
            return []

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

        def parse_financial_metric(self, company_facts, **kwargs) -> FinancialMetric:
            return FinancialMetric(
                period_end="2026-06-30",
                filed_at="2026-07-30",
                revenue=1,
                source_tags={"revenue": "Revenues"},
            )

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


def test_finish_sync_blocks_persistence_when_required_mapping_fails(monkeypatch) -> None:
    class FakeStore:
        def __init__(self) -> None:
            self.statuses = []
            self.persist_called = False

        def upsert_sync_status(self, company, task_type: str, status: str, last_error=None) -> None:
            self.statuses.append((company.ticker, task_type, status, last_error))

        def persist_filing_bundle(self, company, filing, base_metrics, derived_metrics):
            self.persist_called = True
            raise AssertionError("persist_filing_bundle should not be called when parsing fails")

        def list_base_metric_history(self, company):
            raise AssertionError("list_base_metric_history should not be called when parsing fails")

    class FakeProvider:
        def resolve_ticker(self, ticker: str) -> CompanyLookup:
            return CompanyLookup(ticker="GAP", cik="0000000002", name="GAP CORP")

        def get_submissions(self, cik: str):
            return {
                "name": "GAP CORP",
                "filings": {
                    "recent": {
                        "form": ["10-K"],
                        "accessionNumber": ["0000000002-26-000001"],
                        "filingDate": ["2026-02-20"],
                        "reportDate": ["2025-12-31"],
                    }
                },
            }

        def get_company_facts(self, cik: str):
            return {"facts": {"us-gaap": {}}}

        def extract_latest_metric(self, company_facts, metric_name: str):
            return {
                "val": 333333,
                "unit": "USD",
                "end": "2025-12-31",
                "filed": "2026-02-20",
                "form": "10-K",
            }

        def parse_financial_metric(self, company_facts, **kwargs) -> FinancialMetric:
            raise FinancialMetricMappingError(
                field_name="revenue",
                candidate_tags=["Revenues", "SalesRevenueNet"],
                ticker=kwargs.get("ticker"),
                cik=kwargs.get("cik"),
                period_context={"end": "2025-12-31", "form": "10-K"},
            )

    fake_store = FakeStore()
    monkeypatch.setattr(main_module, "provider_factory", FakeProvider)
    monkeypatch.setattr(main_module, "persistence_store_factory", lambda: fake_store)
    asyncio.run(main_module.finish_sync("GAP"))

    payload = main_module.sync_state.get("GAP")
    assert payload is not None
    assert payload.status == "FAILED"
    assert "revenue" in payload.message
    assert fake_store.persist_called is False
    assert fake_store.statuses[0] == ("GAP", "SEC_SYNC", "PENDING", None)
    assert fake_store.statuses[1] == ("GAP", "SEC_SYNC", "IN_PROGRESS", None)
    assert fake_store.statuses[2] == ("GAP", "SCRAPE", "IN_PROGRESS", None)
    assert fake_store.statuses[3] == ("GAP", "SCRAPE", "SUCCESS", None)
    assert fake_store.statuses[4] == ("GAP", "PARSE", "IN_PROGRESS", None)
    assert fake_store.statuses[-2][1] == "PARSE"
    assert fake_store.statuses[-2][2] == "FAILURE"
    assert "FinancialMetricMappingError" in fake_store.statuses[-2][3]
    assert "revenue" in fake_store.statuses[-2][3]
    assert "Revenues" in fake_store.statuses[-2][3]
    assert "0000000002" in fake_store.statuses[-2][3]
    assert fake_store.statuses[-1][1] == "SEC_SYNC"
    assert fake_store.statuses[-1][2] == "FAILURE"
