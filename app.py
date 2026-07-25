"""Authenticated, project-aware entry point for Catalyst AI."""

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.ui import require_authenticated_user, render_authenticated_sidebar
from catalyst_ai.projects.ui import (
    get_selected_project,
    render_project_dashboard,
    render_project_sidebar,
)


initialize_database()
current_user = require_authenticated_user()
selected_project = get_selected_project(current_user)

if selected_project is None:
    render_authenticated_sidebar(current_user)
    render_project_dashboard(current_user)
else:
    render_project_sidebar(selected_project)
    render_authenticated_sidebar(current_user)

    # The validated Catalyst AI workflow executes only inside an authenticated,
    # authorized project workspace. Sprint 3 will persist workflow state by project.
    from catalyst_ai import workflow_app  # noqa: E402,F401
