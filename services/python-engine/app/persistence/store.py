from __future__ import annotations

from typing import Any, Optional, Protocol

from app.models.financial_metric import FinancialMetric
from app.persistence.types import FilingMetadata
from app.providers.sec_types import CompanyLookup, DerivedMetric


class PersistenceStore(Protocol):
    """Repository interface for database-backed SEC persistence."""

    def upsert_sync_status(
        self,
        company: CompanyLookup,
        task_type: str,
        status: str,
        last_error: Optional[str] = None,
    ) -> None:
        ...

    def persist_filing_bundle(
        self,
        company: CompanyLookup,
        filing: FilingMetadata,
        base_metrics: FinancialMetric,
        derived_metrics: dict[str, DerivedMetric],
    ) -> dict[str, Any]:
        ...
