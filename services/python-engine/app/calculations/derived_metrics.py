from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any, Iterable, Optional

from app.models.financial_metric import FinancialMetric
from app.providers.sec_types import DerivedMetric


def calculate_derived_metrics(
    base_metrics: FinancialMetric,
    historical_base_metrics: Optional[Iterable[FinancialMetric]] = None,
    market_data: Optional[dict[str, Optional[float]]] = None,
) -> dict[str, Any]:
    """Calculate internal value metrics from normalized base facts.

    Missing inputs skip only their dependent derived metric. The raw
    ``FinancialMetric`` remains the source DNA and is never mutated here.
    """
    results: dict[str, Any] = {}
    period_end = base_metrics.period_end or ""
    filed_at = base_metrics.filed_at
    history = _history_up_to_current(base_metrics, historical_base_metrics or [base_metrics])

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

    results.update(_story7_yearly_metrics(base_metrics, history, market_data=market_data))
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


def _ready_cell(
    *,
    value: float,
    unit: str,
    formula: str,
    lookback: Optional[dict[str, Any]] = None,
    parameters: Optional[dict[str, Any]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "status": "ready",
        "value": float(value),
        "unit": unit,
        "formula": formula,
        "missing_inputs": [],
        "lookback": lookback or {},
        "parameters": parameters or {},
        "metadata": metadata or {},
    }


def _missing_cell(*, missing_inputs: list[str], message: str, unit: str = "n/a") -> dict[str, Any]:
    return {
        "status": "missing",
        "value": None,
        "unit": unit,
        "formula": "",
        "missing_inputs": sorted(set(missing_inputs)),
        "lookback": {},
        "parameters": {},
        "metadata": {"message": message},
    }


def _not_applicable_cell(*, reason: str, unit: str = "n/a", formula: str = "") -> dict[str, Any]:
    return {
        "status": "not_applicable",
        "value": None,
        "unit": unit,
        "formula": formula,
        "missing_inputs": [],
        "lookback": {},
        "parameters": {},
        "metadata": {"reason": reason},
    }


def _history_up_to_current(
    base_metrics: FinancialMetric,
    historical_base_metrics: Iterable[FinancialMetric],
) -> list[FinancialMetric]:
    metrics = [metric for metric in historical_base_metrics if metric.period_end]
    metrics.sort(key=lambda metric: metric.period_end or "")
    if not base_metrics.period_end:
        return metrics
    return [metric for metric in metrics if (metric.period_end or "") <= base_metrics.period_end]


def _story7_yearly_metrics(
    base_metrics: FinancialMetric,
    history: list[FinancialMetric],
    *,
    market_data: Optional[dict[str, Optional[float]]] = None,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    defaults = {
        "discount_rate": 0.10,
        "terminal_growth_rate": 0.03,
        "forecast_years": 10,
        "margin_of_safety": 0.30,
        "default_retention_ratio": 0.60,
        "default_payout_ratio": 0.40,
        "default_effective_tax_rate": 0.25,
        "munger_exit_multiples": [15, 20, 25],
    }

    owner_series = _owner_earnings_series(history)
    oe_context = _owner_earnings_growth_context(base_metrics, owner_series)
    results["oe_dcf_total"] = _oe_dcf_metric(base_metrics, oe_context, defaults)
    results["oe_dcf_margin_of_safety_price"] = _margin_of_safety_metric(
        results["oe_dcf_total"],
        defaults["margin_of_safety"],
    )

    munger = _munger_metrics(base_metrics, history, oe_context, defaults)
    results.update(munger)

    eps_cagr = _eps_cagr_metric(base_metrics, history)
    results["eps_cagr_percent_points"] = eps_cagr

    spot_price: Optional[float] = (market_data or {}).get("spot_price")
    market_cap: Optional[float] = (market_data or {}).get("market_cap")
    eps_for_pe = base_metrics.real_eps or base_metrics.eps_diluted or base_metrics.eps_basic
    if spot_price is not None and eps_for_pe not in (None, 0) and float(eps_for_pe) > 0:
        results["pe_ratio"] = _ready_cell(
            value=spot_price / float(eps_for_pe),
            unit="multiple",
            formula="spot_price / eps",
            metadata={"spot_price": spot_price, "eps_used": float(eps_for_pe)},
        )
        results["earnings_yield_percent"] = _ready_cell(
            value=float(eps_for_pe) / spot_price * 100,
            unit="percent",
            formula="eps / spot_price * 100",
        )
    elif spot_price is not None and eps_for_pe not in (None,) and float(eps_for_pe) <= 0:
        results["pe_ratio"] = _not_applicable_cell(reason="EPS_for_PE <= 0", unit="multiple")
        results["earnings_yield_percent"] = _not_applicable_cell(reason="EPS_for_PE <= 0", unit="percent")
    else:
        results["pe_ratio"] = _not_applicable_cell(reason="spot_price_unavailable", unit="multiple")
        results["earnings_yield_percent"] = _not_applicable_cell(reason="spot_price_unavailable", unit="percent")

    results["peg_ratio"] = _peg_metric(results["pe_ratio"], eps_cagr)
    results["pegy_ratio"] = _pegy_metric(results["pe_ratio"], eps_cagr, base_metrics, market_cap=market_cap)

    results.update(_shareholder_return_metrics(base_metrics, oe_context, market_cap=market_cap))
    results.update(_quality_risk_metrics(base_metrics))
    results.update(_pricing_power_metrics(base_metrics, history))
    return results


def _owner_earnings_value(metric: FinancialMetric) -> Optional[float]:
    if metric.net_income is None or metric.capex is None or metric.depreciation_and_amortization is None:
        return None
    da = float(metric.depreciation_and_amortization)
    capex = abs(float(metric.capex))
    maintenance_capex = min(capex, da) if da > 0 else capex
    return float(metric.net_income) + da - maintenance_capex


def _owner_earnings_series(history: list[FinancialMetric]) -> list[tuple[str, float]]:
    series: list[tuple[str, float]] = []
    for metric in history:
        if not metric.period_end:
            continue
        owner_earnings = _owner_earnings_value(metric)
        if owner_earnings is None:
            continue
        series.append((metric.period_end, owner_earnings))
    return series


def _owner_earnings_growth_context(
    base_metrics: FinancialMetric,
    owner_series: list[tuple[str, float]],
) -> dict[str, Any]:
    if base_metrics.shares_outstanding in (None, 0):
        return {"status": "missing", "missing_inputs": ["shares_outstanding"]}
    if not owner_series:
        return {"status": "missing", "missing_inputs": ["owner_earnings_history"]}

    last_three = owner_series[-3:]
    avg_owner_earnings = sum(value for _, value in last_three) / len(last_three)
    avg_oe_per_share = avg_owner_earnings / float(base_metrics.shares_outstanding)

    yoy_values: list[float] = []
    yoy_periods: list[tuple[str, str]] = []
    max_periods = owner_series[-8:]
    for index in range(1, len(max_periods)):
        prev_period, prev_value = max_periods[index - 1]
        curr_period, curr_value = max_periods[index]
        if prev_value == 0:
            continue
        yoy_values.append((curr_value - prev_value) / prev_value)
        yoy_periods.append((prev_period, curr_period))
    if not yoy_values:
        return {"status": "not_applicable", "reason": "insufficient_history"}
    median_g = float(median(yoy_values))

    equity = base_metrics.parent_shareholders_equity or base_metrics.shareholders_equity
    if equity in (None, 0):
        return {"status": "missing", "missing_inputs": ["parent_shareholders_equity"]}
    roe = float(base_metrics.net_income or 0) / float(equity)

    payout_ratio: Optional[float] = None
    retention_ratio = 0.60
    payout_fallback = True
    if base_metrics.cash_dividends is not None and base_metrics.net_income not in (None, 0):
        payout_ratio = float(base_metrics.cash_dividends) / float(base_metrics.net_income)
        retention_ratio = 1 - payout_ratio
        payout_fallback = False

    g_ceiling = min(roe * retention_ratio, 0.25)
    final_g = max(0.0, min(median_g, g_ceiling))
    return {
        "status": "ready",
        "avg_oe_per_share": avg_oe_per_share,
        "avg_oe_window": [period for period, _ in last_three],
        "median_g": median_g,
        "g_ceiling": g_ceiling,
        "g": final_g,
        "roe": roe,
        "retention_ratio": retention_ratio,
        "payout_ratio": payout_ratio,
        "payout_fallback": payout_fallback,
        "yoy_periods": yoy_periods,
    }


def _oe_dcf_metric(
    base_metrics: FinancialMetric,
    context: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    if context.get("status") == "not_applicable":
        return _not_applicable_cell(reason=context.get("reason", "insufficient_history"), unit="currency")
    if context.get("status") != "ready":
        return _missing_cell(
            missing_inputs=context.get("missing_inputs", ["owner_earnings_inputs"]),
            message="SEC fact unavailable",
            unit="currency",
        )
    if base_metrics.shares_outstanding in (None, 0):
        return _missing_cell(missing_inputs=["shares_outstanding"], message="SEC fact unavailable", unit="currency")

    r = defaults["discount_rate"]
    g_tv = defaults["terminal_growth_rate"]
    n = defaults["forecast_years"]
    g = context["g"]
    avg_oe_per_share = context["avg_oe_per_share"]
    pv_stage1 = sum(avg_oe_per_share * ((1 + g) ** year) / ((1 + r) ** year) for year in range(1, n + 1))
    oe_10 = avg_oe_per_share * ((1 + g) ** n)
    terminal_value = oe_10 * (1 + g_tv) / (r - g_tv)
    pv_terminal = terminal_value / ((1 + r) ** n)
    net_cash = float(base_metrics.cash_and_equivalents or 0) - float((base_metrics.long_term_debt or 0) + (base_metrics.current_debt or 0))
    net_cash_per_share = net_cash / float(base_metrics.shares_outstanding)
    total = pv_stage1 + pv_terminal + net_cash_per_share

    return _ready_cell(
        value=total,
        unit="currency",
        formula="OE_DCF_total = PV_stage1 + PV_terminal + net_cash_per_share",
        lookback={
            "avg_oe_periods": context["avg_oe_window"],
            "oe_yoy_periods": context["yoy_periods"],
            "forecast_years": n,
        },
        parameters={
            "discount_rate": r,
            "terminal_growth_rate": g_tv,
            "growth_rate": g,
            "retention_ratio": context["retention_ratio"],
            "payout_ratio": context["payout_ratio"],
            "payout_fallback_used": context["payout_fallback"],
        },
        metadata={"net_cash_per_share": net_cash_per_share},
    )


def _margin_of_safety_metric(metric: dict[str, Any], margin_of_safety: float) -> dict[str, Any]:
    if metric.get("status") == "not_applicable":
        return _not_applicable_cell(
            reason=metric.get("metadata", {}).get("reason", "intrinsic_value_not_applicable"),
            unit="currency",
        )
    if metric.get("status") != "ready" or metric.get("value") is None:
        return _missing_cell(
            missing_inputs=metric.get("missing_inputs", ["intrinsic_value"]),
            message="Intrinsic value unavailable",
            unit="currency",
        )
    return _ready_cell(
        value=float(metric["value"]) * (1 - margin_of_safety),
        unit="currency",
        formula="intrinsic_value * (1 - margin_of_safety)",
        parameters={"margin_of_safety": margin_of_safety},
    )


def _munger_metrics(
    base_metrics: FinancialMetric,
    history: list[FinancialMetric],
    context: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    if context.get("status") == "not_applicable":
        reason = context.get("reason", "insufficient_history")
        return {
            "munger_15": _not_applicable_cell(reason=reason, unit="currency"),
            "munger_20": _not_applicable_cell(reason=reason, unit="currency"),
            "munger_25": _not_applicable_cell(reason=reason, unit="currency"),
            "munger_15_margin_of_safety_price": _not_applicable_cell(reason=reason, unit="currency"),
            "munger_20_margin_of_safety_price": _not_applicable_cell(reason=reason, unit="currency"),
            "munger_25_margin_of_safety_price": _not_applicable_cell(reason=reason, unit="currency"),
        }
    if context.get("status") != "ready":
        missing = context.get("missing_inputs", ["owner_earnings_inputs"])
        return {
            "munger_15": _missing_cell(missing_inputs=missing, message="SEC fact unavailable", unit="currency"),
            "munger_20": _missing_cell(missing_inputs=missing, message="SEC fact unavailable", unit="currency"),
            "munger_25": _missing_cell(missing_inputs=missing, message="SEC fact unavailable", unit="currency"),
            "munger_15_margin_of_safety_price": _missing_cell(missing_inputs=missing, message="SEC fact unavailable", unit="currency"),
            "munger_20_margin_of_safety_price": _missing_cell(missing_inputs=missing, message="SEC fact unavailable", unit="currency"),
            "munger_25_margin_of_safety_price": _missing_cell(missing_inputs=missing, message="SEC fact unavailable", unit="currency"),
        }

    r = defaults["discount_rate"]
    n = defaults["forecast_years"]
    g = context["g"]
    avg_oe_per_share = context["avg_oe_per_share"]
    payout_values = _recent_payout_ratios(history, periods=3)
    payout_fallback = len(payout_values) == 0
    payout = (sum(payout_values) / len(payout_values)) if payout_values else defaults["default_payout_ratio"]
    pv_dividends = sum(
        avg_oe_per_share * ((1 + g) ** year) * payout / ((1 + r) ** year)
        for year in range(1, n + 1)
    )
    eps_10 = avg_oe_per_share * ((1 + g) ** n)
    net_cash = float(base_metrics.cash_and_equivalents or 0) - float((base_metrics.long_term_debt or 0) + (base_metrics.current_debt or 0))
    shares = float(base_metrics.shares_outstanding or 0)
    net_cash_per_share = 0.0 if shares == 0 else net_cash / shares

    values: dict[str, Any] = {}
    for multiple in defaults["munger_exit_multiples"]:
        exit_value = eps_10 * multiple / ((1 + r) ** n)
        fair_value = pv_dividends + exit_value + net_cash_per_share
        key = f"munger_{multiple}"
        values[key] = _ready_cell(
            value=fair_value,
            unit="currency",
            formula=f"PV_dividends + EPS_10*{multiple}/(1+r)^n + net_cash_per_share",
            lookback={"payout_periods_used": len(payout_values), "forecast_years": n},
            parameters={
                "discount_rate": r,
                "growth_rate": g,
                "exit_multiple": multiple,
                "payout_ratio": payout,
                "payout_fallback_used": payout_fallback,
            },
        )
        values[f"{key}_margin_of_safety_price"] = _margin_of_safety_metric(values[key], defaults["margin_of_safety"])
    return values


def _recent_payout_ratios(history: list[FinancialMetric], periods: int) -> list[float]:
    ratios: list[float] = []
    for metric in reversed(history):
        if metric.cash_dividends is None or metric.net_income in (None, 0):
            continue
        ratios.append(float(metric.cash_dividends) / float(metric.net_income))
        if len(ratios) >= periods:
            break
    return list(reversed(ratios))


def _eps_cagr_metric(base_metrics: FinancialMetric, history: list[FinancialMetric]) -> dict[str, Any]:
    series = _series_with_fallback(history, ["real_eps", "eps_basic", "eps_diluted"])
    if len(series) < 2:
        return _not_applicable_cell(reason="insufficient_history", unit="percent_points")

    end_period, end_value = series[-1]
    if end_value <= 0:
        return _not_applicable_cell(reason="EPS_for_PE <= 0", unit="percent_points")

    candidates = []
    end_date = _parse_iso_date(end_period)
    if end_date is None:
        return _missing_cell(missing_inputs=["eps_period_end"], message="SEC fact unavailable", unit="percent_points")

    for period, value in series[:-1]:
        if value <= 0:
            continue
        start_date = _parse_iso_date(period)
        if start_date is None:
            continue
        years = (end_date - start_date).days / 365.25
        if years >= 0.75:
            candidates.append((abs(years - 3), years, period, value))
    if not candidates:
        return _not_applicable_cell(reason="no_positive_eps_baseline", unit="percent_points")

    _, years, start_period, start_value = min(candidates, key=lambda item: item[0])
    cagr_decimal = (end_value / start_value) ** (1 / years) - 1
    cagr_percent_points = cagr_decimal * 100
    return _ready_cell(
        value=cagr_percent_points,
        unit="percent_points",
        formula="(ending / beginning)^(1/n)-1, stored as percentage points",
        lookback={"start_period": start_period, "end_period": end_period, "years": years},
        metadata={"decimal_value": cagr_decimal},
    )


def _peg_metric(pe_metric: dict[str, Any], eps_cagr_metric: dict[str, Any]) -> dict[str, Any]:
    if pe_metric.get("status") == "not_applicable":
        return _not_applicable_cell(reason="pe_ratio_not_applicable", unit="multiple")
    if pe_metric.get("status") != "ready":
        return _not_applicable_cell(reason="spot_price_unavailable", unit="multiple")
    if eps_cagr_metric.get("status") == "not_applicable":
        return _not_applicable_cell(reason="eps_cagr_not_applicable", unit="multiple")
    if eps_cagr_metric.get("status") != "ready" or eps_cagr_metric.get("value") is None:
        return _missing_cell(
            missing_inputs=["eps_cagr_percent_points"],
            message="SEC fact unavailable",
            unit="multiple",
        )
    denominator = float(eps_cagr_metric["value"])
    if denominator <= 0:
        return _not_applicable_cell(reason="CAGR <= 0", unit="multiple", formula="PE / CAGR_percent_points")
    return _ready_cell(
        value=float(pe_metric["value"]) / denominator,
        unit="multiple",
        formula="PE / CAGR_percent_points",
    )


def _pegy_metric(
    pe_metric: dict[str, Any],
    eps_cagr_metric: dict[str, Any],
    base_metrics: FinancialMetric,
    *,
    market_cap: Optional[float] = None,
) -> dict[str, Any]:
    if pe_metric.get("status") == "not_applicable":
        return _not_applicable_cell(reason="pe_ratio_not_applicable", unit="multiple")
    if pe_metric.get("status") != "ready":
        return _not_applicable_cell(reason="spot_price_unavailable", unit="multiple")
    if eps_cagr_metric.get("status") == "not_applicable":
        return _not_applicable_cell(reason="eps_cagr_not_applicable", unit="multiple")
    if eps_cagr_metric.get("status") != "ready" or eps_cagr_metric.get("value") is None:
        return _missing_cell(missing_inputs=["eps_cagr_percent_points"], message="SEC fact unavailable", unit="multiple")
    if market_cap is None or market_cap <= 0:
        return _not_applicable_cell(reason="market_cap_unavailable", unit="multiple")
    cash_dividends = base_metrics.cash_dividends or base_metrics.dividends_and_interest_paid
    div_pct = float(cash_dividends) / market_cap * 100 if cash_dividends is not None else 0.0
    eps_cagr_pct = float(eps_cagr_metric["value"])
    denominator = eps_cagr_pct + div_pct
    if denominator <= 0:
        return _not_applicable_cell(reason="CAGR+DivYield <= 0", unit="multiple", formula="PE / (CAGR + DivYield)")
    return _ready_cell(
        value=float(pe_metric["value"]) / denominator,
        unit="multiple",
        formula="PE / (CAGR_percent_points + div_yield_percent)",
    )


def _shareholder_return_metrics(
    base_metrics: FinancialMetric,
    oe_context: dict[str, Any],
    *,
    market_cap: Optional[float] = None,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    dividend_source = "primary"
    cash_dividends = base_metrics.cash_dividends
    if cash_dividends is None and base_metrics.dividends_and_interest_paid is not None:
        cash_dividends = base_metrics.dividends_and_interest_paid
        dividend_source = "fallback"
    if cash_dividends is None:
        results["cash_dividends"] = _not_applicable_cell(
            reason="no_dividends_paid",
            unit="currency",
        )
    else:
        results["cash_dividends"] = _ready_cell(
            value=float(cash_dividends),
            unit="currency",
            formula="SEC dividends cash outflow",
            metadata={"dividend_source": dividend_source},
        )

    buyback_cash = float(base_metrics.buyback_cash or 0)
    equity_issuance_cash = float(base_metrics.equity_issuance_cash or 0) - float(base_metrics.minority_equity_issuance or 0)
    net_buyback_cash = buyback_cash - equity_issuance_cash
    results["net_buyback_cash"] = _ready_cell(
        value=net_buyback_cash,
        unit="currency",
        formula="buyback_cash - (equity_issuance_cash - minority_equity_issuance)",
    )
    if market_cap is not None and market_cap > 0:
        div_amount = float(cash_dividends) if cash_dividends is not None else 0.0
        results["dividend_yield_percent"] = _ready_cell(
            value=div_amount / market_cap * 100,
            unit="percent",
            formula="cash_dividends / market_cap * 100",
            metadata={"market_cap": market_cap},
        )
        results["net_buyback_yield_percent"] = _ready_cell(
            value=net_buyback_cash / market_cap * 100,
            unit="percent",
            formula="net_buyback_cash / market_cap * 100",
        )
        results["total_shareholder_yield_percent"] = _ready_cell(
            value=(div_amount + net_buyback_cash) / market_cap * 100,
            unit="percent",
            formula="(cash_dividends + net_buyback_cash) / market_cap * 100",
        )
    else:
        results["dividend_yield_percent"] = _not_applicable_cell(reason="market_cap_unavailable", unit="percent")
        results["net_buyback_yield_percent"] = _not_applicable_cell(reason="market_cap_unavailable", unit="percent")
        results["total_shareholder_yield_percent"] = _not_applicable_cell(reason="market_cap_unavailable", unit="percent")
    if cash_dividends is None:
        results["dividend_payout_ratio_percent"] = _not_applicable_cell(
            reason="no_dividends_paid",
            unit="percent",
        )
    elif base_metrics.net_income in (None, 0):
        results["dividend_payout_ratio_percent"] = _missing_cell(
            missing_inputs=["net_income_attributable_to_parent"],
            message="SEC fact unavailable",
            unit="percent",
        )
    else:
        results["dividend_payout_ratio_percent"] = _ready_cell(
            value=float(cash_dividends) / float(base_metrics.net_income) * 100,
            unit="percent",
            formula="cash_dividends / net_income * 100",
        )

    if oe_context.get("status") == "not_applicable":
        results["borrow_to_dividend_risk"] = _not_applicable_cell(
            reason=oe_context.get("reason", "insufficient_history"),
            unit="flag",
        )
    elif oe_context.get("status") != "ready":
        results["borrow_to_dividend_risk"] = _missing_cell(
            missing_inputs=["owner_earnings"],
            message="SEC fact unavailable",
            unit="flag",
        )
    elif base_metrics.current_debt_maturities is None or cash_dividends is None or base_metrics.capex is None:
        results["borrow_to_dividend_risk"] = _missing_cell(
            missing_inputs=["current_debt_maturities", "cash_dividends"],
            message="SEC fact unavailable",
            unit="flag",
        )
    else:
        distributable = (
            float(oe_context["avg_oe_per_share"]) * float(base_metrics.shares_outstanding or 0)
            - abs(float(base_metrics.capex))
            - float(base_metrics.current_debt_maturities)
        )
        results["borrow_to_dividend_risk"] = _ready_cell(
            value=1.0 if distributable <= float(cash_dividends) else 0.0,
            unit="flag",
            formula="(OE - capex - current_debt_maturities) <= cash_dividends",
            metadata={"distributable_profit_proxy": distributable},
        )
    return results


def _quality_risk_metrics(base_metrics: FinancialMetric) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if base_metrics.pledged_shares is None or base_metrics.total_shares in (None, 0):
        results["pledge_ratio_percent"] = _missing_cell(
            missing_inputs=["pledged_shares", "total_shares"],
            message="SEC fact unavailable",
            unit="percent",
        )
    else:
        results["pledge_ratio_percent"] = _ready_cell(
            value=float(base_metrics.pledged_shares) / float(base_metrics.total_shares) * 100,
            unit="percent",
            formula="pledged_shares / total_shares * 100",
        )

    effective_ebt = _pretax_income_value(base_metrics)
    if base_metrics.income_tax_expense is None or effective_ebt in (None, 0):
        missing_inputs = []
        if base_metrics.income_tax_expense is None:
            missing_inputs.append("income_tax_expense")
        if effective_ebt in (None, 0):
            missing_inputs.append("pretax_income")
        results["book_effective_tax_rate_percent"] = _missing_cell(
            missing_inputs=missing_inputs or ["income_tax_expense", "pretax_income"],
            message="SEC fact unavailable",
            unit="percent",
        )
        results["book_tax_to_theoretical_25_ratio_percent"] = _missing_cell(
            missing_inputs=missing_inputs or ["income_tax_expense", "pretax_income"],
            message="SEC fact unavailable",
            unit="percent",
        )
        results["cash_taxes_to_theoretical_25_ratio_percent"] = _missing_cell(
            missing_inputs=["cash_taxes_paid", *(["pretax_income"] if effective_ebt in (None, 0) else [])],
            message="SEC fact unavailable",
            unit="percent",
        )
    else:
        ebt = float(effective_ebt)
        tax = float(base_metrics.income_tax_expense)
        theoretical_25 = ebt * 0.25
        results["book_effective_tax_rate_percent"] = _ready_cell(
            value=tax / ebt * 100,
            unit="percent",
            formula="income_tax_expense / EBT * 100",
        )
        results["theoretical_tax_at_25_percent"] = _ready_cell(
            value=theoretical_25,
            unit="currency",
            formula="EBT * 25%",
        )
        results["theoretical_tax_at_15_percent"] = _ready_cell(
            value=ebt * 0.15,
            unit="currency",
            formula="EBT * 15%",
        )
        results["book_tax_to_theoretical_25_ratio_percent"] = _ready_cell(
            value=tax / theoretical_25 * 100 if theoretical_25 != 0 else 0.0,
            unit="percent",
            formula="income_tax_expense / (EBT*25%) * 100",
        )
        if base_metrics.cash_taxes_paid is None:
            results["cash_taxes_to_theoretical_25_ratio_percent"] = _missing_cell(
                missing_inputs=["cash_taxes_paid"],
                message="SEC fact unavailable",
                unit="percent",
            )
        else:
            results["cash_taxes_to_theoretical_25_ratio_percent"] = _ready_cell(
                value=float(base_metrics.cash_taxes_paid) / theoretical_25 * 100 if theoretical_25 != 0 else 0.0,
                unit="percent",
                formula="cash_taxes_paid / (EBT*25%) * 100",
            )

    equity = base_metrics.shareholders_equity or base_metrics.parent_shareholders_equity
    if equity in (None, 0):
        results["goodwill_to_equity_percent"] = _missing_cell(
            missing_inputs=["equity_denominator"],
            message="SEC fact unavailable",
            unit="percent",
        )
    elif base_metrics.goodwill is None:
        results["goodwill_to_equity_percent"] = _not_applicable_cell(
            reason="goodwill_not_disclosed",
            unit="percent",
        )
    else:
        results["goodwill_to_equity_percent"] = _ready_cell(
            value=float(base_metrics.goodwill) / float(equity) * 100,
            unit="percent",
            formula="goodwill / equity * 100",
        )

    ocf_to_income = _safe_ratio(base_metrics.operating_cash_flow, base_metrics.net_income)
    if ocf_to_income is None:
        results["ocf_to_net_income"] = _missing_cell(
            missing_inputs=["operating_cash_flow", "net_income"],
            message="SEC fact unavailable",
            unit="multiple",
        )
    else:
        results["ocf_to_net_income"] = _ready_cell(
            value=ocf_to_income,
            unit="multiple",
            formula="operating_cash_flow / net_income",
        )

    results["roic"] = _roic_metric(base_metrics)
    return results


def _roic_metric(base_metrics: FinancialMetric) -> dict[str, Any]:
    if base_metrics.operating_income is None:
        return _missing_cell(missing_inputs=["operating_income"], message="SEC fact unavailable", unit="percent")
    interest_expense = float(base_metrics.interest_expense or 0)
    ebit = float(base_metrics.operating_income) + max(interest_expense, 0)

    used_default_tax = False
    if base_metrics.income_tax_expense is None or base_metrics.pretax_income in (None, 0):
        effective_tax_rate = 0.25
        used_default_tax = True
    else:
        effective_tax_rate = float(base_metrics.income_tax_expense) / float(base_metrics.pretax_income)
        effective_tax_rate = min(max(effective_tax_rate, 0.0), 0.50)

    nopat = ebit * (1 - effective_tax_rate)
    interest_bearing_debt = (
        float(base_metrics.short_term_borrowings or 0)
        + float(base_metrics.current_portion_of_long_term_debt or 0)
        + float(base_metrics.long_term_debt or 0)
        + float(base_metrics.bonds_payable or 0)
        + float(base_metrics.lease_liabilities or 0)
    )
    parent_equity = float(base_metrics.parent_shareholders_equity or base_metrics.shareholders_equity or 0)
    cash = float(base_metrics.cash_and_equivalents or 0)
    invested_capital = interest_bearing_debt + parent_equity - cash
    if invested_capital <= 0:
        return _not_applicable_cell(reason="invested_capital <= 0", unit="percent", formula="NOPAT / invested_capital")
    return _ready_cell(
        value=nopat / invested_capital * 100,
        unit="percent",
        formula="NOPAT / invested_capital * 100",
        metadata={"effective_tax_rate_default_used": used_default_tax},
        parameters={"effective_tax_rate": effective_tax_rate},
    )


def _pricing_power_metrics(base_metrics: FinancialMetric, history: list[FinancialMetric]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    gross_profit_value = _gross_profit_value(base_metrics)
    results["gross_margin_percent"] = _ratio_percent_metric_with_labels(
        gross_profit_value,
        base_metrics.revenue,
        formula="gross_profit / revenue * 100",
        numerator_label="gross_profit",
    )
    results["operating_margin_percent"] = _ratio_percent_metric(base_metrics.operating_income, base_metrics.revenue, "operating_income / revenue * 100")
    results["net_margin_percent"] = _ratio_percent_metric(base_metrics.net_income, base_metrics.revenue, "net_income / revenue * 100")

    for field_name, key in [
        ("revenue", "revenue_3y_cagr_percent_points"),
        ("gross_profit", "gross_profit_3y_cagr_percent_points"),
        ("operating_income", "operating_income_3y_cagr_percent_points"),
        ("net_income", "net_income_3y_cagr_percent_points"),
    ]:
        results[key] = _cagr_metric(history, field_name, target_years=3)

    for field_name, key in [
        ("revenue", "revenue_yoy_percent"),
        ("gross_profit", "gross_profit_yoy_percent"),
        ("operating_income", "operating_income_yoy_percent"),
        ("net_income", "net_income_yoy_percent"),
    ]:
        results[key] = _yoy_metric(history, field_name)

    margin_history = _margin_series(history)
    for margin_name, key in [
        ("gross_margin_percent", "gross_margin_yoy_percent"),
        ("operating_margin_percent", "operating_margin_yoy_percent"),
        ("net_margin_percent", "net_margin_yoy_percent"),
    ]:
        results[key] = _yoy_from_series(margin_history.get(margin_name, []), key)
    return results


def _ratio_percent_metric(numerator: Optional[float], denominator: Optional[float], formula: str) -> dict[str, Any]:
    return _ratio_percent_metric_with_labels(numerator, denominator, formula=formula)


def _ratio_percent_metric_with_labels(
    numerator: Optional[float],
    denominator: Optional[float],
    *,
    formula: str,
    numerator_label: str = "numerator",
    denominator_label: str = "revenue",
) -> dict[str, Any]:
    if denominator in (None, 0):
        return _not_applicable_cell(reason=f"{denominator_label} <= 0 or missing", unit="percent", formula=formula)
    if numerator is None:
        return _missing_cell(
            missing_inputs=[numerator_label],
            message="SEC fact unavailable",
            unit="percent",
        )
    return _ready_cell(value=float(numerator) / float(denominator) * 100, unit="percent", formula=formula)


def _series_with_fallback(history: list[FinancialMetric], fields: list[str]) -> list[tuple[str, float]]:
    series: list[tuple[str, float]] = []
    for metric in history:
        if not metric.period_end:
            continue
        value: Optional[float] = None
        for field_name in fields:
            if field_name == "gross_profit":
                candidate = _gross_profit_value(metric)
            elif field_name == "pretax_income":
                candidate = _pretax_income_value(metric)
            else:
                candidate = getattr(metric, field_name, None)
            if candidate is not None:
                value = float(candidate)
                break
        if value is None:
            continue
        series.append((metric.period_end, value))
    return series


def _cagr_metric(history: list[FinancialMetric], field_name: str, target_years: int) -> dict[str, Any]:
    series = _series_with_fallback(history, [field_name])
    if len(series) < 2:
        return _not_applicable_cell(reason="insufficient_history", unit="percent_points")
    end_period, end_value = series[-1]
    if end_value <= 0:
        return _not_applicable_cell(reason=f"{field_name} ending value <= 0", unit="percent_points")
    end_date = _parse_iso_date(end_period)
    if end_date is None:
        return _missing_cell(missing_inputs=["period_end"], message="SEC fact unavailable", unit="percent_points")
    candidates = []
    for period, value in series[:-1]:
        if value <= 0:
            continue
        start_date = _parse_iso_date(period)
        if start_date is None:
            continue
        years = (end_date - start_date).days / 365.25
        if years >= 1:
            candidates.append((abs(years - target_years), years, period, value))
    if not candidates:
        return _not_applicable_cell(reason="insufficient_history", unit="percent_points")
    _, years, start_period, start_value = min(candidates, key=lambda item: item[0])
    cagr = (end_value / start_value) ** (1 / years) - 1
    return _ready_cell(
        value=cagr * 100,
        unit="percent_points",
        formula=f"CAGR({field_name}) * 100",
        lookback={"start_period": start_period, "end_period": end_period, "years": years},
    )


def _yoy_metric(history: list[FinancialMetric], field_name: str) -> dict[str, Any]:
    series = _series_with_fallback(history, [field_name])
    return _yoy_from_series(series, field_name)


def _margin_series(history: list[FinancialMetric]) -> dict[str, list[tuple[str, float]]]:
    output = {
        "gross_margin_percent": [],
        "operating_margin_percent": [],
        "net_margin_percent": [],
    }
    for metric in history:
        if not metric.period_end or metric.revenue in (None, 0):
            continue
        revenue = float(metric.revenue)
        gross_profit_value = _gross_profit_value(metric)
        if gross_profit_value is not None:
            output["gross_margin_percent"].append((metric.period_end, gross_profit_value / revenue * 100))
        if metric.operating_income is not None:
            output["operating_margin_percent"].append((metric.period_end, float(metric.operating_income) / revenue * 100))
        if metric.net_income is not None:
            output["net_margin_percent"].append((metric.period_end, float(metric.net_income) / revenue * 100))
    return output


def _gross_profit_value(metric: FinancialMetric) -> Optional[float]:
    if metric.gross_profit is not None:
        return float(metric.gross_profit)
    if metric.revenue is not None and metric.cost_of_revenue is not None:
        return float(metric.revenue) - float(metric.cost_of_revenue)
    return None


def _pretax_income_value(metric: FinancialMetric) -> Optional[float]:
    if metric.pretax_income is not None:
        return float(metric.pretax_income)
    if metric.net_income is not None and metric.income_tax_expense is not None:
        return float(metric.net_income) + float(metric.income_tax_expense)
    return None


def _yoy_from_series(series: list[tuple[str, float]], label: str) -> dict[str, Any]:
    if len(series) < 2:
        return _not_applicable_cell(reason="insufficient_history", unit="percent")
    (prev_period, prev_value), (curr_period, curr_value) = series[-2], series[-1]
    if prev_value == 0:
        return _not_applicable_cell(reason="prior_year == 0", unit="percent", formula="(current-prior)/prior")
    yoy = (curr_value - prev_value) / prev_value * 100
    return _ready_cell(
        value=yoy,
        unit="percent",
        formula="(current - prior) / prior * 100",
        lookback={"prior_period": prev_period, "current_period": curr_period},
    )


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
