"""Tests for signup duplicate checks and member-directory selection."""

import pytest

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.service import RegistrationError, bootstrap_initial_admin, register_user
from catalyst_ai.projects.members import add_project_member, search_available_users
from catalyst_ai.projects.service import create_project


@pytest.fixture
def database(tmp_path, monkeypatch):
    database_path = tmp_path / "signup-directory.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))
    initialize_database()
    return database_path


def test_signup_creates_active_user_and_rejects_case_insensitive_duplicates(database):
    bootstrap_initial_admin(
        "catalyst.admin", "admin@example.com", "Administrator", "Secure-password-123"
    )
    user = register_user(
        "product.owner", "Owner@Example.com", "Product Owner", "Secure-password-456"
    )
    assert user.status == "ACTIVE"
    assert user.email == "owner@example.com"

    with pytest.raises(RegistrationError, match="username is already"):
        register_user(
            "PRODUCT.OWNER", "other@example.com", "Duplicate", "Secure-password-789"
        )
    with pytest.raises(RegistrationError, match="email address"):
        register_user(
            "another.owner", "OWNER@example.com", "Duplicate", "Secure-password-789"
        )


def test_directory_search_returns_only_available_active_users(database):
    owner = bootstrap_initial_admin(
        "owner", "owner@example.com", "Owner", "Secure-password-123"
    )
    editor = register_user(
        "editor.user", "editor@example.com", "Editor User", "Secure-password-456"
    )
    reviewer = register_user(
        "review.user", "reviewer@example.com", "Review User", "Secure-password-789"
    )
    project = create_project(owner.id, "Directory Project")

    results = search_available_users(project.id, owner.id, "user")
    assert {entry.user_id for entry in results} == {editor.id, reviewer.id}

    add_project_member(project.id, owner.id, editor.id, "EDITOR")
    results = search_available_users(project.id, owner.id, "user")
    assert {entry.user_id for entry in results} == {reviewer.id}


def test_directory_requires_two_characters(database):
    owner = bootstrap_initial_admin(
        "owner", "owner@example.com", "Owner", "Secure-password-123"
    )
    project = create_project(owner.id, "Search Project")
    assert search_available_users(project.id, owner.id, "a") == []
