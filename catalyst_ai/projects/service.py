"""Project creation, access, and retrieval services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from catalyst_ai.auth.database import database_connection, initialize_database
from catalyst_ai.projects.models import Project


class ProjectError(ValueError):
    """Raised when a project action is invalid or unauthorized."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_project(row: Mapping[str, Any]) -> Project:
    return Project(
        id=int(row["id"]),
        name=str(row["name"]),
        description=str(row["description"]),
        owner_user_id=int(row["owner_user_id"]),
        created_by_user_id=int(row["created_by_user_id"]),
        status=str(row["status"]),
        workflow_stage=str(row["workflow_stage"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        last_activity_at=str(row["last_activity_at"]),
        user_role=str(row["user_role"]),
    )


def create_project(user_id: int, name: str, description: str = "") -> Project:
    """Create a project and grant its creator OWNER membership atomically."""
    initialize_database()
    name = name.strip()
    description = description.strip()
    if len(name) < 3 or len(name) > 100:
        raise ProjectError("Project name must be 3–100 characters.")
    if len(description) > 1000:
        raise ProjectError("Project description must not exceed 1,000 characters.")

    now = _utc_now()
    with database_connection() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE id = ? AND status = 'ACTIVE'", (user_id,)
        ).fetchone()
        if user is None:
            raise ProjectError("The current user cannot create projects.")

        inserted = connection.execute(
            """
            INSERT INTO projects (
                name, description, owner_user_id, created_by_user_id,
                status, workflow_stage, created_at, updated_at, last_activity_at
            ) VALUES (?, ?, ?, ?, 'ACTIVE', 'DOCUMENT_UPLOAD', ?, ?, ?)
            RETURNING id
            """,
            (name, description, user_id, user_id, now, now, now),
        ).fetchone()
        project_id = int(inserted["id"])
        connection.execute(
            """
            INSERT INTO project_memberships (
                project_id, user_id, role, status, added_by_user_id, created_at, updated_at
            ) VALUES (?, ?, 'OWNER', 'ACTIVE', ?, ?, ?)
            """,
            (project_id, user_id, user_id, now, now),
        )
        row = connection.execute(
            """
            SELECT p.*, pm.role AS user_role
            FROM projects p
            JOIN project_memberships pm ON pm.project_id = p.id
            WHERE p.id = ? AND pm.user_id = ?
            """,
            (project_id, user_id),
        ).fetchone()
    return _row_to_project(row)


def list_user_projects(user_id: int, include_archived: bool = False) -> list[Project]:
    """List projects the user owns or has been granted active access to."""
    initialize_database()
    archived_clause = "" if include_archived else "AND p.status != 'ARCHIVED'"
    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT p.*, pm.role AS user_role
            FROM projects p
            JOIN project_memberships pm ON pm.project_id = p.id
            WHERE pm.user_id = ? AND pm.status = 'ACTIVE' {archived_clause}
            ORDER BY p.last_activity_at DESC, p.id DESC
            """,
            (user_id,),
        ).fetchall()
    return [_row_to_project(row) for row in rows]


def get_accessible_project(user_id: int, project_id: int) -> Project:
    """Return a project only when the user has active membership."""
    initialize_database()
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT p.*, pm.role AS user_role
            FROM projects p
            JOIN project_memberships pm ON pm.project_id = p.id
            WHERE p.id = ? AND pm.user_id = ? AND pm.status = 'ACTIVE'
            LIMIT 1
            """,
            (project_id, user_id),
        ).fetchone()
        if row is None:
            raise ProjectError("You do not have access to this project.")
        now = _utc_now()
        connection.execute(
            "UPDATE projects SET last_activity_at = ?, updated_at = ? WHERE id = ?",
            (now, now, project_id),
        )
        row = connection.execute(
            """
            SELECT p.*, pm.role AS user_role
            FROM projects p
            JOIN project_memberships pm ON pm.project_id = p.id
            WHERE p.id = ? AND pm.user_id = ?
            """,
            (project_id, user_id),
        ).fetchone()
    return _row_to_project(row)
