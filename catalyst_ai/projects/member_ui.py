"""Streamlit member-management experience for project owners and admins."""

from __future__ import annotations

import streamlit as st

from catalyst_ai.projects.members import (
    MembershipError,
    add_project_member,
    list_project_members,
    remove_project_member,
    update_project_member_role,
)
from catalyst_ai.projects.permissions import ASSIGNABLE_ROLES, has_permission


def render_project_members(project, current_user) -> None:
    """Render project membership settings with role-aware actions."""
    st.title("Project members")
    st.caption(project.name)
    can_manage = has_permission(project.user_role, "manage_members")

    if can_manage:
        with st.expander("Add member", expanded=False):
            st.write("Add an existing active Catalyst AI user by username or email.")
            with st.form("add_project_member", clear_on_submit=True):
                identifier = st.text_input("Username or email")
                role = st.selectbox(
                    "Project role",
                    ASSIGNABLE_ROLES,
                    format_func=lambda value: value.title(),
                )
                submitted = st.form_submit_button("Add member", use_container_width=True)
            if submitted:
                try:
                    add_project_member(project.id, current_user.id, identifier, role)
                except MembershipError as exc:
                    st.error(str(exc))
                else:
                    st.success("Project member added.")
                    st.rerun()
    else:
        st.info("Only the project owner or an admin can manage members.")

    st.divider()
    members = list_project_members(project.id, current_user.id)
    for member in members:
        with st.container(border=True):
            identity, role_column, action_column = st.columns([3, 2, 2])
            identity.markdown(f"**{member.display_name}**")
            identity.caption(f"{member.username} · {member.email}")

            if member.role == "OWNER" or not can_manage:
                role_column.markdown(f"**{member.role.title()}**")
                action_column.caption("Protected" if member.role == "OWNER" else member.status.title())
                continue

            new_role = role_column.selectbox(
                "Role",
                ASSIGNABLE_ROLES,
                index=ASSIGNABLE_ROLES.index(member.role),
                format_func=lambda value: value.title(),
                key=f"member_role_{member.user_id}",
                label_visibility="collapsed",
            )
            save_col, remove_col = action_column.columns(2)
            if save_col.button("Save", key=f"save_member_{member.user_id}"):
                try:
                    update_project_member_role(
                        project.id, current_user.id, member.user_id, new_role
                    )
                except MembershipError as exc:
                    st.error(str(exc))
                else:
                    st.success("Member role updated.")
                    st.rerun()
            if remove_col.button("Remove", key=f"remove_member_{member.user_id}"):
                try:
                    remove_project_member(project.id, current_user.id, member.user_id)
                except MembershipError as exc:
                    st.error(str(exc))
                else:
                    st.success("Member removed from the project.")
                    st.rerun()
