from app.models.financial_metric import FinancialMetric
from app.persistence.filing_metadata import extract_all_supported_filings, extract_latest_supported_filing
from app.providers.sec_types import DerivedMetric


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


def test_extract_all_supported_filings_merges_recent_and_archives_without_limit() -> None:
    filings = extract_all_supported_filings(
        {
            "filings": {
                "recent": {
                    "form": ["10-K", "8-K", "10-Q"],
                    "accessionNumber": ["recent-k", "recent-8k", "recent-q"],
                    "filingDate": ["2026-03-01", "2026-02-01", "2025-12-01"],
                    "reportDate": ["2026-01-31", "2026-01-15", "2025-10-31"],
                }
            }
        },
        [
            {
                "form": ["10-K", "10-Q", "8-K"],
                "accessionNumber": ["archive-k-1", "archive-q-1", "archive-8k"],
                "filingDate": ["2012-03-01", "2011-12-01", "2011-11-01"],
                "reportDate": ["2012-01-31", "2011-10-31", "2011-10-15"],
            }
        ],
        "0001045810",
    )

    assert [filing.accession_number for filing in filings] == [
        "recent-k",
        "recent-q",
        "archive-k-1",
        "archive-q-1",
    ]


def test_extract_all_supported_filings_dedupes_duplicate_accessions() -> None:
    filings = extract_all_supported_filings(
        {
            "filings": {
                "recent": {
                    "form": ["10-K"],
                    "accessionNumber": ["same-accession"],
                    "filingDate": ["2026-03-01"],
                    "reportDate": ["2026-01-31"],
                }
            }
        },
        [
            {
                "form": ["10-K"],
                "accessionNumber": ["same-accession"],
                "filingDate": ["2026-03-01"],
                "reportDate": ["2026-01-31"],
            }
        ],
        "0001045810",
    )

    assert len(filings) == 1
    assert filings[0].accession_number == "same-accession"


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


def test_derived_metrics_can_include_valuation_section() -> None:
    derived = {
        "valuation": {
            "status": "ready",
            "scores": {"valuation_formula": 1.6},
            "flags": {"formula_gt_1_5": True},
        }
    }

    assert derived["valuation"]["scores"]["valuation_formula"] == 1.6
