from app.calculations.derived_metrics import calculate_derived_metrics
from app.models.financial_metric import FinancialMetric


def test_calculate_derived_metrics_from_base_metrics() -> None:
    base = FinancialMetric(
        period_end="2026-12-31",
        filed_at="2027-02-15",
        revenue=2000,
        gross_profit=800,
        net_income=300,
        operating_cash_flow=420,
        capex=-90,
        depreciation_and_amortization=40,
        shareholders_equity=1500,
    )

    derived = calculate_derived_metrics(base)

    assert derived["free_cash_flow"].value == 330
    assert derived["free_cash_flow"].source == "operating_cash_flow - abs(capex)"
    assert derived["owner_earnings"].value == 250
    assert derived["owner_earnings"].source == "net_income + depreciation_and_amortization - abs(capex)"
    assert derived["roe"].value == 0.2
    assert derived["gross_margin"].value == 0.4
    assert "revenue_10y_cagr" not in derived


def test_calculate_derived_metrics_skips_missing_dependencies() -> None:
    base = FinancialMetric(
        period_end="2026-12-31",
        filed_at="2027-02-15",
        revenue=1000,
        net_income=100,
    )

    derived = calculate_derived_metrics(base)

    assert derived == {}


def test_calculate_derived_metrics_skips_zero_denominator_ratios() -> None:
    base = FinancialMetric(
        period_end="2026-12-31",
        revenue=0,
        gross_profit=10,
        net_income=10,
        shareholders_equity=0,
    )

    derived = calculate_derived_metrics(base)

    assert "roe" not in derived
    assert "gross_margin" not in derived


def test_calculate_revenue_10_year_cagr_from_history() -> None:
    history = [
        FinancialMetric(period_end="2016-12-31", revenue=100),
        FinancialMetric(period_end="2021-12-31", revenue=180),
        FinancialMetric(period_end="2026-12-31", filed_at="2027-02-15", revenue=259.37424601),
    ]

    derived = calculate_derived_metrics(history[-1], history)

    assert "revenue_10y_cagr" in derived
    assert round(derived["revenue_10y_cagr"].value, 4) == 0.1
    assert derived["revenue_10y_cagr"].source == "CAGR(revenue, 10 years)"


def test_calculate_revenue_10_year_cagr_skips_incomplete_history() -> None:
    history = [
        FinancialMetric(period_end="2023-12-31", revenue=100),
        FinancialMetric(period_end="2026-12-31", revenue=130),
    ]

    derived = calculate_derived_metrics(history[-1], history)

    assert "revenue_10y_cagr" not in derived
