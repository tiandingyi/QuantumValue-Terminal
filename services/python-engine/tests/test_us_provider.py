import requests

from app.providers.us_provider import SEC_TICKER_MAP_URL, USProvider, pad_cik


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None, url="https://example.test"):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error for {self.url}", response=self)
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def get(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        response = self._responses[url]
        if isinstance(response, list):
            next_response = response.pop(0)
            return next_response
        return response


def test_pad_cik_zero_fills_values() -> None:
    assert pad_cik("320193") == "0000320193"
    assert pad_cik(1045810) == "0001045810"


def test_fetch_company_data_uses_ticker_mapping_and_sec_headers() -> None:
    session = FakeSession(
        {
            SEC_TICKER_MAP_URL: FakeResponse({
                "0": {"ticker": "NVDA", "cik_str": 1045810, "title": "NVIDIA CORP"},
            }),
            "https://data.sec.gov/submissions/CIK0001045810.json": FakeResponse({
                "name": "NVIDIA CORP",
            }),
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json": FakeResponse({
                "facts": {},
            }),
        }
    )
    sleeps = []
    ticks = iter([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    provider = USProvider(
        session=session,
        sleep_fn=lambda seconds: sleeps.append(round(seconds, 2)),
        clock_fn=lambda: next(ticks),
    )

    bundle = provider.fetch_company_data("nvda")

    assert bundle.company.ticker == "NVDA"
    assert bundle.company.cik == "0001045810"
    assert bundle.company.name == "NVIDIA CORP"
    assert bundle.submissions["name"] == "NVIDIA CORP"
    assert len(session.calls) == 3
    assert sleeps == [0.15, 0.15]
    for call in session.calls:
        assert call["headers"]["User-Agent"] == "Dingyi Quant Research data-ops@dingyi-analytics.net"
        assert call["headers"]["Accept-Encoding"] == "gzip, deflate"


def test_extract_latest_metric_returns_latest_end_date() -> None:
    provider = USProvider(session=FakeSession({}))
    latest = provider.extract_latest_metric(
        {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [
                                {"end": "2024-01-28", "filed": "2024-02-21", "val": 65728000000},
                                {"end": "2025-01-26", "filed": "2025-02-20", "val": 80945000000},
                            ]
                        }
                    }
                }
            }
        },
        "Assets",
    )

    assert latest["val"] == 80945000000
    assert latest["end"] == "2025-01-26"
    assert latest["unit"] == "USD"


def test_extract_requested_financials_derives_requested_metrics() -> None:
    provider = USProvider(session=FakeSession({}))
    metrics = provider.extract_requested_financials(
        {
            "facts": {
                "us-gaap": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 130500}]}
                    },
                    "NetIncomeLoss": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 72880}]}
                    },
                    "OperatingIncomeLoss": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 81453}]}
                    },
                    "InterestExpense": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 250}]}
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 78900}]}
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": -3200}]}
                    },
                    "StockholdersEquity": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 110000}]}
                    },
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 8000}]}
                    },
                    "LongTermDebt": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 12000}]}
                    },
                    "ShortTermBorrowings": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 3000}]}
                    },
                    "GrossProfit": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 97500}]}
                    },
                    "IncomeTaxExpenseBenefit": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 8600}]}
                    },
                    "IncomeBeforeTaxExpenseBenefit": {
                        "units": {"USD": [{"end": "2025-01-26", "filed": "2025-02-20", "val": 81453}]}
                    },
                }
            }
        }
    )

    assert metrics["fcf"].value == 75700
    assert metrics["net_income"].value == 72880
    assert round(metrics["nopat"].value, 2) == round(81453 * (1 - 8600 / 81453), 2)
    assert metrics["invested_capital"].value == 117000
    assert round(metrics["gross_margin"].value, 4) == round(97500 / 130500, 4)
    assert metrics["ebit"].value == 81453
    assert metrics["interest_expense"].value == 250


def test_get_json_retries_after_429_and_respects_retry_after_seconds() -> None:
    session = FakeSession(
        {
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json": [
                FakeResponse({}, status_code=429, headers={"Retry-After": "1"}),
                FakeResponse({"facts": {"ok": True}}, status_code=200),
            ]
        }
    )
    sleeps = []
    current_time = {"value": 0.0}

    def fake_sleep(seconds: float) -> None:
        sleeps.append(round(seconds, 2))
        current_time["value"] += seconds

    provider = USProvider(
        session=session,
        sleep_fn=fake_sleep,
        clock_fn=lambda: current_time["value"],
    )

    payload = provider.get_company_facts("0001045810")

    assert payload["facts"]["ok"] is True
    assert len(session.calls) == 2
    assert sleeps == [1.0]


def test_get_json_raises_after_retry_budget_exhausted() -> None:
    session = FakeSession(
        {
            "https://data.sec.gov/submissions/CIK0001045810.json": [
                FakeResponse({}, status_code=429),
                FakeResponse({}, status_code=429),
                FakeResponse({}, status_code=429),
            ]
        }
    )
    sleeps = []
    current_time = {"value": 0.0}

    def fake_sleep(seconds: float) -> None:
        sleeps.append(round(seconds, 2))
        current_time["value"] += seconds

    provider = USProvider(
        session=session,
        max_retries=2,
        backoff_base_delay=0.5,
        sleep_fn=fake_sleep,
        clock_fn=lambda: current_time["value"],
    )

    try:
        provider.get_submissions("0001045810")
    except requests.HTTPError as exc:
        assert exc.response is not None
        assert exc.response.status_code == 429
    else:
        raise AssertionError("Expected repeated 429 responses to raise an HTTPError")

    assert len(session.calls) == 3
    assert sleeps == [0.5, 1.0]
