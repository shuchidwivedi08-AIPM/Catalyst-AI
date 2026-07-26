"""Tests for the PostgreSQL-ready database abstraction."""

from pathlib import Path

from catalyst_ai.auth.database import (
    database_connection,
    get_database_url,
    initialize_database,
    is_postgresql,
)
from catalyst_ai.auth.service import RegistrationError, register_user


def test_sqlite_is_the_local_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_path = tmp_path / "fallback.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))

    assert get_database_url().startswith("sqlite:///")
    assert not is_postgresql()

    initialize_database()
    assert database_path.exists()


def test_schema_migration_creates_all_durable_tables(tmp_path):
    database_path = tmp_path / "schema.db"
    initialize_database(database_path)

    with database_connection(database_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()

    table_names = {row["name"] for row in tables}
    assert {
        "users",
        "projects",
        "project_memberships",
        "project_workflow_snapshots",
        "schema_migrations",
    }.issubset(table_names)
    assert [row["version"] for row in versions] == [1]


def test_case_insensitive_identity_constraints_survive_backend_abstraction(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "identity.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)

    register_user(
        username="Product.Owner",
        email="Owner@Example.com",
        display_name="Product Owner",
        password="A-secure-password-123",
    )

    try:
        register_user(
            username="product.owner",
            email="different@example.com",
            display_name="Duplicate Username",
            password="A-secure-password-123",
        )
    except RegistrationError as exc:
        assert "username" in str(exc).lower()
    else:
        raise AssertionError("Case-insensitive duplicate username was accepted.")


def test_postgresql_urls_are_normalized_for_psycopg(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@example.com:5432/catalyst?sslmode=require",
    )

    assert get_database_url().startswith("postgresql+psycopg://")
    assert is_postgresql()
