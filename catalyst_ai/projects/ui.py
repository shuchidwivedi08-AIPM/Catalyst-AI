"""Streamlit project dashboard and workspace navigation."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from catalyst_ai.projects.models import Project
from catalyst_ai.projects.service import ProjectError, create_project, get_accessible_project, list_user_projects


_WORKFLOW_STATE_KEYS = {
    "discovery_result", "discovery_resolutions", "validated_product_context",
    "product_context_hash", "product_understanding",
    "product_understanding_context_source", "product_understanding_stakeholder",
    "product_understanding_source_hash", "generated_artifact",
    "generated_artifact_type", "generated_artifact_metadata",
    "persisted_product_context", "restored_uploaded_files",
    "workflow_state_loaded_project_id",
}


def initialize_project_session() -> None:
    st.session_state.setdefault("selected_project_id", None)


def _clear_workflow_session() -> None:
    for key in list(st.session_state):
        if key in _WORKFLOW_STATE_KEYS or key.startswith(("status_", "answer_", "save_")):
            del st.session_state[key]


def select_project(project: Project) -> None:
    if st.session_state.get("selected_project_id") != project.id:
        _clear_workflow_session()
    st.session_state["selected_project_id"] = project.id


def leave_project() -> None:
    _clear_workflow_session()
    st.session_state["selected_project_id"] = None


def _format_activity(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def _render_create_project(user_id: int) -> None:
    with st.expander("Create new project", expanded=False):
        with st.form("create_project_form", clear_on_submit=True):
            name = st.text_input("Project name", max_chars=100)
            description = st.text_area("Description", max_chars=1000)
            submitted = st.form_submit_button("Create project", use_container_width=True)
        if submitted:
            try:
                project = create_project(user_id, name, description)
            except ProjectError as exc:
                st.error(str(exc))
                return
            select_project(project)
            st.rerun()


def render_project_dashboard(user) -> None:
    initialize_project_session()
    st.title("Catalyst AI")
    st.subheader(f"Welcome back, {user.display_name}")
    st.write("Select a project to continue or create a new product workspace.")
    _render_create_project(user.id)
    st.divider()
    st.header("Your projects")

    projects = list_user_projects(user.id)
    if not projects:
        st.info("No projects yet. Create your first project to begin the Catalyst AI workflow.")
        return

    for project in projects:
        with st.container(border=True):
            title_col, role_col = st.columns([3, 1])
            title_col.subheader(project.name)
            role_col.markdown(f"**{project.user_role.title()}**")
            if project.description:
                st.write(project.description)
            stage_col, status_col, activity_col = st.columns(3)
            stage_col.caption("Current stage")
            stage_col.write(project.workflow_stage.replace("_", " ").title())
            status_col.caption("Status")
            status_col.write(project.status.replace("_", " ").title())
            activity_col.caption("Last activity")
            activity_col.write(_format_activity(project.last_activity_at))
            label = "Review project" if project.user_role == "REVIEWER" else "Continue project"
            if st.button(label, key=f"open_project_{project.id}", use_container_width=True):
                select_project(project)
                st.rerun()


def get_selected_project(user) -> Project | None:
    initialize_project_session()
    project_id = st.session_state.get("selected_project_id")
    if project_id is None:
        return None
    try:
        return get_accessible_project(user.id, int(project_id))
    except (ProjectError, TypeError, ValueError):
        leave_project()
        return None


def render_project_sidebar(project: Project) -> None:
    with st.sidebar:
        st.caption("Active project")
        st.markdown(f"### {project.name}")
        st.caption(f"Role: {project.user_role.title()}")
        st.caption(f"Stage: {project.workflow_stage.replace('_', ' ').title()}")
        if st.button("Back to projects", use_container_width=True):
            leave_project()
            st.rerun()
        st.divider()
