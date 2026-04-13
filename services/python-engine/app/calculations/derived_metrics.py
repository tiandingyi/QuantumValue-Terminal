from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from app.models.financial_metric import FinancialMetric
from app.providers.sec_types import DerivedMetric


def calculate_derived_metrics(
    base_metrics: FinancialMetric,
    historical_base_metrics: Optional[Iterable[FinancialMetric]] = None,
) -> dict[str, DerivedMetric]:
    """Calculate internal value metrics from normalized base facts.

    Missing inputs skip only their dependent derived metric. The raw
    ``FinancialMetric`` remains the source DNA and is never mutated here.
    """
    results: dict[str, DerivedMetric] = {}
    period_end = base_metrics.period_end or ""
    filed_at = base_metrics.filed_at

    fcf = _free_cash_flow(base_metrics)
    if fcf is not None:
        results["free_cash_flow"] = DerivedMetric(
            name="Free Cash Flow",
            value=fcf,
            unit="USD",
            end=period_end,
            filed=filed_at,
            source="operating_cash_flow - abs(capex)",
        )

    owner_earnings = _owner_earnings(base_metrics)
    if owner_earnings is not None:
        results["owner_earnings"] = DerivedMetric(
            name="Owner Earnings",
            value=owner_earnings,
            unit="USD",
            end=period_end,
            filed=filed_at,
            source="net_income + depreciation_and_amortization - abs(capex)",
        )

    roe = _safe_ratio(base_metrics.net_income, base_metrics.shareholders_equity)
    if roe is not None:
        results["roe"] = DerivedMetric(
            name="Return on Equity",
            value=roe,
            unit="ratio",
            end=period_end,
            filed=filed_at,
            source="net_income / shareholders_equity",
        )

    gross_margin = _safe_ratio(base_metrics.gross_profit, base_metrics.revenue)
    if gross_margin is not None:
        results["gross_margin"] = DerivedMetric(
            name="Gross Margin",
            value=gross_margin,
            unit="ratio",
            end=period_end,
            filed=filed_at,
            source="gross_profit / revenue",
        )

    revenue_cagr = ten_year_cagr("revenue", historical_base_metrics or [base_metrics])
    if revenue_cagr is not None:
        results["revenue_10y_cagr"] = DerivedMetric(
            name="10-Year Revenue CAGR",
            value=revenue_cagr,
            unit="ratio",
            end=period_end,
            filed=filed_at,
            source="CAGR(revenue, 10 years)",
        )

    return results


def _free_cash_flow(metric: FinancialMetric) -> Optional[float]:
    if metric.operating_cash_flow is None or metric.capex is None:
        return None
    return float(metric.operating_cash_flow) - abs(float(metric.capex))


def _owner_earnings(metric: FinancialMetric) -> Optional[float]:
    required_values = [metric.net_income, metric.depreciation_and_amortization, metric.capex]
    if any(value is None for value in required_values):
        return None
    return float(metric.net_income) + float(metric.depreciation_and_amortization) - abs(float(metric.capex))


def _safe_ratio(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def ten_year_cagr(field_name: str, historical_base_metrics: Iterable[FinancialMetric]) -> Optional[float]:
    sorted_metrics = sorted(
        (
            metric
            for metric in historical_base_metrics
            if metric.period_end and getattr(metric, field_name) not in (None, 0)
        ),
        key=lambda metric: metric.period_end or "",
    )
    if len(sorted_metrics) < 2:
        return None

    latest = sorted_metrics[-1]
    latest_date = _parse_iso_date(latest.period_end)
    latest_value = getattr(latest, field_name)
    if latest_date is None or latest_value is None or latest_value <= 0:
        return None

    eligible_starts: list[tuple[float, FinancialMetric]] = []
    for candidate in sorted_metrics[:-1]:
        candidate_date = _parse_iso_date(candidate.period_end)
        candidate_value = getattr(candidate, field_name)
        if candidate_date is None or candidate_value is None or candidate_value <= 0:
            continue
        elapsed_years = (latest_date - candidate_date).days / 365.25
        if elapsed_years >= 9.5:
            eligible_starts.append((elapsed_years, candidate))

    if not eligible_starts:
        return None

    elapsed_years, start = min(eligible_starts, key=lambda item: abs(item[0] - 10.0))
    start_value = getattr(start, field_name)
    if start_value is None or start_value <= 0:
        return None

    return (float(latest_value) / float(start_value)) ** (1 / elapsed_years) - 1


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
