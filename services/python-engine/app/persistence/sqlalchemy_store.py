from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import MetaData, Table, create_engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.models.financial_metric import FinancialMetric
from app.persistence.store import PersistenceStore
from app.persistence.types import FilingMetadata
from app.providers.sec_types import CompanyLookup, DerivedMetric


class SQLAlchemyPersistenceStore(PersistenceStore):
    """Persist SEC filing metadata and metrics using reflected PostgreSQL tables."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, future=True)
        self._metadata = MetaData()
        self._companies = Table("companies", self._metadata, autoload_with=self._engine)
        self._filings = Table("filings", self._metadata, autoload_with=self._engine)
        self._financial_metrics = Table("financial_metrics", self._metadata, autoload_with=self._engine)
        self._sync_status = Table("sync_status", self._metadata, autoload_with=self._engine)

    def upsert_sync_status(
        self,
        company: CompanyLookup,
        task_type: str,
        status: str,
        last_error: Optional[str] = None,
    ) -> None:
        company_id = self._upsert_company(company)

        statement = insert(self._sync_status).values(
            company_id=company_id,
            task_type=task_type,
            status=status,
            last_error=last_error,
            created_at=func.now(),
            updated_at=func.now(),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[self._sync_status.c.company_id, self._sync_status.c.task_type],
            set_={
                "status": status,
                "last_error": last_error,
                "updated_at": func.now(),
            },
        )

        with self._engine.begin() as connection:
            connection.execute(statement)

    def persist_filing_bundle(
        self,
        company: CompanyLookup,
        filing: FilingMetadata,
        base_metrics: FinancialMetric,
        derived_metrics: dict[str, DerivedMetric],
    ) -> dict[str, Any]:
        company_id = self._upsert_company(company)
        filing_id = self._upsert_filing(company_id, filing)
        metrics_id = self._upsert_metrics(filing_id, base_metrics, derived_metrics)
        return {
            "company_id": str(company_id),
            "filing_id": str(filing_id),
            "financial_metrics_id": str(metrics_id),
            "form_type": filing.form_type,
            "period_end_date": filing.period_end_date,
            "accession_number": filing.accession_number,
        }

    def _upsert_company(self, company: CompanyLookup) -> Any:
        statement = insert(self._companies).values(
            ticker=company.ticker,
            cik=company.cik,
            name=company.name,
            updated_at=func.now(),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[self._companies.c.ticker],
            set_={
                "cik": company.cik,
                "name": company.name,
                "updated_at": func.now(),
            },
        ).returning(self._companies.c.id)

        with self._engine.begin() as connection:
            return connection.execute(statement).scalar_one()

    def _upsert_filing(self, company_id: Any, filing: FilingMetadata) -> Any:
        period_end = datetime.strptime(filing.period_end_date, "%Y-%m-%d").date()
        filed_at = datetime.strptime(filing.filed_at, "%Y-%m-%d").date()

        statement = insert(self._filings).values(
            company_id=company_id,
            cik=filing.cik,
            form_type=filing.form_type,
            period_end_date=period_end,
            accession_number=filing.accession_number,
            filed_at=filed_at,
            type=filing.form_type,
            fiscal_year=period_end.year,
            period=_derive_period_label(filing.form_type, period_end.month),
            accession_num=filing.accession_number,
            updated_at=func.now(),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[self._filings.c.cik, self._filings.c.form_type, self._filings.c.period_end_date],
            set_={
                "company_id": company_id,
                "filed_at": filed_at,
                "accession_number": filing.accession_number,
                "accession_num": filing.accession_number,
                "updated_at": func.now(),
            },
        ).returning(self._filings.c.id)

        with self._engine.begin() as connection:
            return connection.execute(statement).scalar_one()

    def _upsert_metrics(
        self,
        filing_id: Any,
        base_metrics: FinancialMetric,
        derived_metrics: dict[str, DerivedMetric],
    ) -> Any:
        base_payload = base_metrics.model_dump(mode="json")
        derived_payload = {metric_name: asdict(metric) for metric_name, metric in derived_metrics.items()}

        statement = insert(self._financial_metrics).values(
            filing_id=filing_id,
            metrics=base_payload,
            base_metrics=base_payload,
            derived_metrics=derived_payload,
            updated_at=func.now(),
        )
        statement = statement.on_conflict_do_update(
            index_elements=[self._financial_metrics.c.filing_id],
            set_={
                "metrics": base_payload,
                "base_metrics": base_payload,
                "derived_metrics": derived_payload,
                "updated_at": func.now(),
            },
        ).returning(self._financial_metrics.c.id)

        with self._engine.begin() as connection:
            return connection.execute(statement).scalar_one()


def _derive_period_label(form_type: str, period_end_month: int) -> str:
    if form_type == "10-K":
        return "FY"
    quarter = ((period_end_month - 1) // 3) + 1
    return f"Q{quarter}"
