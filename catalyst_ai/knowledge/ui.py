"""Streamlit UI for project knowledge documents."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from catalyst_ai.knowledge.service import (
    KnowledgeError,
    archive_knowledge_document,
    download_knowledge_document,
    list_knowledge_documents,
    permanently_delete_knowledge_document,
    restore_knowledge_document,
    upload_knowledge_document,
)
from catalyst_ai.projects.permissions import has_permission


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_datetime(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def _render_upload_report() -> None:
    report = st.session_state.pop("knowledge_upload_report", None)
    if not report:
        return
    uploaded = report.get("uploaded", [])
    errors = report.get("errors", [])
    if uploaded:
        summary = ", ".join(f"{name} (v{version})" for name, version in uploaded)
        st.success(f"Uploaded {len(uploaded)} document(s): {summary}")
    for file_name, message in errors:
        st.error(f"{file_name}: {message}")


def _render_upload(project, current_user) -> None:
    with st.expander("Upload knowledge documents", expanded=False):
        with st.form("upload_project_knowledge", clear_on_submit=True):
            uploaded_files = st.file_uploader(
                "Knowledge files",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                help="Select one or more files. Maximum size per file: 25 MB.",
            )
            submitted = st.form_submit_button("Upload to project knowledge", use_container_width=True)
        if not submitted:
            return
        if not uploaded_files:
            st.error("Select at least one knowledge document to upload.")
            return

        uploaded_report: list[tuple[str, int]] = []
        error_report: list[tuple[str, str]] = []
        with st.spinner(f"Uploading {len(uploaded_files)} document(s)…"):
            for uploaded in uploaded_files:
                try:
                    document = upload_knowledge_document(
                        project.id,
                        current_user.id,
                        uploaded.name,
                        getattr(uploaded, "type", "") or "application/octet-stream",
                        uploaded.getvalue(),
                    )
                except KnowledgeError as exc:
                    error_report.append((uploaded.name, str(exc)))
                except Exception:
                    error_report.append(
                        (uploaded.name, "Could not be stored. Check Supabase Storage configuration.")
                    )
                else:
                    uploaded_report.append((document.file_name, document.version))

        st.session_state["knowledge_upload_report"] = {
            "uploaded": uploaded_report,
            "errors": error_report,
        }
        st.rerun()


def _filter_and_sort(documents):
    search_col, type_col, status_col = st.columns([2, 1, 1])
    search_text = search_col.text_input(
        "Search",
        placeholder="Search by file name or uploader",
        key="knowledge_search",
    ).strip().lower()
    available_types = sorted({document.file_type.upper() for document in documents})
    file_type = type_col.selectbox("File type", ["All", *available_types], key="knowledge_type_filter")
    status = status_col.selectbox("Status", ["Active", "Archived", "All"], key="knowledge_status_filter")

    sort_col, versions_col = st.columns([2, 1])
    sort_order = sort_col.selectbox(
        "Sort by",
        ["Newest first", "Oldest first", "File name A–Z", "Highest version first"],
        key="knowledge_sort",
    )
    show_all_versions = versions_col.checkbox(
        "Show all versions",
        value=False,
        help="When disabled, only the latest version of each file name is shown.",
        key="knowledge_show_versions",
    )

    filtered = []
    for document in documents:
        if search_text and search_text not in document.file_name.lower() and search_text not in document.uploader_display_name.lower():
            continue
        if file_type != "All" and document.file_type.upper() != file_type:
            continue
        if status == "Active" and document.status == "ARCHIVED":
            continue
        if status == "Archived" and document.status != "ARCHIVED":
            continue
        filtered.append(document)

    if not show_all_versions:
        latest_by_name = {}
        for document in filtered:
            current = latest_by_name.get(document.file_name)
            if current is None or document.version > current.version:
                latest_by_name[document.file_name] = document
        filtered = list(latest_by_name.values())

    if sort_order == "Oldest first":
        filtered.sort(key=lambda item: item.created_at)
    elif sort_order == "File name A–Z":
        filtered.sort(key=lambda item: (item.file_name.lower(), -item.version))
    elif sort_order == "Highest version first":
        filtered.sort(key=lambda item: (item.version, item.created_at), reverse=True)
    else:
        filtered.sort(key=lambda item: item.created_at, reverse=True)
    return filtered


def _prepare_download(project, current_user, document) -> None:
    try:
        downloaded, content = download_knowledge_document(project.id, current_user.id, document.id)
    except Exception:
        st.error("The knowledge document could not be downloaded from storage.")
    else:
        st.session_state[f"knowledge_download_{document.id}"] = content
        st.session_state[f"knowledge_download_name_{document.id}"] = downloaded.file_name


def _render_document(project, current_user, document, latest_version: int, can_manage: bool, can_delete: bool) -> None:
    with st.container(border=True):
        title_col, status_col = st.columns([4, 1])
        latest_label = " · Latest" if document.version == latest_version else ""
        title_col.markdown(f"**{document.file_name}**")
        title_col.caption(
            f"Version {document.version}{latest_label} · {document.file_type.upper()} · {_format_size(document.size_bytes)}"
        )
        status_col.markdown(f"**{document.status.title()}**")

        metadata_col1, metadata_col2, metadata_col3 = st.columns(3)
        metadata_col1.caption("Uploaded by")
        metadata_col1.write(document.uploader_display_name)
        metadata_col2.caption("Uploaded")
        metadata_col2.write(_format_datetime(document.created_at))
        metadata_col3.caption("Checksum")
        metadata_col3.code(document.checksum[:12], language=None)
        if document.status == "ARCHIVED":
            st.caption(f"Archived: {_format_datetime(document.archived_at)}")

        action_columns = st.columns([1, 1, 1, 2])
        if action_columns[0].button("Prepare", key=f"prepare_knowledge_{document.id}"):
            _prepare_download(project, current_user, document)
        content = st.session_state.get(f"knowledge_download_{document.id}")
        if content is not None:
            action_columns[1].download_button(
                "Download",
                data=content,
                file_name=st.session_state[f"knowledge_download_name_{document.id}"],
                mime=document.mime_type,
                key=f"download_knowledge_{document.id}",
            )

        if can_manage and document.status != "ARCHIVED":
            if action_columns[2].button("Archive", key=f"archive_knowledge_{document.id}"):
                try:
                    archive_knowledge_document(project.id, current_user.id, document.id)
                except KnowledgeError as exc:
                    st.error(str(exc))
                else:
                    st.success("Knowledge document archived.")
                    st.rerun()
        elif can_manage and document.status == "ARCHIVED":
            if action_columns[2].button("Restore", key=f"restore_knowledge_{document.id}"):
                try:
                    restore_knowledge_document(project.id, current_user.id, document.id)
                except KnowledgeError as exc:
                    st.error(str(exc))
                else:
                    st.success("Knowledge document restored.")
                    st.rerun()

        if can_delete and document.status == "ARCHIVED":
            with st.expander("Permanent deletion", expanded=False):
                st.warning("This removes both the Supabase Storage object and its metadata. It cannot be undone.")
                confirmed = st.checkbox(
                    f"Permanently delete {document.file_name} version {document.version}",
                    key=f"confirm_delete_knowledge_{document.id}",
                )
                if st.button(
                    "Delete permanently",
                    key=f"delete_knowledge_{document.id}",
                    disabled=not confirmed,
                ):
                    try:
                        permanently_delete_knowledge_document(project.id, current_user.id, document.id)
                    except KnowledgeError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("The archived object could not be permanently deleted from storage.")
                    else:
                        st.session_state.pop(f"knowledge_download_{document.id}", None)
                        st.session_state.pop(f"knowledge_download_name_{document.id}", None)
                        st.success("Knowledge document permanently deleted.")
                        st.rerun()


def render_project_knowledge(project, current_user) -> None:
    """Render durable project knowledge upload, discovery, and lifecycle actions."""
    st.title("Project knowledge")
    st.caption(project.name)
    st.write(
        "Store long-lived reference documents separately from documents used in the current "
        "analysis workflow. RAG indexing will be added in a later sprint."
    )
    can_manage = has_permission(project.user_role, "manage_knowledge")
    can_delete = has_permission(project.user_role, "delete_knowledge")

    _render_upload_report()
    if can_manage:
        _render_upload(project, current_user)
    else:
        st.info("Reviewer access is read-only. You can search, inspect, and download project knowledge.")

    st.divider()
    try:
        documents = list_knowledge_documents(project.id, current_user.id, include_archived=True)
    except KnowledgeError as exc:
        st.error(str(exc))
        return

    if not documents:
        st.info("No project knowledge documents have been uploaded yet.")
        return

    latest_versions = {}
    for document in documents:
        latest_versions[document.file_name] = max(latest_versions.get(document.file_name, 0), document.version)

    active_count = sum(document.status != "ARCHIVED" for document in documents)
    archived_count = len(documents) - active_count
    total_size = sum(document.size_bytes for document in documents if document.status != "ARCHIVED")
    metric_columns = st.columns(3)
    metric_columns[0].metric("Active documents", active_count)
    metric_columns[1].metric("Archived versions", archived_count)
    metric_columns[2].metric("Active storage", _format_size(total_size))

    visible_documents = _filter_and_sort(documents)
    st.caption(f"Showing {len(visible_documents)} of {len(documents)} stored version(s).")
    if not visible_documents:
        st.info("No knowledge documents match the selected filters.")
        return

    for document in visible_documents:
        _render_document(
            project,
            current_user,
            document,
            latest_versions[document.file_name],
            can_manage,
            can_delete,
        )
