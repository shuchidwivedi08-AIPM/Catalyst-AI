from __future__ import annotations

from pathlib import Path

import pytest

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.service import bootstrap_initial_admin
from catalyst_ai.projects.service import ProjectError, create_project, get_accessible_project, list_user_projects


@pytest.fixture()
def project_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database_path = tmp_path / "catalyst_test.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))
    initialize_database()
    return database_path


def _create_user(username: str, email: str):
    return bootstrap_initial_admin(username, email, "Project Owner", "SecurePassword123")


def test_project_creator_becomes_owner(project_database: Path):
    user = _create_user("owner", "owner@example.com")

    project = create_project(user.id, "Catalyst AI", "Enterprise product intelligence")

    assert project.owner_user_id == user.id
    assert project.created_by_user_id == user.id
    assert project.user_role == "OWNER"
    assert project.workflow_stage == "DOCUMENT_UPLOAD"
    assert project.status == "ACTIVE"


def test_dashboard_lists_projects_for_active_member(project_database: Path):
    user = _create_user("owner", "owner@example.com")
    first = create_project(user.id, "First Project")
    second = create_project(user.id, "Second Project")

    projects = list_user_projects(user.id)

    assert {project.id for project in projects} == {first.id, second.id}
    assert all(project.user_role == "OWNER" for project in projects)


def test_project_access_requires_active_membership(project_database: Path):
    owner = _create_user("owner", "owner@example.com")
    project = create_project(owner.id, "Private Project")

    with pytest.raises(ProjectError, match="do not have access"):
        get_accessible_project(owner.id + 999, project.id)


def test_project_name_validation(project_database: Path):
    user = _create_user("owner", "owner@example.com")

    with pytest.raises(ProjectError, match="3–100"):
        create_project(user.id, "AB")
