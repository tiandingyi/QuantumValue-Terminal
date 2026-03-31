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
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    capex: Optional[float] = None
    depreciation_and_amortization: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    shareholders_equity: Optional[float] = None
    long_term_debt: Optional[float] = None
    eps_diluted: Optional[float] = None
    shares_outstanding: Optional[float] = None
    source_tags: dict[str, str] = Field(default_factory=dict)
