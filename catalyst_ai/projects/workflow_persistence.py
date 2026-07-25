"""Project-scoped persistence for the Catalyst AI workflow."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import io
import json
from typing import Any, Iterator

import streamlit as st

from catalyst_ai.ai.schemas import (
    ArtifactMetadata,
    ArtifactType,
    DiscoveryResolution,
    DiscoveryResult,
    GeneratedArtifact,
    ProductUnderstanding,
    ValidatedProductContext,
)
from catalyst_ai.auth.database import database_connection


PERSISTED_SESSION_KEYS = (
    "discovery_result",
    "discovery_resolutions",
    "validated_product_context",
    "product_context_hash",
    "product_understanding",
    "product_understanding_context_source",
    "product_understanding_stakeholder",
    "product_understanding_source_hash",
    "generated_artifact",
    "generated_artifact_type",
    "generated_artifact_metadata",
)


class RestoredUploadedFile(io.BytesIO):
    """Small UploadedFile-compatible object reconstructed from persisted bytes."""

    def __init__(self, name: str, content: bytes, mime_type: str = "") -> None:
        super().__init__(content)
        self.name = name
        self.type = mime_type
        self.size = len(content)

    def getvalue(self) -> bytes:
        position = self.tell()
        self.seek(0)
        value = self.read()
        self.seek(position)
        return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def initialize_workflow_persistence() -> None:
    """Create the single-snapshot persistence table when needed."""
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS project_workflow_snapshots (
                project_id INTEGER PRIMARY KEY,
                snapshot_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )


def _model_payload(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, ArtifactType):
        return value.value
    return value


def _serialize_session() -> dict[str, Any]:
    session: dict[str, Any] = {}
    for key in PERSISTED_SESSION_KEYS:
        value = st.session_state.get(key)
        if key == "discovery_resolutions" and isinstance(value, dict):
            session[key] = {
                finding_id: _model_payload(resolution)
                for finding_id, resolution in value.items()
            }
        else:
            session[key] = _model_payload(value)
    return session


def _deserialize_session(payload: dict[str, Any]) -> dict[str, Any]:
    restored = dict(payload)
    if restored.get("discovery_result"):
        restored["discovery_result"] = DiscoveryResult.model_validate(restored["discovery_result"])
    restored["discovery_resolutions"] = {
        finding_id: DiscoveryResolution.model_validate(value)
        for finding_id, value in (restored.get("discovery_resolutions") or {}).items()
    }
    if restored.get("validated_product_context"):
        restored["validated_product_context"] = ValidatedProductContext.model_validate(
            restored["validated_product_context"]
        )
    if restored.get("product_understanding"):
        restored["product_understanding"] = ProductUnderstanding.model_validate(
            restored["product_understanding"]
        )
    if restored.get("generated_artifact"):
        restored["generated_artifact"] = GeneratedArtifact.model_validate(
            restored["generated_artifact"]
        )
    if restored.get("generated_artifact_type"):
        restored["generated_artifact_type"] = ArtifactType(restored["generated_artifact_type"])
    if restored.get("generated_artifact_metadata"):
        restored["generated_artifact_metadata"] = ArtifactMetadata.model_validate(
            restored["generated_artifact_metadata"]
        )
    return restored


def _serialize_uploaded_files(uploaded_files: Any) -> list[dict[str, str]]:
    records = []
    for uploaded_file in uploaded_files or []:
        try:
            content = uploaded_file.getvalue()
        except Exception:
            continue
        records.append(
            {
                "name": str(uploaded_file.name),
                "mime_type": str(getattr(uploaded_file, "type", "") or ""),
                "content": base64.b64encode(content).decode("ascii"),
            }
        )
    return records


def _deserialize_uploaded_files(records: list[dict[str, str]]) -> list[RestoredUploadedFile]:
    restored = []
    for record in records:
        restored.append(
            RestoredUploadedFile(
                name=record["name"],
                mime_type=record.get("mime_type", ""),
                content=base64.b64decode(record["content"]),
            )
        )
    return restored


def load_project_workflow(project_id: int) -> list[RestoredUploadedFile]:
    """Restore one project's workflow state into the current Streamlit session."""
    initialize_workflow_persistence()
    with database_connection() as connection:
        row = connection.execute(
            "SELECT snapshot_json FROM project_workflow_snapshots WHERE project_id = ?",
            (project_id,),
        ).fetchone()

    if row is None:
        return []

    snapshot = json.loads(row["snapshot_json"])
    for key, value in _deserialize_session(snapshot.get("session", {})).items():
        st.session_state[key] = value
    st.session_state["persisted_product_context"] = snapshot.get("product_context")
    return _deserialize_uploaded_files(snapshot.get("uploaded_files", []))


def save_project_workflow(project_id: int, workflow_module: Any) -> None:
    """Persist the current workflow module and session state as one project snapshot."""
    initialize_workflow_persistence()
    product_context = getattr(workflow_module, "product_context", None)
    if product_context is None:
        product_context = st.session_state.get("persisted_product_context")
    else:
        st.session_state["persisted_product_context"] = product_context

    snapshot = {
        "version": 1,
        "session": _serialize_session(),
        "product_context": product_context,
        "uploaded_files": _serialize_uploaded_files(
            getattr(workflow_module, "uploaded_files", None)
        ),
    }
    encoded = json.dumps(snapshot, ensure_ascii=False)
    now = _utc_now()
    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO project_workflow_snapshots (project_id, snapshot_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                snapshot_json = excluded.snapshot_json,
                updated_at = excluded.updated_at
            """,
            (project_id, encoded, now),
        )
        connection.execute(
            "UPDATE projects SET last_activity_at = ?, updated_at = ? WHERE id = ?",
            (now, now, project_id),
        )


@contextmanager
def restored_file_uploader(files: list[RestoredUploadedFile]) -> Iterator[None]:
    """Use persisted files only when the user has not selected replacement uploads."""
    original = st.file_uploader

    def wrapped_file_uploader(*args, **kwargs):
        selected = original(*args, **kwargs)
        return selected or files

    st.file_uploader = wrapped_file_uploader
    try:
        yield
    finally:
        st.file_uploader = original
