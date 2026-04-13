from app.calculations.valuation import ValuationInputs, calculate_valuation_section
from app.models.financial_metric import FinancialMetric


def test_calculate_valuation_section_scores_and_flags() -> None:
    history = [
        FinancialMetric(period_end="2016-12-31", net_income=100),
        FinancialMetric(period_end="2026-12-31", filed_at="2027-02-15", net_income=400, eps_diluted=5),
    ]
    inputs = ValuationInputs(
        current_price=50,
        tax_after_dividend_yields=(0.02, 0.03, 0.04),
        historical_pe_ratios=(5, 8, 9, 10, 11),
    )

    section = calculate_valuation_section(history[-1], history, inputs)

    assert section["status"] == "ready"
    assert section["missing_inputs"] == []
    assert section["inputs"]["current_static_pe"] == 10
    assert section["inputs"]["avg_tax_after_dividend_yield"] == 0.03
    assert round(section["inputs"]["net_income_10y_cagr"], 4) == round((400 / 100) ** (1 / 10) - 1, 4)
    assert section["inputs"]["current_pe_percentile"] == 80
    assert "valuation_formula" in section["scores"]
    assert section["flags"]["formula_gt_1_5"] is False
    assert section["flags"]["pe_percentile_above_80"] is False


def test_calculate_valuation_section_flags_expensive_pe_percentile() -> None:
    base = FinancialMetric(period_end="2026-12-31", net_income=400, eps_diluted=5)
    history = [FinancialMetric(period_end="2016-12-31", net_income=100), base]
    inputs = ValuationInputs(
        current_static_pe=16,
        tax_after_dividend_yields=(0.02,),
        historical_pe_ratios=(5, 8, 10, 12, 15),
    )

    section = calculate_valuation_section(base, history, inputs)

    assert section["inputs"]["current_static_pe"] == 16
    assert section["inputs"]["current_pe_percentile"] == 100
    assert section["flags"]["pe_percentile_above_80"] is True


def test_calculate_valuation_section_flags_formula_threshold() -> None:
    base = FinancialMetric(period_end="2026-12-31", net_income=400)
    history = [FinancialMetric(period_end="2016-12-31", net_income=100), base]
    inputs = ValuationInputs(
        current_static_pe=0.05,
        tax_after_dividend_yields=(0.05,),
        historical_pe_ratios=(0.04, 0.05, 0.06),
    )

    section = calculate_valuation_section(base, history, inputs)

    assert section["scores"]["valuation_formula"] > 1.5
    assert section["flags"]["formula_gt_1_5"] is True


def test_calculate_valuation_section_reports_missing_inputs() -> None:
    base = FinancialMetric(period_end="2026-12-31", net_income=400)

    section = calculate_valuation_section(base, [base])

    assert section["status"] == "skipped"
    assert section["scores"] == {}
    assert section["missing_inputs"] == [
        "current_static_pe",
        "historical_pe_ratios",
        "net_income_10y_history",
        "tax_after_dividend_yields",
    ]
    assert section["flags"] == {
        "formula_gt_1_5": False,
        "pe_percentile_above_80": False,
    }
