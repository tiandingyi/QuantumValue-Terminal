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
                    "CostOfGoodsAndServicesSold": {
                        "units": {"USD": [{"end": "2025-12-31", "filed": "2026-02-01", "form": "10-K", "fp": "FY", "val": 1100}]}
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
    assert model.cost_of_revenue == 1100
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


def test_parse_financial_metric_does_not_fallback_when_explicit_anchor_is_missing() -> None:
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
                                        "val": 1000,
                                    }
                                ]
                            }
                        },
                        "NetIncomeLoss": {
                            "units": {
                                "USD": [
                                    {
                                        "end": "2025-12-31",
                                        "filed": "2026-02-01",
                                        "form": "10-K",
                                        "fp": "FY",
                                        "val": 100,
                                    }
                                ]
                            }
                        },
                    }
                }
            },
            ticker="OLD",
            cik="0000000004",
            required_fields=["revenue", "net_income"],
            anchor={"end": "1999-12-31", "form": "10-K"},
        )
    except FinancialMetricMappingError as exc:
        assert exc.field_name == "revenue"
        assert exc.period_context == {"end": "1999-12-31", "form": "10-K"}
    else:
        raise AssertionError("Expected explicit missing anchor period to raise instead of using latest facts")


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


# ---------------------------------------------------------------------------
# Story 9 regression tests – new tag synonyms and computed gross_profit
# ---------------------------------------------------------------------------

def _base_facts(period: str = "2024-09-28") -> dict:
    """Minimal us-gaap fact set covering all 13 required fields."""
    def entry(val, unit="USD"):
        return {"units": {unit: [{"end": period, "filed": "2025-01-01", "form": "10-K", "fp": "FY", "val": val}]}}

    return {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": entry(391035000000),
                "GrossProfit": entry(177127000000),
                "CostOfGoodsAndServicesSold": entry(213908000000),
                "OperatingIncomeLoss": entry(123216000000),
                "NetIncomeLoss": entry(93736000000),
                "NetCashProvidedByUsedInOperatingActivities": entry(118254000000),
                "PaymentsToAcquirePropertyPlantAndEquipment": entry(9447000000),
                "DepreciationDepletionAndAmortization": entry(11445000000),
                "Assets": entry(364980000000),
                "Liabilities": entry(308030000000),
                "StockholdersEquity": entry(56950000000),
                "LongTermDebt": entry(85750000000),
                "EarningsPerShareDiluted": entry(6.11, "USD/shares"),
                "WeightedAverageNumberOfDilutedSharesOutstanding": entry(15343783000, "shares"),
            }
        }
    }


def test_capex_falls_back_to_payments_to_acquire_productive_assets() -> None:
    """PaymentsToAcquireProductiveAssets is used for early AAPL-style filings."""
    facts = _base_facts("2008-09-27")
    gaap = facts["facts"]["us-gaap"]
    # Remove the standard capex tag; use the older synonym instead
    del gaap["PaymentsToAcquirePropertyPlantAndEquipment"]
    gaap["PaymentsToAcquireProductiveAssets"] = {
        "units": {"USD": [{"end": "2008-09-27", "filed": "2008-11-05", "form": "10-K", "fp": "FY", "val": 1091000000}]}
    }

    model = parse_financial_metric(facts)
    assert model.capex == 1091000000
    assert model.source_tags["capex"] == "PaymentsToAcquireProductiveAssets"


def test_interest_expense_falls_back_to_interest_expense_debt() -> None:
    """InterestExpenseDebt covers AAPL periods where InterestExpense is absent."""
    facts = _base_facts()
    gaap = facts["facts"]["us-gaap"]
    gaap["InterestExpenseDebt"] = {
        "units": {"USD": [{"end": "2024-09-28", "filed": "2025-01-01", "form": "10-K", "fp": "FY", "val": 3000000000}]}
    }

    model = parse_financial_metric(facts)
    assert model.interest_expense == 3000000000
    assert model.source_tags["interest_expense"] == "InterestExpenseDebt"


def test_interest_expense_falls_back_to_interest_expense_nonoperating() -> None:
    """InterestExpenseNonoperating covers COST-style recent filings."""
    facts = _base_facts("2025-08-31")
    gaap = facts["facts"]["us-gaap"]
    gaap["InterestExpenseNonoperating"] = {
        "units": {"USD": [{"end": "2025-08-31", "filed": "2025-10-10", "form": "10-K", "fp": "FY", "val": 182000000}]}
    }

    model = parse_financial_metric(facts)
    assert model.interest_expense == 182000000
    assert model.source_tags["interest_expense"] == "InterestExpenseNonoperating"


def test_cash_dividends_falls_back_to_dividends_common_stock_cash() -> None:
    """DividendsCommonStockCash is used by COST instead of PaymentsOfDividendsCommonStock."""
    facts = _base_facts("2024-09-01")
    gaap = facts["facts"]["us-gaap"]
    gaap["DividendsCommonStockCash"] = {
        "units": {"USD": [{"end": "2024-09-01", "filed": "2024-10-10", "form": "10-K", "fp": "FY", "val": 1519000000}]}
    }

    model = parse_financial_metric(facts)
    assert model.cash_dividends == 1519000000
    assert model.source_tags["cash_dividends"] == "DividendsCommonStockCash"


def test_gross_profit_computed_from_revenue_minus_cost_of_revenue() -> None:
    """When GrossProfit tag is absent, gross_profit is derived from revenue - cost_of_revenue.

    This covers COST-style filings where revenue and COGS are reported separately
    but no GrossProfit XBRL tag is present for the anchor period.
    """
    period = "2024-09-01"

    def entry(val):
        return {"units": {"USD": [{"end": period, "filed": "2024-10-10", "form": "10-K", "fp": "FY", "val": val}]}}

    facts = {
        "facts": {
            "us-gaap": {
                "RevenueFromContractWithCustomerExcludingAssessedTax": entry(254453000000),
                # No GrossProfit tag — COST pattern
                "CostOfGoodsAndServicesSold": entry(222358000000),
                "OperatingIncomeLoss": entry(9285000000),
                "NetIncomeLoss": entry(7367000000),
                "NetCashProvidedByUsedInOperatingActivities": entry(11068000000),
                "PaymentsToAcquirePropertyPlantAndEquipment": entry(4710000000),
                "DepreciationDepletionAndAmortization": entry(2458000000),
                "Assets": entry(69830000000),
                "Liabilities": entry(41358000000),
                "StockholdersEquity": entry(27472000000),
                "LongTermDebt": entry(5377000000),
                "EarningsPerShareDiluted": {"units": {"USD/shares": [{"end": period, "filed": "2024-10-10", "form": "10-K", "fp": "FY", "val": 16.56}]}},
                "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": [{"end": period, "filed": "2024-10-10", "form": "10-K", "fp": "FY", "val": 444757000}]}},
            }
        }
    }

    model = parse_financial_metric(facts)

    assert model.gross_profit == 254453000000 - 222358000000
    assert model.source_tags["gross_profit"] == "_computed:revenue-cost_of_revenue"


def test_gross_profit_tag_takes_precedence_over_computed() -> None:
    """When GrossProfit tag is present, it is preferred over the computed fallback."""
    facts = _base_facts()
    # GrossProfit tag is present in _base_facts, cost_of_revenue would give a different value
    model = parse_financial_metric(facts)

    assert model.gross_profit == 177127000000
    assert model.source_tags["gross_profit"] == "GrossProfit"

