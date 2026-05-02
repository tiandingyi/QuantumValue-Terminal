from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FinancialMetric(BaseModel):
    """Canonical base-fact model used before any downstream investing calculations."""

    model_config = ConfigDict(extra="forbid")

    period_end: Optional[str] = None
    filed_at: Optional[str] = None
    revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    depreciation_and_amortization: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    shareholders_equity: Optional[float] = None
    long_term_debt: Optional[float] = None
    short_term_borrowings: Optional[float] = None
    current_portion_of_long_term_debt: Optional[float] = None
    bonds_payable: Optional[float] = None
    lease_liabilities: Optional[float] = None
    eps_diluted: Optional[float] = None
    eps_basic: Optional[float] = None
    real_eps: Optional[float] = None
    shares_outstanding: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    current_debt: Optional[float] = None
    interest_expense: Optional[float] = None
    income_tax_expense: Optional[float] = None
    pretax_income: Optional[float] = None
    cash_taxes_paid: Optional[float] = None
    cash_dividends: Optional[float] = None
    dividends_and_interest_paid: Optional[float] = None
    buyback_cash: Optional[float] = None
    equity_issuance_cash: Optional[float] = None
    minority_equity_issuance: Optional[float] = None
    goodwill: Optional[float] = None
    parent_shareholders_equity: Optional[float] = None
    pledged_shares: Optional[float] = None
    total_shares: Optional[float] = None
    current_debt_maturities: Optional[float] = None
    source_tags: dict[str, str] = Field(default_factory=dict)
