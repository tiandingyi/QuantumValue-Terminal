from __future__ import annotations

from typing import Any

from app.providers.sec_metric_store import CompanyFactsMetricStore
from app.providers.sec_types import DerivedMetric
from app.providers.sec_utils import as_float, latest_filed, latest_period_end


def extract_requested_financials(company_facts: dict[str, Any]) -> dict[str, DerivedMetric]:
    """Derive the user-requested financial metrics from a period-aligned SEC fact set.

    Args:
        company_facts: Raw SEC company facts payload.

    Returns:
        dict[str, DerivedMetric]: Derived and directly selected metrics keyed by
        internal names such as ``fcf``, ``net_income``, and ``gross_margin``.

    Raises:
        ValueError: If any required base metric cannot be resolved from SEC data.
    """
    store = CompanyFactsMetricStore(company_facts)
    _, anchor = store.anchor_metric(
        [
            "NetIncomeLoss",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues",
        ]
    )
    revenue_tag, revenue = store.metric_for_anchor_period(
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues",
        ],
        anchor=anchor,
    )
    net_income_tag, net_income = store.metric_for_anchor_period(
        ["NetIncomeLoss", "ProfitLoss"],
        anchor=anchor,
    )
    ebit_tag, ebit = store.metric_for_anchor_period(
        ["OperatingIncomeLoss"],
        anchor=anchor,
    )
    interest_expense_tag, interest_expense = store.metric_for_anchor_period(
        ["InterestExpenseAndDebtExpense", "InterestExpense"],
        anchor=anchor,
    )
    operating_cash_flow_tag, operating_cash_flow = store.metric_for_anchor_period(
        [
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        anchor=anchor,
    )
    capex_tag, capex = store.metric_for_anchor_period(
        [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "CapitalExpendituresIncurredButNotYetPaid",
            "PropertyPlantAndEquipmentAdditions",
        ],
        anchor=anchor,
    )
    equity_tag, equity = store.metric_for_anchor_period(
        [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        anchor=anchor,
    )
    cash_tag, cash = store.metric_for_anchor_period(
        [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ],
        anchor=anchor,
    )
    debt_tag, debt = store.metric_for_anchor_period(
        [
            "LongTermDebtAndCapitalLeaseObligations",
            "LongTermDebtNoncurrent",
            "LongTermDebt",
        ],
        anchor=anchor,
    )
    current_debt_tag, current_debt = store.metric_for_anchor_period(
        [
            "ShortTermBorrowings",
            "LongTermDebtCurrent",
            "CommercialPaper",
        ],
        anchor=anchor,
    )
    gross_profit_tag, gross_profit = store.metric_for_anchor_period(
        ["GrossProfit"],
        anchor=anchor,
    )
    tax_expense_tag, tax_expense = store.metric_for_anchor_period(
        ["IncomeTaxExpenseBenefit", "IncomeTaxes"],
        anchor=anchor,
    )
    pretax_income_tag, pretax_income = store.metric_for_anchor_period(
        [
            "IncomeBeforeTaxExpenseBenefit",
            "PretaxIncome",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        ],
        anchor=anchor,
    )

    aligned_entries = [
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
    latest_period = latest_period_end(aligned_entries)
    latest_report_filed = latest_filed(aligned_entries)

    pretax_value = as_float(pretax_income["val"])
    effective_tax_rate = 0.0 if pretax_value == 0 else as_float(tax_expense["val"]) / pretax_value

    # Derived metrics stay explicit about their source formula so we can audit
    # the accounting path when company tags differ.
    fcf_value = as_float(operating_cash_flow["val"]) - abs(as_float(capex["val"]))
    nopat_value = as_float(ebit["val"]) * (1 - effective_tax_rate)
    invested_capital_value = (
        as_float(equity["val"]) + as_float(debt["val"]) + as_float(current_debt["val"]) - as_float(cash["val"])
    )
    gross_margin_value = as_float(gross_profit["val"]) / as_float(revenue["val"])

    return {
        "fcf": DerivedMetric(
            name="Free Cash Flow",
            value=fcf_value,
            unit=operating_cash_flow["unit"],
            end=latest_period,
            filed=latest_report_filed,
            source=f"{operating_cash_flow_tag} - abs({capex_tag})",
        ),
        "net_income": DerivedMetric(
            name="Net Income",
            value=as_float(net_income["val"]),
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
            filed=latest_report_filed,
            source=f"{ebit_tag} * (1 - {tax_expense_tag}/{pretax_income_tag})",
        ),
        "invested_capital": DerivedMetric(
            name="Invested Capital",
            value=invested_capital_value,
            unit=equity["unit"],
            end=latest_period,
            filed=latest_report_filed,
            source=f"{equity_tag} + {debt_tag} + {current_debt_tag} - {cash_tag}",
        ),
        "gross_margin": DerivedMetric(
            name="Gross Margin",
            value=gross_margin_value,
            unit="ratio",
            end=latest_period,
            filed=latest_report_filed,
            source=f"{gross_profit_tag}/{revenue_tag}",
        ),
        "ebit": DerivedMetric(
            name="EBIT",
            value=as_float(ebit["val"]),
            unit=ebit["unit"],
            end=ebit["end"],
            filed=ebit.get("filed"),
            source=ebit_tag,
        ),
        "interest_expense": DerivedMetric(
            name="Interest Expense",
            value=as_float(interest_expense["val"]),
            unit=interest_expense["unit"],
            end=interest_expense["end"],
            filed=interest_expense.get("filed"),
            source=interest_expense_tag,
        ),
    }
