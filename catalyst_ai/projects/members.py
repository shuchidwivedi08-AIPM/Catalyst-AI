"""Project membership administration and user-directory services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from catalyst_ai.auth.database import CompatibleConnection, database_connection, initialize_database
from catalyst_ai.projects.permissions import ASSIGNABLE_ROLES, require_permission


@dataclass(frozen=True)
class ProjectMember:
    membership_id: int
    project_id: int
    user_id: int
    username: str
    email: str
    display_name: str
    role: str
    status: str
    added_by_user_id: int
    created_at: str


@dataclass(frozen=True)
class UserDirectoryEntry:
    user_id: int
    username: str
    email: str
    display_name: str
    previous_membership_status: str | None = None


class MembershipError(ValueError):
    """Raised when a membership action is invalid or unauthorized."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _actor_role(connection: CompatibleConnection, project_id: int, actor_user_id: int) -> str:
    row = connection.execute(
        """
        SELECT role FROM project_memberships
        WHERE project_id = ? AND user_id = ? AND status = 'ACTIVE'
        """,
        (project_id, actor_user_id),
    ).fetchone()
    if row is None:
        raise MembershipError("You do not have access to manage this project.")
    return str(row["role"])


def _require_member_management(
    connection: CompatibleConnection, project_id: int, actor_user_id: int
) -> None:
    actor_role = _actor_role(connection, project_id, actor_user_id)
    try:
        require_permission(actor_role, "manage_members")
    except PermissionError as exc:
        raise MembershipError(str(exc)) from exc


def _row_to_member(row: Mapping[str, Any]) -> ProjectMember:
    return ProjectMember(
        membership_id=int(row["membership_id"]),
        project_id=int(row["project_id"]),
        user_id=int(row["user_id"]),
        username=str(row["username"]),
        email=str(row["email"]),
        display_name=str(row["display_name"]),
        role=str(row["role"]),
        status=str(row["membership_status"]),
        added_by_user_id=int(row["added_by_user_id"]),
        created_at=str(row["membership_created_at"]),
    )


def list_project_members(project_id: int, requesting_user_id: int) -> list[ProjectMember]:
    """List project members for any active project participant."""
    initialize_database()
    with database_connection() as connection:
        _actor_role(connection, project_id, requesting_user_id)
        rows = connection.execute(
            """
            SELECT pm.id AS membership_id, pm.project_id, pm.user_id, pm.role,
                   pm.status AS membership_status, pm.added_by_user_id,
                   pm.created_at AS membership_created_at,
                   u.username, u.email, u.display_name
            FROM project_memberships pm
            JOIN users u ON u.id = pm.user_id
            WHERE pm.project_id = ? AND pm.status != 'REMOVED'
            ORDER BY CASE pm.role
                WHEN 'OWNER' THEN 1 WHEN 'ADMIN' THEN 2
                WHEN 'EDITOR' THEN 3 ELSE 4 END,
                LOWER(u.display_name)
            """,
            (project_id,),
        ).fetchall()
    return [_row_to_member(row) for row in rows]


def search_available_users(
    project_id: int,
    actor_user_id: int,
    query: str,
    limit: int = 10,
) -> list[UserDirectoryEntry]:
    """Search active users not already active in the project."""
    initialize_database()
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        return []
    safe_limit = max(1, min(int(limit), 20))
    pattern = f"%{normalized_query}%"
    with database_connection() as connection:
        _require_member_management(connection, project_id, actor_user_id)
        rows = connection.execute(
            """
            SELECT u.id, u.username, u.email, u.display_name,
                   pm.status AS previous_membership_status
            FROM users u
            LEFT JOIN project_memberships pm
              ON pm.project_id = ? AND pm.user_id = u.id
            WHERE u.status = 'ACTIVE'
              AND (pm.status IS NULL OR pm.status != 'ACTIVE')
              AND (
                  LOWER(u.display_name) LIKE LOWER(?) OR
                  LOWER(u.username) LIKE LOWER(?) OR
                  LOWER(u.email) LIKE LOWER(?)
              )
            ORDER BY LOWER(u.display_name), LOWER(u.username)
            LIMIT ?
            """,
            (project_id, pattern, pattern, pattern, safe_limit),
        ).fetchall()
    return [
        UserDirectoryEntry(
            user_id=int(row["id"]),
            username=str(row["username"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            previous_membership_status=row["previous_membership_status"],
        )
        for row in rows
    ]


def add_project_member(
    project_id: int,
    actor_user_id: int,
    user_identifier: str | int,
    role: str,
) -> ProjectMember:
    """Add or reactivate a selected existing Catalyst AI user."""
    initialize_database()
    normalized_role = role.strip().upper()
    if normalized_role not in ASSIGNABLE_ROLES:
        raise MembershipError("Select Admin, Editor, or Reviewer access.")

    now = _utc_now()
    with database_connection() as connection:
        _require_member_management(connection, project_id, actor_user_id)
        if isinstance(user_identifier, int):
            user = connection.execute(
                "SELECT id FROM users WHERE id = ? AND status = 'ACTIVE' LIMIT 1",
                (user_identifier,),
            ).fetchone()
        else:
            identifier = user_identifier.strip()
            if not identifier:
                raise MembershipError("Select an existing Catalyst AI user.")
            user = connection.execute(
                """
                SELECT id FROM users
                WHERE (username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE)
                  AND status = 'ACTIVE'
                LIMIT 1
                """,
                (identifier, identifier),
            ).fetchone()
        if user is None:
            raise MembershipError("The selected active Catalyst AI user could not be found.")
        target_user_id = int(user["id"])

        existing = connection.execute(
            "SELECT role, status FROM project_memberships WHERE project_id = ? AND user_id = ?",
            (project_id, target_user_id),
        ).fetchone()
        if existing and existing["role"] == "OWNER":
            raise MembershipError("The project owner cannot be reassigned.")
        if existing and existing["status"] == "ACTIVE":
            raise MembershipError("That user is already an active project member.")

        connection.execute(
            """
            INSERT INTO project_memberships (
                project_id, user_id, role, status, added_by_user_id, created_at, updated_at
            ) VALUES (?, ?, ?, 'ACTIVE', ?, ?, ?)
            ON CONFLICT(project_id, user_id) DO UPDATE SET
                role = excluded.role,
                status = 'ACTIVE',
                added_by_user_id = excluded.added_by_user_id,
                updated_at = excluded.updated_at
            """,
            (project_id, target_user_id, normalized_role, actor_user_id, now, now),
        )
        row = connection.execute(
            """
            SELECT pm.id AS membership_id, pm.project_id, pm.user_id, pm.role,
                   pm.status AS membership_status, pm.added_by_user_id,
                   pm.created_at AS membership_created_at,
                   u.username, u.email, u.display_name
            FROM project_memberships pm JOIN users u ON u.id = pm.user_id
            WHERE pm.project_id = ? AND pm.user_id = ?
            """,
            (project_id, target_user_id),
        ).fetchone()
    return _row_to_member(row)


def update_project_member_role(
    project_id: int,
    actor_user_id: int,
    target_user_id: int,
    role: str,
) -> None:
    """Change a non-owner member's role."""
    normalized_role = role.strip().upper()
    if normalized_role not in ASSIGNABLE_ROLES:
        raise MembershipError("Select Admin, Editor, or Reviewer access.")
    now = _utc_now()
    with database_connection() as connection:
        _require_member_management(connection, project_id, actor_user_id)
        target = connection.execute(
            "SELECT role, status FROM project_memberships WHERE project_id = ? AND user_id = ?",
            (project_id, target_user_id),
        ).fetchone()
        if target is None or target["status"] != "ACTIVE":
            raise MembershipError("That active project member could not be found.")
        if target["role"] == "OWNER":
            raise MembershipError("The project owner's role cannot be changed.")
        connection.execute(
            "UPDATE project_memberships SET role = ?, updated_at = ? WHERE project_id = ? AND user_id = ?",
            (normalized_role, now, project_id, target_user_id),
        )


def remove_project_member(project_id: int, actor_user_id: int, target_user_id: int) -> None:
    """Remove a non-owner member while retaining membership history."""
    now = _utc_now()
    with database_connection() as connection:
        _require_member_management(connection, project_id, actor_user_id)
        target = connection.execute(
            "SELECT role, status FROM project_memberships WHERE project_id = ? AND user_id = ?",
            (project_id, target_user_id),
        ).fetchone()
        if target is None or target["status"] != "ACTIVE":
            raise MembershipError("That active project member could not be found.")
        if target["role"] == "OWNER":
            raise MembershipError("The project owner cannot be removed.")
        if target_user_id == actor_user_id:
            raise MembershipError("Use a dedicated leave-project flow to remove yourself.")
        connection.execute(
            "UPDATE project_memberships SET status = 'REMOVED', updated_at = ? WHERE project_id = ? AND user_id = ?",
            (now, project_id, target_user_id),
        )
