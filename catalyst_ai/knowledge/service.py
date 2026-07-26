"""Project-scoped knowledge document metadata and lifecycle services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import uuid

from catalyst_ai.auth.database import database_connection, initialize_database
from catalyst_ai.projects.permissions import require_permission
from catalyst_ai.knowledge.storage import delete_object, download_object, upload_object

SUPPORTED_KNOWLEDGE_TYPES = {"pdf", "docx", "txt"}
MAX_KNOWLEDGE_FILE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    project_id: int
    scope: str
    file_name: str
    file_type: str
    mime_type: str
    storage_path: str
    checksum: str
    version: int
    status: str
    size_bytes: int
    uploaded_by_user_id: int
    uploader_display_name: str
    created_at: str
    updated_at: str
    archived_at: str | None


class KnowledgeError(ValueError):
    """Raised when a project knowledge operation is invalid or unauthorized."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def initialize_knowledge_repository() -> None:
    initialize_database()
    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id TEXT PRIMARY KEY,
                project_id INTEGER NOT NULL,
                scope TEXT NOT NULL CHECK (scope IN ('PROJECT', 'COMPANY')),
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                storage_path TEXT NOT NULL UNIQUE,
                checksum TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('UPLOADED', 'READY', 'FAILED', 'ARCHIVED')),
                size_bytes INTEGER NOT NULL,
                uploaded_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT,
                UNIQUE(project_id, scope, file_name, version),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_project_status ON knowledge_documents(project_id, status)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_documents_project_name ON knowledge_documents(project_id, file_name, version)"
        )


def _actor_role(connection, project_id: int, user_id: int) -> str:
    row = connection.execute(
        "SELECT role FROM project_memberships WHERE project_id = ? AND user_id = ? AND status = 'ACTIVE'",
        (project_id, user_id),
    ).fetchone()
    if row is None:
        raise KnowledgeError("You do not have access to this project's knowledge repository.")
    return str(row["role"])


def _row_to_document(row) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=str(row["id"]),
        project_id=int(row["project_id"]),
        scope=str(row["scope"]),
        file_name=str(row["file_name"]),
        file_type=str(row["file_type"]),
        mime_type=str(row["mime_type"]),
        storage_path=str(row["storage_path"]),
        checksum=str(row["checksum"]),
        version=int(row["version"]),
        status=str(row["status"]),
        size_bytes=int(row["size_bytes"]),
        uploaded_by_user_id=int(row["uploaded_by_user_id"]),
        uploader_display_name=str(row.get("uploader_display_name") or f"User {row['uploaded_by_user_id']}"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        archived_at=row["archived_at"],
    )


def _select_document(connection, document_id: str, project_id: int):
    return connection.execute(
        """
        SELECT kd.*, u.display_name AS uploader_display_name
        FROM knowledge_documents kd
        JOIN users u ON u.id = kd.uploaded_by_user_id
        WHERE kd.id = ? AND kd.project_id = ?
        """,
        (document_id, project_id),
    ).fetchone()


def list_knowledge_documents(
    project_id: int,
    requesting_user_id: int,
    include_archived: bool = False,
) -> list[KnowledgeDocument]:
    initialize_knowledge_repository()
    with database_connection() as connection:
        _actor_role(connection, project_id, requesting_user_id)
        archived_clause = "" if include_archived else "AND kd.status != 'ARCHIVED'"
        rows = connection.execute(
            f"""
            SELECT kd.*, u.display_name AS uploader_display_name
            FROM knowledge_documents kd
            JOIN users u ON u.id = kd.uploaded_by_user_id
            WHERE kd.project_id = ? {archived_clause}
            ORDER BY kd.created_at DESC, kd.file_name, kd.version DESC
            """,
            (project_id,),
        ).fetchall()
    return [_row_to_document(row) for row in rows]


def upload_knowledge_document(
    project_id: int,
    actor_user_id: int,
    file_name: str,
    mime_type: str,
    content: bytes,
    scope: str = "PROJECT",
) -> KnowledgeDocument:
    initialize_knowledge_repository()
    clean_name = Path(file_name).name.strip()
    extension = Path(clean_name).suffix.lower().lstrip(".")
    normalized_scope = scope.strip().upper()
    if not clean_name or extension not in SUPPORTED_KNOWLEDGE_TYPES:
        raise KnowledgeError("Upload a PDF, DOCX, or TXT knowledge document.")
    if not content:
        raise KnowledgeError("The selected knowledge document is empty.")
    if len(content) > MAX_KNOWLEDGE_FILE_BYTES:
        raise KnowledgeError("Knowledge documents must not exceed 25 MB.")
    if normalized_scope != "PROJECT":
        raise KnowledgeError("Company knowledge will be enabled when workspaces are introduced.")

    checksum = hashlib.sha256(content).hexdigest()
    now = _utc_now()
    document_id = str(uuid.uuid4())
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_name)

    with database_connection() as connection:
        role = _actor_role(connection, project_id, actor_user_id)
        try:
            require_permission(role, "manage_knowledge")
        except PermissionError as exc:
            raise KnowledgeError(str(exc)) from exc
        duplicate = connection.execute(
            "SELECT id FROM knowledge_documents WHERE project_id = ? AND scope = ? AND checksum = ? AND status != 'ARCHIVED' LIMIT 1",
            (project_id, normalized_scope, checksum),
        ).fetchone()
        if duplicate:
            raise KnowledgeError("This exact document is already present in the project knowledge repository.")
        latest = connection.execute(
            "SELECT MAX(version) AS latest_version FROM knowledge_documents WHERE project_id = ? AND scope = ? AND file_name = ?",
            (project_id, normalized_scope, clean_name),
        ).fetchone()
        version = int(latest["latest_version"] or 0) + 1
        storage_path = f"projects/{project_id}/knowledge/{document_id}/v{version}/{safe_name}"

    upload_object(storage_path, content, mime_type or "application/octet-stream")
    try:
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_documents (
                    id, project_id, scope, file_name, file_type, mime_type, storage_path,
                    checksum, version, status, size_bytes, uploaded_by_user_id,
                    created_at, updated_at, archived_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'READY', ?, ?, ?, ?, NULL)
                """,
                (
                    document_id,
                    project_id,
                    normalized_scope,
                    clean_name,
                    extension,
                    mime_type or "application/octet-stream",
                    storage_path,
                    checksum,
                    version,
                    len(content),
                    actor_user_id,
                    now,
                    now,
                ),
            )
            row = _select_document(connection, document_id, project_id)
    except Exception:
        try:
            delete_object(storage_path)
        finally:
            raise
    return _row_to_document(row)


def download_knowledge_document(
    project_id: int,
    requesting_user_id: int,
    document_id: str,
) -> tuple[KnowledgeDocument, bytes]:
    initialize_knowledge_repository()
    with database_connection() as connection:
        _actor_role(connection, project_id, requesting_user_id)
        row = _select_document(connection, document_id, project_id)
    if row is None:
        raise KnowledgeError("Knowledge document not found.")
    document = _row_to_document(row)
    return document, download_object(document.storage_path)


def archive_knowledge_document(project_id: int, actor_user_id: int, document_id: str) -> None:
    """Archive metadata while retaining the original object for history and restoration."""
    initialize_knowledge_repository()
    now = _utc_now()
    with database_connection() as connection:
        role = _actor_role(connection, project_id, actor_user_id)
        try:
            require_permission(role, "manage_knowledge")
        except PermissionError as exc:
            raise KnowledgeError(str(exc)) from exc
        row = connection.execute(
            "SELECT id FROM knowledge_documents WHERE id = ? AND project_id = ? AND status != 'ARCHIVED'",
            (document_id, project_id),
        ).fetchone()
        if row is None:
            raise KnowledgeError("Knowledge document not found or already archived.")
        connection.execute(
            "UPDATE knowledge_documents SET status = 'ARCHIVED', archived_at = ?, updated_at = ? WHERE id = ?",
            (now, now, document_id),
        )


def restore_knowledge_document(project_id: int, actor_user_id: int, document_id: str) -> None:
    initialize_knowledge_repository()
    now = _utc_now()
    with database_connection() as connection:
        role = _actor_role(connection, project_id, actor_user_id)
        try:
            require_permission(role, "manage_knowledge")
        except PermissionError as exc:
            raise KnowledgeError(str(exc)) from exc
        row = connection.execute(
            "SELECT id FROM knowledge_documents WHERE id = ? AND project_id = ? AND status = 'ARCHIVED'",
            (document_id, project_id),
        ).fetchone()
        if row is None:
            raise KnowledgeError("Archived knowledge document not found.")
        connection.execute(
            "UPDATE knowledge_documents SET status = 'READY', archived_at = NULL, updated_at = ? WHERE id = ?",
            (now, document_id),
        )


def permanently_delete_knowledge_document(
    project_id: int,
    actor_user_id: int,
    document_id: str,
) -> None:
    """Permanently remove an archived document. This action is Owner-only."""
    initialize_knowledge_repository()
    with database_connection() as connection:
        role = _actor_role(connection, project_id, actor_user_id)
        try:
            require_permission(role, "delete_knowledge")
        except PermissionError as exc:
            raise KnowledgeError(str(exc)) from exc
        row = connection.execute(
            "SELECT storage_path FROM knowledge_documents WHERE id = ? AND project_id = ? AND status = 'ARCHIVED'",
            (document_id, project_id),
        ).fetchone()
        if row is None:
            raise KnowledgeError("Only archived knowledge documents can be permanently deleted.")
        storage_path = str(row["storage_path"])

    delete_object(storage_path)
    with database_connection() as connection:
        connection.execute(
            "DELETE FROM knowledge_documents WHERE id = ? AND project_id = ? AND status = 'ARCHIVED'",
            (document_id, project_id),
        )
