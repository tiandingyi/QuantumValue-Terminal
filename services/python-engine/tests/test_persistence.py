from app.models.financial_metric import FinancialMetric
from app.persistence.filing_metadata import extract_latest_supported_filing
from app.providers.sec_types import CompanyLookup, DerivedMetric


def test_extract_latest_supported_filing_picks_latest_supported_form() -> None:
    filing = extract_latest_supported_filing(
        {
            "filings": {
                "recent": {
                    "form": ["8-K", "10-Q", "10-K"],
                    "accessionNumber": ["a", "b", "c"],
                    "filingDate": ["2026-01-10", "2026-02-10", "2026-03-10"],
                    "reportDate": ["2026-01-09", "2025-12-31", "2025-12-31"],
                }
            }
        },
        "0000320193",
    )

    assert filing.form_type == "10-Q"
    assert filing.accession_number == "b"
    assert filing.period_end_date == "2025-12-31"


def test_financial_metric_dump_is_ready_for_jsonb_storage() -> None:
    metric = FinancialMetric(
        period_end="2025-12-31",
        filed_at="2026-02-01",
        revenue=2_000_000_000,
        net_income=15000000,
        source_tags={"revenue": "Revenues", "net_income": "NetIncomeLoss"},
    )
    payload = metric.model_dump(mode="json")

    assert payload["revenue"] == 2_000_000_000
    assert payload["net_income"] == 15_000_000
    assert payload["source_tags"]["revenue"] == "Revenues"


def test_derived_metric_payload_is_separable_from_base_payload() -> None:
    derived = {
        "fcf": DerivedMetric(
            name="Free Cash Flow",
            value=123.0,
            unit="USD",
            end="2025-12-31",
            filed="2026-02-01",
            source="OperatingCashFlow - Capex",
        )
    }

    assert derived["fcf"].source == "OperatingCashFlow - Capex"
    assert derived["fcf"].value == 123.0
