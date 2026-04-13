import logging

from app.models.financial_metric import FinancialMetric
from app.parsers.financial_metric_parser import FinancialMetricMappingError, parse_financial_metric


def test_parse_financial_metric_maps_synonym_tags() -> None:
    model = parse_financial_metric(
        {
            "facts": {
                "us-gaap": {
                    "TotalRevenues": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 2000}]}
                    },
                    "GrossProfit": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 900}]}
                    },
                    "OperatingIncomeLoss": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 500}]}
                    },
                    "ProfitLoss": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 420}]}
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 610}]}
                    },
                    "PropertyPlantAndEquipmentAdditions": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 140}]}
                    },
                    "DepreciationAndAmortization": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 70}]}
                    },
                    "Assets": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 4500}]}
                    },
                    "Liabilities": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 1800}]}
                    },
                    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 2700}]}
                    },
                    "LongTermDebtNoncurrent": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 300}]}
                    },
                    "DilutedEarningsPerShare": {
                        "units": {"USD/shares": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 2.15}]}
                    },
                    "WeightedAverageNumberOfDilutedSharesOutstanding": {
                        "units": {"shares": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 195}]}
                    },
                }
            }
        }
    )

    assert isinstance(model, FinancialMetric)
    assert model.revenue == 2000
    assert model.gross_profit == 900
    assert model.operating_income == 500
    assert model.net_income == 420
    assert model.operating_cash_flow == 610
    assert model.capex == 140
    assert model.depreciation_and_amortization == 70
    assert model.assets == 4500
    assert model.liabilities == 1800
    assert model.shareholders_equity == 2700
    assert model.long_term_debt == 300
    assert model.eps_diluted == 2.15
    assert model.shares_outstanding == 195
    assert model.source_tags["revenue"] == "TotalRevenues"


def test_parse_financial_metric_normalizes_abbreviated_units() -> None:
    model = parse_financial_metric(
        {
            "facts": {
                "us-gaap": {
                    "NetIncomeLoss": {
                        "units": {"millions": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 15}]}
                    },
                    "Revenues": {
                        "units": {"billions": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 2}]}
                    },
                }
            }
        },
        required_fields=["revenue", "net_income"],
    )

    assert model.net_income == 15_000_000
    assert model.revenue == 2_000_000_000


def test_parse_financial_metric_raises_for_missing_required_metric(caplog) -> None:
    caplog.set_level(logging.WARNING)

    try:
        parse_financial_metric(
            {
                "facts": {
                    "us-gaap": {
                        "Revenues": {
                            "units": {
                                "USD": [
                                    {
                                        "end": "2025-12-31",
                                        "filed": "2026-02-01",
                                        "form": "10-K",
                                        "fp": "FY",
                                        "fy": 2025,
                                        "val": 1000,
                                    }
                                ]
                            }
                        },
                    }
                }
            },
            ticker="MISSING",
            cik="0000000001",
            required_fields=["revenue", "net_income"],
        )
    except FinancialMetricMappingError as exc:
        assert exc.field_name == "net_income"
        assert exc.candidate_tags == ["NetIncomeLoss", "ProfitLoss"]
        assert exc.ticker == "MISSING"
        assert exc.cik == "0000000001"
        assert exc.period_context == {
            "end": "2025-12-31",
            "filed": "2026-02-01",
            "form": "10-K",
            "fy": 2025,
            "fp": "FY",
        }
        assert "net_income" in str(exc)
        assert "NetIncomeLoss" in str(exc)
        assert "0000000001" in str(exc)
    else:
        raise AssertionError("Expected missing required metric to raise FinancialMetricMappingError")

    assert "missing metric 'net_income'" in caplog.text.lower()


def test_parse_financial_metric_handles_missing_optional_metrics_with_warning(caplog) -> None:
    caplog.set_level(logging.WARNING)

    model = parse_financial_metric(
        {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 1000}]}
                    },
                    "NetIncomeLoss": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 120}]}
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": None}]}
                    },
                }
            }
        },
        required_fields=["revenue", "net_income"],
    )

    assert model.capex is None
    assert "missing metric 'capex'" in caplog.text.lower()
