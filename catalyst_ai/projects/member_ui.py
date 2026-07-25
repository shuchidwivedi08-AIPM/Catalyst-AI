"""Streamlit member-management experience for project owners and admins."""

from __future__ import annotations

import streamlit as st

from catalyst_ai.projects.members import (
    MembershipError,
    add_project_member,
    list_project_members,
    remove_project_member,
    search_available_users,
    update_project_member_role,
)
from catalyst_ai.projects.permissions import ASSIGNABLE_ROLES, has_permission


def _render_add_member(project, current_user) -> None:
    with st.expander("Add member", expanded=False):
        st.write("Search and select an existing active Catalyst AI user.")
        query = st.text_input(
            "Search users",
            placeholder="Enter at least 2 characters of a name, username, or email",
            key="member_user_search",
        )
        results = []
        if len(query.strip()) >= 2:
            try:
                results = search_available_users(project.id, current_user.id, query)
            except MembershipError as exc:
                st.error(str(exc))
                return
            if not results:
                st.info("No available active users match this search.")

        options = {entry.user_id: entry for entry in results}
        selected_user_id = st.selectbox(
            "Select user",
            options=list(options),
            format_func=lambda user_id: (
                f"{options[user_id].display_name} · {options[user_id].username} · "
                f"{options[user_id].email}"
                + (
                    " · Previously removed"
                    if options[user_id].previous_membership_status == "REMOVED"
                    else ""
                )
            ),
            disabled=not options,
            key="selected_project_member_user",
        )
        role = st.selectbox(
            "Project role",
            ASSIGNABLE_ROLES,
            format_func=lambda value: value.title(),
            key="new_project_member_role",
        )
        if st.button(
            "Add member",
            use_container_width=True,
            disabled=selected_user_id is None,
            key="add_selected_project_member",
        ):
            try:
                add_project_member(project.id, current_user.id, int(selected_user_id), role)
            except MembershipError as exc:
                st.error(str(exc))
            else:
                st.success("Project member added.")
                st.session_state.pop("member_user_search", None)
                st.session_state.pop("selected_project_member_user", None)
                st.rerun()


def render_project_members(project, current_user) -> None:
    """Render project membership settings with role-aware actions."""
    st.title("Project members")
    st.caption(project.name)
    can_manage = has_permission(project.user_role, "manage_members")

    if can_manage:
        _render_add_member(project, current_user)
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
