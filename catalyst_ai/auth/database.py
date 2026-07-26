"""Database configuration and migrations for Catalyst AI.

Production deployments use PostgreSQL through ``DATABASE_URL``. SQLite remains
available as a zero-configuration local-development and test fallback.
"""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
from threading import Lock
from typing import Any, Iterator, Mapping, Sequence

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine, Result
from sqlalchemy.exc import IntegrityError as DatabaseIntegrityError


DEFAULT_DATABASE_PATH = Path("data/catalyst_ai.db")
_SCHEMA_VERSION = 1
_metadata = MetaData()
_engine_cache: dict[str, Engine] = {}
_engine_lock = Lock()

users = Table(
    "users",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(50), nullable=False),
    Column("email", String(320), nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("display_name", String(200), nullable=False),
    Column("status", String(20), nullable=False, server_default="ACTIVE"),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("last_login_at", String(40)),
    CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'LOCKED')", name="ck_users_status"),
)
Index("uq_users_username_ci", func.lower(users.c.username), unique=True)
Index("uq_users_email_ci", func.lower(users.c.email), unique=True)
Index("idx_users_status", users.c.status)

projects = Table(
    "projects",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(100), nullable=False),
    Column("description", Text, nullable=False, server_default=""),
    Column("owner_user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("created_by_user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("status", String(20), nullable=False, server_default="ACTIVE"),
    Column("workflow_stage", String(40), nullable=False, server_default="DOCUMENT_UPLOAD"),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("last_activity_at", String(40), nullable=False),
    Column("archived_at", String(40)),
    CheckConstraint(
        "status IN ('ACTIVE', 'ON_HOLD', 'COMPLETED', 'ARCHIVED')",
        name="ck_projects_status",
    ),
)
Index("idx_projects_owner", projects.c.owner_user_id)

project_memberships = Table(
    "project_memberships",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("role", String(20), nullable=False),
    Column("status", String(20), nullable=False, server_default="ACTIVE"),
    Column("added_by_user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    UniqueConstraint("project_id", "user_id", name="uq_project_membership_user"),
    CheckConstraint("role IN ('OWNER', 'ADMIN', 'EDITOR', 'REVIEWER')", name="ck_member_role"),
    CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'REMOVED')", name="ck_member_status"),
)
Index("idx_project_memberships_user", project_memberships.c.user_id, project_memberships.c.status)
Index("idx_project_memberships_project", project_memberships.c.project_id, project_memberships.c.status)

project_workflow_snapshots = Table(
    "project_workflow_snapshots",
    _metadata,
    Column(
        "project_id",
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("snapshot_json", Text, nullable=False),
    Column("updated_at", String(40), nullable=False),
)

schema_migrations = Table(
    "schema_migrations",
    _metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", String(40), nullable=False),
)


def get_database_path() -> Path:
    """Return the configured SQLite fallback path."""
    configured_path = os.getenv("CATALYST_DATABASE_PATH")
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


def _streamlit_database_url() -> str | None:
    try:
        import streamlit as st

        value = st.secrets.get("DATABASE_URL")
        return str(value).strip() if value else None
    except Exception:
        return None


def get_database_url(database_path: Path | None = None) -> str:
    """Resolve PostgreSQL configuration or return a local SQLite URL."""
    if database_path is not None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.resolve()}"

    configured = (os.getenv("DATABASE_URL") or _streamlit_database_url() or "").strip()
    if configured:
        if configured.startswith("postgres://"):
            configured = "postgresql://" + configured[len("postgres://") :]
        if configured.startswith("postgresql://"):
            configured = "postgresql+psycopg://" + configured[len("postgresql://") :]
        return configured

    path = get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.resolve()}"


def is_postgresql(database_path: Path | None = None) -> bool:
    return get_database_url(database_path).startswith("postgresql+")


def _get_engine(database_path: Path | None = None) -> Engine:
    url = get_database_url(database_path)
    with _engine_lock:
        engine = _engine_cache.get(url)
        if engine is None:
            options: dict[str, Any] = {"pool_pre_ping": True}
            if url.startswith("sqlite:"):
                options["connect_args"] = {"check_same_thread": False}
            engine = create_engine(url, **options)
            _engine_cache[url] = engine
        return engine


def _prepare_sql(sql: str, parameters: Sequence[Any] | Mapping[str, Any] | None):
    """Translate legacy qmark SQL and SQLite case-insensitive comparisons."""
    sql = re.sub(
        r"([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\?\s+COLLATE\s+NOCASE",
        r"LOWER(\1) = LOWER(?)",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"\s+COLLATE\s+NOCASE", "", sql, flags=re.IGNORECASE)
    if parameters is None or isinstance(parameters, Mapping):
        return sql, parameters or {}

    values = tuple(parameters)
    index = 0

    def replace(_: re.Match[str]) -> str:
        nonlocal index
        token = f":p{index}"
        index += 1
        return token

    translated = re.sub(r"\?", replace, sql)
    if index != len(values):
        raise ValueError("SQL parameter count does not match placeholder count.")
    return translated, {f"p{i}": value for i, value in enumerate(values)}


class CompatibleResult:
    """Small result wrapper preserving the existing sqlite-style call surface."""

    def __init__(self, result: Result[Any]) -> None:
        self._result = result

    @property
    def rowcount(self) -> int:
        return self._result.rowcount

    def fetchone(self):
        return self._result.mappings().first()

    def fetchall(self):
        return self._result.mappings().all()


class CompatibleConnection:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def execute(
        self,
        sql: str,
        parameters: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> CompatibleResult:
        translated, bindings = _prepare_sql(sql, parameters)
        return CompatibleResult(self._connection.execute(text(translated), bindings))


@contextmanager
def database_connection(database_path: Path | None = None) -> Iterator[CompatibleConnection]:
    """Open a transaction using PostgreSQL or the SQLite local fallback."""
    engine = _get_engine(database_path)
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        yield CompatibleConnection(connection)


def initialize_database(database_path: Path | None = None) -> None:
    """Apply idempotent schema migrations to the configured database."""
    engine = _get_engine(database_path)
    _metadata.create_all(engine)
    with engine.begin() as connection:
        current = connection.execute(select(func.max(schema_migrations.c.version))).scalar()
        if not current or int(current) < _SCHEMA_VERSION:
            from datetime import datetime, timezone

            connection.execute(
                schema_migrations.insert().values(
                    version=_SCHEMA_VERSION,
                    applied_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                )
            )
