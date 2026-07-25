from __future__ import annotations

from pathlib import Path

import pytest

from catalyst_ai.auth.database import database_connection, initialize_database
from catalyst_ai.auth.service import bootstrap_initial_admin, hash_password
from catalyst_ai.projects.members import (
    MembershipError,
    add_project_member,
    list_project_members,
    remove_project_member,
    update_project_member_role,
)
from catalyst_ai.projects.permissions import has_permission
from catalyst_ai.projects.service import create_project


@pytest.fixture
def project_users(tmp_path: Path, monkeypatch):
    database_path = tmp_path / "catalyst.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))
    initialize_database()
    owner = bootstrap_initial_admin("owner", "owner@example.com", "Owner", "OwnerPassword123")
    with database_connection() as connection:
        user_ids = []
        for username, email, name in (
            ("admin", "admin@example.com", "Admin User"),
            ("editor", "editor@example.com", "Editor User"),
            ("reviewer", "reviewer@example.com", "Reviewer User"),
        ):
            cursor = connection.execute(
                """
                INSERT INTO users (username, email, password_hash, display_name, status)
                VALUES (?, ?, ?, ?, 'ACTIVE')
                """,
                (username, email, hash_password("MemberPassword123"), name),
            )
            user_ids.append(int(cursor.lastrowid))
    project = create_project(owner.id, "Access Control Project")
    return owner, project, user_ids


def test_role_permission_matrix():
    assert has_permission("OWNER", "manage_members")
    assert has_permission("ADMIN", "manage_members")
    assert has_permission("EDITOR", "modify_workflow")
    assert not has_permission("REVIEWER", "modify_workflow")
    assert not has_permission("EDITOR", "manage_members")


def test_owner_can_add_and_change_member_role(project_users):
    owner, project, user_ids = project_users
    member = add_project_member(project.id, owner.id, "admin@example.com", "ADMIN")
    assert member.role == "ADMIN"

    update_project_member_role(project.id, owner.id, user_ids[0], "EDITOR")
    members = list_project_members(project.id, owner.id)
    assert next(item for item in members if item.user_id == user_ids[0]).role == "EDITOR"


def test_admin_can_add_member_but_editor_cannot(project_users):
    owner, project, user_ids = project_users
    add_project_member(project.id, owner.id, "admin", "ADMIN")
    added = add_project_member(project.id, user_ids[0], "editor", "EDITOR")
    assert added.role == "EDITOR"

    with pytest.raises(MembershipError):
        add_project_member(project.id, user_ids[1], "reviewer", "REVIEWER")


def test_owner_is_protected_and_removed_member_loses_listing(project_users):
    owner, project, user_ids = project_users
    add_project_member(project.id, owner.id, "reviewer", "REVIEWER")

    with pytest.raises(MembershipError):
        update_project_member_role(project.id, owner.id, owner.id, "ADMIN")
    with pytest.raises(MembershipError):
        remove_project_member(project.id, owner.id, owner.id)

    remove_project_member(project.id, owner.id, user_ids[2])
    members = list_project_members(project.id, owner.id)
    assert all(member.user_id != user_ids[2] for member in members)


def test_unknown_user_and_owner_role_assignment_are_rejected(project_users):
    owner, project, _ = project_users
    with pytest.raises(MembershipError):
        add_project_member(project.id, owner.id, "missing@example.com", "EDITOR")
    with pytest.raises(MembershipError):
        add_project_member(project.id, owner.id, "admin", "OWNER")
