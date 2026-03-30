from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time
from typing import Any, Callable, Optional

import requests


SEC_BASE_URL = "https://data.sec.gov"
SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT = "Dingyi Quant Research data-ops@dingyi-analytics.net"
DEFAULT_RATE_LIMIT_DELAY = 0.15


@dataclass(frozen=True)
class CompanyLookup:
    ticker: str
    cik: str
    name: str


@dataclass(frozen=True)
class CompanyDataBundle:
    company: CompanyLookup
    submissions: dict[str, Any]
    company_facts: dict[str, Any]


@dataclass(frozen=True)
class DerivedMetric:
    name: str
    value: float
    unit: str
    end: str
    filed: Optional[str]
    source: str


class USProvider:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        request_delay: float = DEFAULT_RATE_LIMIT_DELAY,
        timeout: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session = session or requests.Session()
        self._request_delay = request_delay
        self._timeout = timeout
        self._sleep = sleep_fn
        self._clock = clock_fn
        self._last_request_at: Optional[float] = None
        self._ticker_cache: Optional[dict[str, CompanyLookup]] = None

    def fetch_company_data(self, ticker: str) -> CompanyDataBundle:
        company = self.resolve_ticker(ticker)
        submissions = self.get_submissions(company.cik)
        company_facts = self.get_company_facts(company.cik)
        return CompanyDataBundle(
            company=company,
            submissions=submissions,
            company_facts=company_facts,
        )

    def resolve_ticker(self, ticker: str) -> CompanyLookup:
        normalized_ticker = normalize_ticker(ticker)
        ticker_map = self._load_ticker_map()
        company = ticker_map.get(normalized_ticker)
        if company is None:
            raise ValueError(f"Ticker {normalized_ticker} was not found in SEC company_tickers.json.")
        return company

    def get_submissions(self, cik: str) -> dict[str, Any]:
        padded_cik = pad_cik(cik)
        return self._get_json(f"{SEC_BASE_URL}/submissions/CIK{padded_cik}.json")

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        padded_cik = pad_cik(cik)
        return self._get_json(f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{padded_cik}.json")

    def extract_latest_metric(
        self,
        company_facts: dict[str, Any],
        metric_name: str,
        taxonomy: str = "us-gaap",
    ) -> dict[str, Any]:
        candidates = self._collect_metric_candidates(company_facts, metric_name, taxonomy=taxonomy)
        if not candidates:
            raise ValueError(f"Metric {taxonomy}:{metric_name} does not contain any dated values.")

        candidates.sort(
            key=lambda item: (
                _parse_date(item.get("end")),
                _parse_date(item.get("filed")),
            ),
            reverse=True,
        )
        return candidates[0]

    def extract_metric_for_anchor_period(
        self,
        company_facts: dict[str, Any],
        metric_names: list[str],
        anchor: dict[str, Any],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict[str, Any]]:
        anchor_end = anchor.get("end")
        anchor_form = anchor.get("form")
        anchor_fp = anchor.get("fp")
        anchor_fy = anchor.get("fy")

        best_fallback: Optional[tuple[str, dict[str, Any]]] = None
        for metric_name in metric_names:
            candidates = self._collect_metric_candidates(company_facts, metric_name, taxonomy=taxonomy)
            if not candidates:
                continue

            exact_matches = [
                item
                for item in candidates
                if item.get("end") == anchor_end
                and (anchor_form is None or item.get("form") == anchor_form)
                and (anchor_fp is None or item.get("fp") == anchor_fp)
            ]
            if exact_matches:
                exact_matches.sort(
                    key=lambda item: (_parse_date(item.get("filed")), _parse_date(item.get("end"))),
                    reverse=True,
                )
                return metric_name, exact_matches[0]

            same_end_matches = [item for item in candidates if item.get("end") == anchor_end]
            if same_end_matches:
                same_end_matches.sort(
                    key=lambda item: (
                        _score_anchor_match(item, anchor_fy=anchor_fy, anchor_fp=anchor_fp, anchor_form=anchor_form),
                        _parse_date(item.get("filed")),
                    ),
                    reverse=True,
                )
                return metric_name, same_end_matches[0]

            if best_fallback is None:
                candidates.sort(
                    key=lambda item: (
                        _score_anchor_match(item, anchor_fy=anchor_fy, anchor_fp=anchor_fp, anchor_form=anchor_form),
                        _parse_date(item.get("end")),
                        _parse_date(item.get("filed")),
                    ),
                    reverse=True,
                )
                best_fallback = (metric_name, candidates[0])

        if best_fallback is not None:
            return best_fallback

        raise ValueError(
            f"None of the candidate metrics were found for taxonomy {taxonomy}: {', '.join(metric_names)}."
        )

    def extract_anchor_metric(
        self,
        company_facts: dict[str, Any],
        metric_names: list[str],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict[str, Any]]:
        best_match: Optional[tuple[str, dict[str, Any]]] = None
        for metric_name in metric_names:
            candidates = self._collect_metric_candidates(company_facts, metric_name, taxonomy=taxonomy)
            if not candidates:
                continue

            candidates.sort(
                key=lambda item: (
                    _is_annual_filing(item),
                    _parse_date(item.get("end")),
                    _parse_date(item.get("filed")),
                ),
                reverse=True,
            )
            candidate = candidates[0]
            if best_match is None:
                best_match = (metric_name, candidate)
                continue
            if (
                _is_annual_filing(candidate),
                _parse_date(candidate.get("end")),
                _parse_date(candidate.get("filed")),
            ) > (
                _is_annual_filing(best_match[1]),
                _parse_date(best_match[1].get("end")),
                _parse_date(best_match[1].get("filed")),
            ):
                best_match = (metric_name, candidate)

        if best_match is None:
            raise ValueError(
                f"None of the candidate metrics were found for taxonomy {taxonomy}: {', '.join(metric_names)}."
            )
        return best_match

    def _collect_metric_candidates(
        self,
        company_facts: dict[str, Any],
        metric_name: str,
        taxonomy: str = "us-gaap",
    ) -> list[dict[str, Any]]:
        taxonomy_facts = company_facts.get("facts", {}).get(taxonomy, {})
        metric_node = taxonomy_facts.get(metric_name)
        if not metric_node:
            return []

        units = metric_node.get("units", {})
        candidates: list[dict[str, Any]] = []
        for unit_name, entries in units.items():
            for entry in entries:
                if "val" not in entry or "end" not in entry:
                    continue
                candidate = dict(entry)
                candidate["unit"] = unit_name
                candidates.append(candidate)
        return candidates

    def extract_latest_metric_from_candidates(
        self,
        company_facts: dict[str, Any],
        metric_names: list[str],
        taxonomy: str = "us-gaap",
    ) -> tuple[str, dict[str, Any]]:
        for metric_name in metric_names:
            try:
                return metric_name, self.extract_latest_metric(company_facts, metric_name, taxonomy=taxonomy)
            except ValueError:
                continue

        raise ValueError(
            f"None of the candidate metrics were found for taxonomy {taxonomy}: {', '.join(metric_names)}."
        )

    def extract_requested_financials(self, company_facts: dict[str, Any]) -> dict[str, DerivedMetric]:
        anchor_tag, anchor = self.extract_anchor_metric(
            company_facts,
            [
                "NetIncomeLoss",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "Revenues",
            ],
        )
        revenue_tag, revenue = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "Revenues",
            ],
            anchor=anchor,
        )
        net_income_tag, net_income = self.extract_metric_for_anchor_period(
            company_facts,
            ["NetIncomeLoss", "ProfitLoss"],
            anchor=anchor,
        )
        ebit_tag, ebit = self.extract_metric_for_anchor_period(
            company_facts,
            ["OperatingIncomeLoss"],
            anchor=anchor,
        )
        interest_expense_tag, interest_expense = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "InterestExpenseAndDebtExpense",
                "InterestExpense",
            ],
            anchor=anchor,
        )
        operating_cash_flow_tag, operating_cash_flow = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
                "NetCashProvidedByUsedInOperatingActivities",
            ],
            anchor=anchor,
        )
        capex_tag, capex = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "CapitalExpendituresIncurredButNotYetPaid",
                "PropertyPlantAndEquipmentAdditions",
            ],
            anchor=anchor,
        )
        equity_tag, equity = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ],
            anchor=anchor,
        )
        cash_tag, cash = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ],
            anchor=anchor,
        )
        debt_tag, debt = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "LongTermDebtAndCapitalLeaseObligations",
                "LongTermDebtNoncurrent",
                "LongTermDebt",
            ],
            anchor=anchor,
        )
        current_debt_tag, current_debt = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "ShortTermBorrowings",
                "LongTermDebtCurrent",
                "CommercialPaper",
            ],
            anchor=anchor,
        )
        gross_profit_tag, gross_profit = self.extract_metric_for_anchor_period(
            company_facts,
            ["GrossProfit"],
            anchor=anchor,
        )
        tax_expense_tag, tax_expense = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "IncomeTaxExpenseBenefit",
                "IncomeTaxes",
            ],
            anchor=anchor,
        )
        pretax_income_tag, pretax_income = self.extract_metric_for_anchor_period(
            company_facts,
            [
                "IncomeBeforeTaxExpenseBenefit",
                "PretaxIncome",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            ],
            anchor=anchor,
        )

        latest_period = _latest_period_end(
            [
                revenue,
                net_income,
                ebit,
                interest_expense,
                operating_cash_flow,
                capex,
                equity,
                cash,
                debt,
                current_debt,
                gross_profit,
                tax_expense,
                pretax_income,
            ]
        )
        latest_filed = _latest_filed(
            [
                revenue,
                net_income,
                ebit,
                interest_expense,
                operating_cash_flow,
                capex,
                equity,
                cash,
                debt,
                current_debt,
                gross_profit,
                tax_expense,
                pretax_income,
            ]
        )

        effective_tax_rate = 0.0
        pretax_value = _as_float(pretax_income["val"])
        if pretax_value != 0:
            effective_tax_rate = _as_float(tax_expense["val"]) / pretax_value

        fcf_value = _as_float(operating_cash_flow["val"]) - abs(_as_float(capex["val"]))
        nopat_value = _as_float(ebit["val"]) * (1 - effective_tax_rate)
        invested_capital_value = (
            _as_float(equity["val"]) + _as_float(debt["val"]) + _as_float(current_debt["val"]) - _as_float(cash["val"])
        )
        gross_margin_value = _as_float(gross_profit["val"]) / _as_float(revenue["val"])

        return {
            "fcf": DerivedMetric(
                name="Free Cash Flow",
                value=fcf_value,
                unit=operating_cash_flow["unit"],
                end=latest_period,
                filed=latest_filed,
                source=f"{operating_cash_flow_tag} - abs({capex_tag})",
            ),
            "net_income": DerivedMetric(
                name="Net Income",
                value=_as_float(net_income["val"]),
                unit=net_income["unit"],
                end=net_income["end"],
                filed=net_income.get("filed"),
                source=net_income_tag,
            ),
            "nopat": DerivedMetric(
                name="NOPAT",
                value=nopat_value,
                unit=ebit["unit"],
                end=latest_period,
                filed=latest_filed,
                source=f"{ebit_tag} * (1 - {tax_expense_tag}/{pretax_income_tag})",
            ),
            "invested_capital": DerivedMetric(
                name="Invested Capital",
                value=invested_capital_value,
                unit=equity["unit"],
                end=latest_period,
                filed=latest_filed,
                source=f"{equity_tag} + {debt_tag} + {current_debt_tag} - {cash_tag}",
            ),
            "gross_margin": DerivedMetric(
                name="Gross Margin",
                value=gross_margin_value,
                unit="ratio",
                end=latest_period,
                filed=latest_filed,
                source=f"{gross_profit_tag}/{revenue_tag}",
            ),
            "ebit": DerivedMetric(
                name="EBIT",
                value=_as_float(ebit["val"]),
                unit=ebit["unit"],
                end=ebit["end"],
                filed=ebit.get("filed"),
                source=ebit_tag,
            ),
            "interest_expense": DerivedMetric(
                name="Interest Expense",
                value=_as_float(interest_expense["val"]),
                unit=interest_expense["unit"],
                end=interest_expense["end"],
                filed=interest_expense.get("filed"),
                source=interest_expense_tag,
            ),
        }

    def _load_ticker_map(self) -> dict[str, CompanyLookup]:
        if self._ticker_cache is not None:
            return self._ticker_cache

        payload = self._get_json(SEC_TICKER_MAP_URL)
        ticker_map: dict[str, CompanyLookup] = {}
        for item in payload.values():
            ticker = normalize_ticker(item["ticker"])
            ticker_map[ticker] = CompanyLookup(
                ticker=ticker,
                cik=pad_cik(item["cik_str"]),
                name=item["title"],
            )

        self._ticker_cache = ticker_map
        return ticker_map

    def _get_json(self, url: str) -> dict[str, Any]:
        self._throttle()
        response = self._session.get(
            url,
            headers={
                "User-Agent": SEC_USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        self._last_request_at = self._clock()
        return response.json()

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return

        elapsed = self._clock() - self._last_request_at
        remaining = self._request_delay - elapsed
        if remaining > 0:
            self._sleep(remaining)


def normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized:
        raise ValueError("Ticker is required.")
    return normalized


def pad_cik(cik: str | int) -> str:
    digits_only = str(cik).strip()
    if not digits_only:
        raise ValueError("CIK is required.")
    return digits_only.zfill(10)


def _parse_date(value: Any) -> datetime:
    if not value:
        return datetime.min
    return datetime.strptime(str(value), "%Y-%m-%d")


def _as_float(value: Any) -> float:
    return float(value)


def _latest_period_end(entries: list[dict[str, Any]]) -> str:
    return max(str(entry["end"]) for entry in entries if entry.get("end"))


def _latest_filed(entries: list[dict[str, Any]]) -> Optional[str]:
    filed_values = [str(entry["filed"]) for entry in entries if entry.get("filed")]
    if not filed_values:
        return None
    return max(filed_values)


def _is_annual_filing(entry: dict[str, Any]) -> bool:
    return entry.get("form") == "10-K" or entry.get("fp") == "FY"


def _score_anchor_match(
    entry: dict[str, Any],
    anchor_fy: Any,
    anchor_fp: Any,
    anchor_form: Any,
) -> int:
    score = 0
    if anchor_fy is not None and entry.get("fy") == anchor_fy:
        score += 2
    if anchor_fp is not None and entry.get("fp") == anchor_fp:
        score += 2
    if anchor_form is not None and entry.get("form") == anchor_form:
        score += 1
    if _is_annual_filing(entry):
        score += 1
    return score
