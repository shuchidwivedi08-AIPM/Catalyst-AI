"""Tests for durable project knowledge metadata and permissions."""
import pytest

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.service import bootstrap_initial_admin, register_user
from catalyst_ai.knowledge import service as knowledge_service
from catalyst_ai.knowledge.service import (
    KnowledgeError,
    archive_knowledge_document,
    list_knowledge_documents,
    upload_knowledge_document,
)
from catalyst_ai.projects.members import add_project_member
from catalyst_ai.projects.service import create_project


@pytest.fixture
def knowledge_database(tmp_path, monkeypatch):
    database_path = tmp_path / "knowledge-test.db"
    monkeypatch.setenv("CATALYST_DATABASE_PATH", str(database_path))
    initialize_database(database_path)
    stored = {}
    monkeypatch.setattr(knowledge_service, "upload_object", lambda path, content, mime: stored.__setitem__(path, content))
    monkeypatch.setattr(knowledge_service, "download_object", lambda path: stored[path])
    monkeypatch.setattr(knowledge_service, "delete_object", lambda path: stored.pop(path, None))
    return stored


def _users_and_project():
    owner = bootstrap_initial_admin("owner", "owner@example.com", "Owner", "A-secure-password-123")
    editor = register_user("editor", "editor@example.com", "Editor", "A-secure-password-123")
    reviewer = register_user("reviewer", "reviewer@example.com", "Reviewer", "A-secure-password-123")
    project = create_project(owner.id, "Knowledge Project")
    add_project_member(project.id, owner.id, editor.id, "EDITOR")
    add_project_member(project.id, owner.id, reviewer.id, "REVIEWER")
    return owner, editor, reviewer, project


def test_editor_can_upload_and_versions_increment(knowledge_database):
    owner, editor, reviewer, project = _users_and_project()
    first = upload_knowledge_document(project.id, editor.id, "standards.txt", "text/plain", b"version one")
    second = upload_knowledge_document(project.id, editor.id, "standards.txt", "text/plain", b"version two")
    assert first.version == 1
    assert second.version == 2
    assert len(list_knowledge_documents(project.id, reviewer.id)) == 2


def test_duplicate_content_is_rejected(knowledge_database):
    owner, editor, reviewer, project = _users_and_project()
    upload_knowledge_document(project.id, owner.id, "policy.txt", "text/plain", b"same content")
    with pytest.raises(KnowledgeError, match="already present"):
        upload_knowledge_document(project.id, editor.id, "copy.txt", "text/plain", b"same content")


def test_reviewer_cannot_upload_but_can_list(knowledge_database):
    owner, editor, reviewer, project = _users_and_project()
    upload_knowledge_document(project.id, owner.id, "policy.txt", "text/plain", b"policy")
    assert len(list_knowledge_documents(project.id, reviewer.id)) == 1
    with pytest.raises(KnowledgeError, match="permission"):
        upload_knowledge_document(project.id, reviewer.id, "review.txt", "text/plain", b"review")


def test_archive_hides_document(knowledge_database):
    owner, editor, reviewer, project = _users_and_project()
    document = upload_knowledge_document(project.id, owner.id, "policy.txt", "text/plain", b"policy")
    archive_knowledge_document(project.id, owner.id, document.id)
    assert list_knowledge_documents(project.id, owner.id) == []
    assert len(list_knowledge_documents(project.id, owner.id, include_archived=True)) == 1
