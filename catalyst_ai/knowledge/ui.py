"""Streamlit UI for project knowledge documents."""
from __future__ import annotations

import streamlit as st

from catalyst_ai.knowledge.service import (
    KnowledgeError,
    archive_knowledge_document,
    download_knowledge_document,
    list_knowledge_documents,
    upload_knowledge_document,
)
from catalyst_ai.projects.permissions import has_permission


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def render_project_knowledge(project, current_user) -> None:
    """Render durable project knowledge upload, listing, download, and archive actions."""
    st.title("Project knowledge")
    st.caption(project.name)
    st.write(
        "Store long-lived reference documents separately from the business documents "
        "used in the current analysis workflow. RAG indexing will be added in a later sprint."
    )
    can_manage = has_permission(project.user_role, "manage_knowledge")

    if can_manage:
        with st.expander("Upload knowledge document", expanded=False):
            with st.form("upload_project_knowledge", clear_on_submit=True):
                uploaded = st.file_uploader(
                    "Knowledge file",
                    type=["pdf", "docx", "txt"],
                    help="Maximum file size: 25 MB.",
                )
                submitted = st.form_submit_button("Upload to project knowledge", use_container_width=True)
            if submitted:
                if uploaded is None:
                    st.error("Select a knowledge document to upload.")
                else:
                    try:
                        upload_knowledge_document(
                            project.id,
                            current_user.id,
                            uploaded.name,
                            getattr(uploaded, "type", "") or "application/octet-stream",
                            uploaded.getvalue(),
                        )
                    except KnowledgeError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("The knowledge document could not be stored. Check Supabase Storage configuration.")
                    else:
                        st.success("Knowledge document uploaded.")
                        st.rerun()
    else:
        st.info("Reviewer access is read-only. You can view and download project knowledge.")

    st.divider()
    try:
        documents = list_knowledge_documents(project.id, current_user.id)
    except KnowledgeError as exc:
        st.error(str(exc))
        return

    if not documents:
        st.info("No project knowledge documents have been uploaded yet.")
        return

    for document in documents:
        with st.container(border=True):
            title_col, meta_col = st.columns([3, 1])
            title_col.markdown(f"**{document.file_name}**")
            title_col.caption(f"Version {document.version} · {document.file_type.upper()} · {_format_size(document.size_bytes)}")
            meta_col.markdown(f"**{document.status.title()}**")
            meta_col.caption(document.created_at.replace("T", " ")[:19])
            action_columns = st.columns([1, 1, 3])
            if action_columns[0].button("Prepare download", key=f"prepare_knowledge_{document.id}"):
                try:
                    downloaded, content = download_knowledge_document(project.id, current_user.id, document.id)
                except Exception:
                    st.error("The knowledge document could not be downloaded from storage.")
                else:
                    st.session_state[f"knowledge_download_{document.id}"] = content
                    st.session_state[f"knowledge_download_name_{document.id}"] = downloaded.file_name
            content = st.session_state.get(f"knowledge_download_{document.id}")
            if content is not None:
                action_columns[1].download_button(
                    "Download",
                    data=content,
                    file_name=st.session_state[f"knowledge_download_name_{document.id}"],
                    mime=document.mime_type,
                    key=f"download_knowledge_{document.id}",
                )
            if can_manage and action_columns[2].button("Archive", key=f"archive_knowledge_{document.id}"):
                try:
                    archive_knowledge_document(project.id, current_user.id, document.id)
                except KnowledgeError as exc:
                    st.error(str(exc))
                else:
                    st.success("Knowledge document archived.")
                    st.rerun()
