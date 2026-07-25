"""Central role and permission policy for Catalyst AI projects."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


PROJECT_ROLES = ("OWNER", "ADMIN", "EDITOR", "REVIEWER")
ASSIGNABLE_ROLES = ("ADMIN", "EDITOR", "REVIEWER")

_PERMISSION_ROLES = {
    "view_project": set(PROJECT_ROLES),
    "modify_workflow": {"OWNER", "ADMIN", "EDITOR"},
    "manage_members": {"OWNER", "ADMIN"},
    "change_project_settings": {"OWNER", "ADMIN"},
    "archive_project": {"OWNER"},
    "delete_project": {"OWNER"},
}


def has_permission(role: str, permission: str) -> bool:
    """Return whether a project role grants a named permission."""
    return role.upper() in _PERMISSION_ROLES.get(permission, set())


def require_permission(role: str, permission: str) -> None:
    """Raise a stable authorization error when permission is missing."""
    if not has_permission(role, permission):
        raise PermissionError("You do not have permission to perform this project action.")


@contextmanager
def read_only_workflow(enabled: bool) -> Iterator[None]:
    """Disable workflow mutation controls while retaining review and download access."""
    if not enabled:
        yield
        return

    original_button = st.button
    original_form_submit_button = st.form_submit_button
    original_file_uploader = st.file_uploader

    def disabled_button(*args, **kwargs):
        kwargs["disabled"] = True
        return original_button(*args, **kwargs)

    def disabled_form_submit_button(*args, **kwargs):
        kwargs["disabled"] = True
        return original_form_submit_button(*args, **kwargs)

    def disabled_file_uploader(*args, **kwargs):
        kwargs["disabled"] = True
        return original_file_uploader(*args, **kwargs)

    st.button = disabled_button
    st.form_submit_button = disabled_form_submit_button
    st.file_uploader = disabled_file_uploader
    try:
        yield
    finally:
        st.button = original_button
        st.form_submit_button = original_form_submit_button
        st.file_uploader = original_file_uploader
