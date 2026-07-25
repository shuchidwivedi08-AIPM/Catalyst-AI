"""Tests for Catalyst AI authentication services."""

import pytest

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.service import (
    AuthenticationError,
    BootstrapError,
    authenticate_user,
    bootstrap_initial_admin,
    hash_password,
    has_users,
    verify_password,
)


@pytest.fixture
def auth_database(tmp_path, monkeypatch):
    database_path = tmp_path / "auth-test.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))
    initialize_database()
    return database_path


def test_password_hash_is_salted_and_verifiable():
    first_hash = hash_password("A-secure-password-123")
    second_hash = hash_password("A-secure-password-123")

    assert first_hash != second_hash
    assert verify_password("A-secure-password-123", first_hash)
    assert not verify_password("wrong-password", first_hash)


def test_initial_admin_can_only_be_created_once(auth_database):
    assert not has_users()

    user = bootstrap_initial_admin(
        username="catalyst.admin",
        email="admin@example.com",
        display_name="Catalyst Administrator",
        password="A-secure-password-123",
    )

    assert has_users()
    assert user.username == "catalyst.admin"
    assert user.status == "ACTIVE"

    with pytest.raises(BootstrapError, match="already been completed"):
        bootstrap_initial_admin(
            username="another.admin",
            email="another@example.com",
            display_name="Another Administrator",
            password="Another-secure-password-123",
        )


def test_user_can_authenticate_by_username_or_email(auth_database):
    bootstrap_initial_admin(
        username="product.owner",
        email="owner@example.com",
        display_name="Product Owner",
        password="A-secure-password-123",
    )

    by_username = authenticate_user("PRODUCT.OWNER", "A-secure-password-123")
    by_email = authenticate_user("OWNER@EXAMPLE.COM", "A-secure-password-123")

    assert by_username.id == by_email.id
    assert by_email.last_login_at is not None


def test_invalid_credentials_return_generic_error(auth_database):
    bootstrap_initial_admin(
        username="product.owner",
        email="owner@example.com",
        display_name="Product Owner",
        password="A-secure-password-123",
    )

    with pytest.raises(AuthenticationError, match="username or password"):
        authenticate_user("missing-user", "wrong-password")

    with pytest.raises(AuthenticationError, match="username or password"):
        authenticate_user("product.owner", "wrong-password")


def test_bootstrap_validates_password_strength(auth_database):
    with pytest.raises(BootstrapError, match="at least 12"):
        bootstrap_initial_admin(
            username="admin",
            email="admin@example.com",
            display_name="Administrator",
            password="short",
        )
