"""Authenticated, project-aware entry point for Catalyst AI."""

import importlib
import sys

import streamlit as st

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.ui import require_authenticated_user, render_authenticated_sidebar
from catalyst_ai.projects.ui import get_selected_project, render_project_dashboard, render_project_sidebar
from catalyst_ai.projects.workflow_persistence import (
    initialize_workflow_persistence,
    load_project_workflow,
    restored_file_uploader,
    save_project_workflow,
)


initialize_database()
initialize_workflow_persistence()
current_user = require_authenticated_user()
selected_project = get_selected_project(current_user)

if selected_project is None:
    render_authenticated_sidebar(current_user)
    render_project_dashboard(current_user)
else:
    render_project_sidebar(selected_project)
    render_authenticated_sidebar(current_user)

    loaded_project_id = st.session_state.get("workflow_state_loaded_project_id")
    if loaded_project_id != selected_project.id:
        restored_files = load_project_workflow(selected_project.id)
        st.session_state["workflow_state_loaded_project_id"] = selected_project.id
        st.session_state["restored_uploaded_files"] = restored_files
    else:
        restored_files = st.session_state.get("restored_uploaded_files", [])

    # Execute the validated workflow inside the selected project boundary. A reload
    # is required because Streamlit reruns the entry script while Python caches imports.
    with restored_file_uploader(restored_files):
        module_name = "catalyst_ai.workflow_app"
        if module_name in sys.modules:
            workflow_app = importlib.reload(sys.modules[module_name])
        else:
            workflow_app = importlib.import_module(module_name)

    save_project_workflow(selected_project.id, workflow_app)
