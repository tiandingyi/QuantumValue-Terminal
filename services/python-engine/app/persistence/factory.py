from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from app.persistence.store import PersistenceStore


logger = logging.getLogger(__name__)


def build_persistence_store(database_url: Optional[str]) -> Optional[PersistenceStore]:
    """Create the SQLAlchemy-backed persistence store when configuration allows it."""
    if not database_url:
        return None

    try:
        from app.persistence.sqlalchemy_store import SQLAlchemyPersistenceStore
    except ModuleNotFoundError as exc:
        logger.warning("Persistence store disabled because database dependencies are missing: %s", exc)
        return None

    return SQLAlchemyPersistenceStore(_normalize_sqlalchemy_database_url(database_url))


def _normalize_sqlalchemy_database_url(database_url: str) -> str:
    """Translate legacy postgres URLs into a SQLAlchemy-compatible psycopg URL."""
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://") :]

    parts = urlsplit(database_url)
    if parts.scheme == "postgres":
        return urlunsplit(("postgresql+psycopg", parts.netloc, parts.path, parts.query, parts.fragment))
    if parts.scheme == "postgresql":
        return urlunsplit(("postgresql+psycopg", parts.netloc, parts.path, parts.query, parts.fragment))
    return database_url
