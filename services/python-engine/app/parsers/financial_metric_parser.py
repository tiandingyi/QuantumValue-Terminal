from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Optional, Tuple

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
DEFAULT_REQUIRED_METRIC_FIELDS = frozenset(METRIC_TAGS.keys())


@dataclass(frozen=True)
class FinancialMetricMappingError(ValueError):
    field_name: str
    candidate_tags: list[str]
    ticker: Optional[str] = None
    cik: Optional[str] = None
    period_context: Optional[dict[str, Any]] = None

    def __str__(self) -> str:
        context_parts = [
            f"field={self.field_name}",
            f"candidate_tags={self.candidate_tags}",
        ]
        if self.ticker:
            context_parts.append(f"ticker={self.ticker}")
        if self.cik:
            context_parts.append(f"cik={self.cik}")
        if self.period_context:
            context_parts.append(f"period_context={self.period_context}")
        return "Missing required SEC financial fact mapping (" + ", ".join(context_parts) + ")"


def parse_financial_metric(
    company_facts: dict[str, Any],
    *,
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
    required_fields: Optional[Iterable[str]] = None,
) -> FinancialMetric:
    """Parse raw SEC company facts into a standardized Pydantic model."""
    store = CompanyFactsMetricStore(company_facts)
    anchor = _resolve_anchor(store)
    required_field_names = set(required_fields) if required_fields is not None else set(DEFAULT_REQUIRED_METRIC_FIELDS)
    unknown_required_fields = required_field_names - set(METRIC_TAGS)
    if unknown_required_fields:
        raise ValueError(f"Unknown required FinancialMetric fields: {sorted(unknown_required_fields)}")

    values: dict[str, Any] = {"source_tags": {}}
    aligned_facts: list[dict[str, Any]] = []

    for field_name, metric_tags in METRIC_TAGS.items():
        metric = _safe_lookup(store, field_name, metric_tags, anchor)
        if metric is None:
            if field_name in required_field_names:
                raise FinancialMetricMappingError(
                    field_name=field_name,
                    candidate_tags=metric_tags,
                    ticker=ticker,
                    cik=cik,
                    period_context=_period_context(anchor),
                )
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


def _period_context(anchor: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if anchor is None:
        return None

    return {
        key: anchor.get(key)
        for key in ("end", "filed", "form", "fy", "fp")
        if anchor.get(key) is not None
    }


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
