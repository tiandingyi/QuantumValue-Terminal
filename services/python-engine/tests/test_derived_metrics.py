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

    assert "free_cash_flow" not in derived
    assert derived["oe_dcf_total"]["status"] in {"missing", "not_applicable"}
    assert derived["gross_margin_percent"]["status"] in {"missing", "not_applicable"}


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


def test_story7_metrics_include_structured_cells() -> None:
    history = [
        FinancialMetric(
            period_end="2023-12-31",
            revenue=1000,
            gross_profit=450,
            operating_income=180,
            net_income=120,
            operating_cash_flow=200,
            capex=50,
            depreciation_and_amortization=30,
            shareholders_equity=700,
            parent_shareholders_equity=700,
            shares_outstanding=100,
            cash_and_equivalents=100,
            long_term_debt=200,
            current_debt=20,
            cash_dividends=20,
            eps_basic=1.2,
        ),
        FinancialMetric(
            period_end="2024-12-31",
            revenue=1100,
            gross_profit=500,
            operating_income=200,
            net_income=140,
            operating_cash_flow=230,
            capex=55,
            depreciation_and_amortization=32,
            shareholders_equity=760,
            parent_shareholders_equity=760,
            shares_outstanding=100,
            cash_and_equivalents=120,
            long_term_debt=205,
            current_debt=20,
            cash_dividends=25,
            eps_basic=1.4,
        ),
        FinancialMetric(
            period_end="2025-12-31",
            revenue=1250,
            gross_profit=575,
            operating_income=250,
            net_income=180,
            operating_cash_flow=290,
            capex=60,
            depreciation_and_amortization=35,
            shareholders_equity=840,
            parent_shareholders_equity=840,
            shares_outstanding=100,
            cash_and_equivalents=140,
            long_term_debt=210,
            current_debt=25,
            cash_dividends=30,
            eps_basic=1.8,
            income_tax_expense=45,
            pretax_income=225,
            current_debt_maturities=10,
        ),
    ]
    derived = calculate_derived_metrics(history[-1], history)

    assert derived["oe_dcf_total"]["status"] == "ready"
    assert derived["oe_dcf_margin_of_safety_price"]["status"] == "ready"
    assert derived["munger_20"]["status"] == "ready"
    assert derived["eps_cagr_percent_points"]["status"] == "ready"
    assert derived["dividend_payout_ratio_percent"]["status"] == "ready"
    assert derived["gross_margin_percent"]["status"] == "ready"
    assert derived["revenue_3y_cagr_percent_points"]["status"] == "ready"
    assert derived["revenue_yoy_percent"]["status"] == "ready"


def test_story7_market_data_missing_states() -> None:
    metric = FinancialMetric(
        period_end="2025-12-31",
        revenue=1000,
        net_income=100,
        operating_cash_flow=150,
        capex=30,
        depreciation_and_amortization=20,
        shareholders_equity=500,
        parent_shareholders_equity=500,
        shares_outstanding=50,
    )
    derived = calculate_derived_metrics(metric, [metric])

    assert derived["pe_ratio"]["status"] == "not_applicable"
    assert derived["pe_ratio"]["metadata"]["reason"] == "spot_price_unavailable"
    assert derived["total_shareholder_yield_percent"]["status"] == "not_applicable"


def test_story7_market_data_ready_paths() -> None:
    history = [
        FinancialMetric(
            period_end="2023-12-31",
            revenue=1000,
            gross_profit=450,
            operating_income=180,
            net_income=120,
            operating_cash_flow=200,
            capex=50,
            depreciation_and_amortization=30,
            shareholders_equity=700,
            parent_shareholders_equity=700,
            shares_outstanding=100,
            cash_and_equivalents=100,
            long_term_debt=200,
            current_debt=20,
            cash_dividends=20,
            eps_basic=1.2,
        ),
        FinancialMetric(
            period_end="2024-12-31",
            revenue=1100,
            gross_profit=500,
            operating_income=200,
            net_income=140,
            operating_cash_flow=230,
            capex=55,
            depreciation_and_amortization=32,
            shareholders_equity=760,
            parent_shareholders_equity=760,
            shares_outstanding=100,
            cash_and_equivalents=120,
            long_term_debt=205,
            current_debt=20,
            cash_dividends=25,
            eps_basic=1.4,
        ),
        FinancialMetric(
            period_end="2025-12-31",
            revenue=1250,
            gross_profit=575,
            operating_income=250,
            net_income=180,
            operating_cash_flow=290,
            capex=60,
            depreciation_and_amortization=35,
            shareholders_equity=840,
            parent_shareholders_equity=840,
            shares_outstanding=100,
            cash_and_equivalents=140,
            long_term_debt=210,
            current_debt=25,
            cash_dividends=30,
            eps_basic=1.8,
            income_tax_expense=45,
            pretax_income=225,
            current_debt_maturities=10,
        ),
    ]

    derived = calculate_derived_metrics(
        history[-1],
        history,
        market_data={"spot_price": 180.0, "market_cap": 18_000.0},
    )

    assert derived["pe_ratio"]["status"] == "ready"
    assert round(derived["pe_ratio"]["value"], 2) == 100.0
    assert derived["peg_ratio"]["status"] == "ready"
    assert derived["pegy_ratio"]["status"] == "ready"
    assert derived["dividend_yield_percent"]["status"] == "ready"
    assert derived["total_shareholder_yield_percent"]["status"] == "ready"


def test_gross_margin_uses_cost_of_revenue_fallback() -> None:
    metric = FinancialMetric(
        period_end="2025-12-31",
        revenue=1000,
        cost_of_revenue=700,
        operating_income=100,
        net_income=80,
        operating_cash_flow=120,
        capex=20,
        depreciation_and_amortization=10,
        shareholders_equity=500,
        parent_shareholders_equity=500,
        shares_outstanding=100,
    )
    derived = calculate_derived_metrics(metric, [metric])

    assert derived["gross_margin_percent"]["status"] == "ready"
    assert round(derived["gross_margin_percent"]["value"], 2) == 30.0


def test_book_etr_uses_pretax_fallback_from_net_income_plus_tax() -> None:
    metric = FinancialMetric(
        period_end="2025-12-31",
        revenue=1000,
        operating_income=100,
        net_income=80,
        income_tax_expense=20,
        operating_cash_flow=120,
        capex=20,
        depreciation_and_amortization=10,
        shareholders_equity=500,
        parent_shareholders_equity=500,
        shares_outstanding=100,
    )
    derived = calculate_derived_metrics(metric, [metric])

    assert derived["book_effective_tax_rate_percent"]["status"] == "ready"
    assert round(derived["book_effective_tax_rate_percent"]["value"], 2) == 20.0
