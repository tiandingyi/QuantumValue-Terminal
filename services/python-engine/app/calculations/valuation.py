from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from app.calculations.derived_metrics import ten_year_cagr
from app.models.financial_metric import FinancialMetric


@dataclass(frozen=True)
class ValuationInputs:
    """Market-derived inputs required for valuation scoring.

    SEC filings provide EPS and earnings history, but current price, dividend
    yield, and historical P/E series must come from a market data source.
    """

    current_price: Optional[float] = None
    current_static_pe: Optional[float] = None
    tax_after_dividend_yields: tuple[float, ...] = ()
    historical_pe_ratios: tuple[float, ...] = ()


def calculate_valuation_section(
    base_metrics: FinancialMetric,
    historical_base_metrics: Iterable[FinancialMetric],
    valuation_inputs: Optional[ValuationInputs] = None,
) -> dict:
    """Build the dedicated valuation section stored inside derived_metrics."""
    inputs = valuation_inputs or ValuationInputs()
    missing_inputs: list[str] = []

    net_income_cagr = ten_year_cagr("net_income", historical_base_metrics)
    if net_income_cagr is None:
        missing_inputs.append("net_income_10y_history")

    average_dividend_yield = _average_positive(inputs.tax_after_dividend_yields)
    if average_dividend_yield is None:
        missing_inputs.append("tax_after_dividend_yields")

    current_static_pe = _current_static_pe(base_metrics, inputs)
    if current_static_pe is None:
        missing_inputs.append("current_static_pe")

    pe_percentile = _percentile_rank(current_static_pe, inputs.historical_pe_ratios)
    if pe_percentile is None:
        missing_inputs.append("historical_pe_ratios")

    section = {
        "status": "ready" if not missing_inputs else "skipped",
        "missing_inputs": sorted(set(missing_inputs)),
        "formula": "(net_income_10y_cagr + avg_tax_after_dividend_yield) / current_static_pe",
        "inputs": {
            "net_income_10y_cagr": net_income_cagr,
            "avg_tax_after_dividend_yield": average_dividend_yield,
            "current_static_pe": current_static_pe,
            "current_pe_percentile": pe_percentile,
        },
        "scores": {},
        "flags": {
            "formula_gt_1_5": False,
            "pe_percentile_above_80": bool(pe_percentile is not None and pe_percentile > 80),
        },
    }

    if net_income_cagr is not None and average_dividend_yield is not None and current_static_pe not in (None, 0):
        formula_score = (net_income_cagr + average_dividend_yield) / current_static_pe
        section["scores"]["valuation_formula"] = formula_score
        section["flags"]["formula_gt_1_5"] = formula_score > 1.5

    return section


def _current_static_pe(base_metrics: FinancialMetric, inputs: ValuationInputs) -> Optional[float]:
    if inputs.current_static_pe is not None and inputs.current_static_pe > 0:
        return float(inputs.current_static_pe)
    if inputs.current_price is None or base_metrics.eps_diluted in (None, 0):
        return None
    pe_ratio = float(inputs.current_price) / float(base_metrics.eps_diluted)
    return pe_ratio if pe_ratio > 0 else None


def _average_positive(values: Iterable[float]) -> Optional[float]:
    positive_values = [float(value) for value in values if value is not None and value >= 0]
    if not positive_values:
        return None
    return sum(positive_values) / len(positive_values)


def _percentile_rank(current_value: Optional[float], historical_values: Iterable[float]) -> Optional[float]:
    if current_value is None:
        return None
    values = sorted(float(value) for value in historical_values if value is not None and value > 0)
    if not values:
        return None
    values_at_or_below = sum(1 for value in values if value <= current_value)
    return values_at_or_below / len(values) * 100
