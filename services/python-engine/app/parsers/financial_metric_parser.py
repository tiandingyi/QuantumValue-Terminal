from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from app.models.financial_metric import FinancialMetric
from app.providers.sec_metric_store import CompanyFactsMetricStore


logger = logging.getLogger(__name__)

METRIC_TAGS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "RevenueFromContractWithCustomer",
        "TotalRevenues",
        "SalesRevenueNet",
        "Revenues",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "NetCashProvidedByUsedInOperatingActivities",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpendituresIncurredButNotYetPaid",
        "PropertyPlantAndEquipmentAdditions",
    ],
    "depreciation_and_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
        "DepreciationAndAmortization",
    ],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "shareholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "long_term_debt": [
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ],
    "eps_diluted": [
        "EarningsPerShareDiluted",
        "DilutedEarningsPerShare",
        "IncomeLossFromContinuingOperationsPerDilutedShare",
        "BasicAndDilutedEarningsPerShare",
    ],
    "shares_outstanding": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ],
}

UNIT_MULTIPLIERS = {
    "thousand": 1_000,
    "thousands": 1_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "billion": 1_000_000_000,
    "billions": 1_000_000_000,
}

ANCHOR_TAGS = METRIC_TAGS["revenue"] + METRIC_TAGS["net_income"]


def parse_financial_metric(company_facts: dict[str, Any]) -> FinancialMetric:
    """Parse raw SEC company facts into a standardized Pydantic model."""
    store = CompanyFactsMetricStore(company_facts)
    anchor = _resolve_anchor(store)

    values: dict[str, Any] = {"source_tags": {}}
    aligned_facts: list[dict[str, Any]] = []

    for field_name, metric_tags in METRIC_TAGS.items():
        metric = _safe_lookup(store, field_name, metric_tags, anchor)
        if metric is None:
            values[field_name] = None
            continue

        tag_name, fact = metric
        values[field_name] = _normalize_absolute_value(fact.get("val"), fact.get("unit"))
        values["source_tags"][field_name] = tag_name
        aligned_facts.append(fact)

    if aligned_facts:
        values["period_end"] = max(str(fact["end"]) for fact in aligned_facts if fact.get("end"))
        filed_values = [str(fact["filed"]) for fact in aligned_facts if fact.get("filed")]
        values["filed_at"] = max(filed_values) if filed_values else None

    return FinancialMetric.model_validate(values)


def _resolve_anchor(
    store: CompanyFactsMetricStore,
) -> Optional[dict[str, Any]]:
    try:
        _, anchor = store.anchor_metric(ANCHOR_TAGS)
        return anchor
    except ValueError:
        logger.warning("FinancialMetric parser could not resolve an anchor filing period; falling back to latest facts.")
        return None


def _safe_lookup(
    store: CompanyFactsMetricStore,
    field_name: str,
    metric_tags: list[str],
    anchor: Optional[dict[str, Any]],
) -> Optional[Tuple[str, dict[str, Any]]]:
    try:
        if anchor is not None:
            return store.metric_for_anchor_period(metric_tags, anchor=anchor)
        return store.latest_metric_from_candidates(metric_tags)
    except ValueError:
        logger.warning("FinancialMetric parser missing metric '%s'; defaulting to None.", field_name)
        return None


def _normalize_absolute_value(value: Any, unit_hint: Any) -> Optional[float]:
    if value is None:
        return None

    numeric_value = float(value)
    normalized_unit = str(unit_hint or "").strip().lower()
    multiplier = UNIT_MULTIPLIERS.get(normalized_unit, 1)
    absolute_value = numeric_value * multiplier

    if absolute_value.is_integer():
        return float(int(absolute_value))
    return absolute_value
