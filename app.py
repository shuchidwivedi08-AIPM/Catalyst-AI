"""Authenticated entry point for Catalyst AI."""

from catalyst_ai.auth.database import initialize_database
from catalyst_ai.auth.ui import require_authenticated_user, render_authenticated_sidebar


initialize_database()
current_user = require_authenticated_user()

# Importing the workflow executes the existing Streamlit application only after
# authentication succeeds. Keeping it isolated preserves the validated product
# workflow while Sprint 1 introduces identity and route protection.
from catalyst_ai import workflow_app  # noqa: E402,F401

render_authenticated_sidebar(current_user)
