"""Streamlit authentication UI for Catalyst AI."""

from __future__ import annotations

import time

import streamlit as st

from catalyst_ai.auth.service import (
    AuthenticationError,
    BootstrapError,
    authenticate_user,
    bootstrap_initial_admin,
    has_users,
)


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 30


def initialize_auth_session() -> None:
    """Initialize authentication keys that survive Streamlit reruns."""
    st.session_state.setdefault("authenticated_user", None)
    st.session_state.setdefault("login_attempts", 0)
    st.session_state.setdefault("login_locked_until", 0.0)


def _render_branding() -> None:
    st.title("Catalyst AI")
    st.subheader("Understand. Validate. Reason. Generate.")
    st.caption("Enterprise AI-powered product discovery and requirement intelligence.")


def render_initial_admin_setup() -> None:
    """Render one-time administrator creation when the database is empty."""
    _render_branding()
    st.info(
        "Create the initial administrator account. This setup screen is disabled "
        "after the first account is created."
    )
    with st.form("initial_admin_setup", clear_on_submit=False):
        display_name = st.text_input("Display name", autocomplete="name")
        username = st.text_input("Username", autocomplete="username")
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input(
            "Password", type="password", autocomplete="new-password",
            help="Use at least 12 characters."
        )
        confirm_password = st.text_input(
            "Confirm password", type="password", autocomplete="new-password"
        )
        submitted = st.form_submit_button("Create administrator", use_container_width=True)

    if submitted:
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
        try:
            user = bootstrap_initial_admin(username, email, display_name, password)
        except BootstrapError as exc:
            st.error(str(exc))
            return
        st.session_state["authenticated_user"] = user
        st.success("Administrator account created.")
        st.rerun()


def render_login() -> None:
    """Render username/password authentication with basic attempt throttling."""
    _render_branding()
    st.write("Sign in to access your Catalyst AI projects and product workflows.")

    remaining_lockout = max(
        0, int(st.session_state["login_locked_until"] - time.monotonic())
    )
    if remaining_lockout:
        st.warning(f"Too many unsuccessful attempts. Try again in {remaining_lockout} seconds.")

    with st.form("login_form", clear_on_submit=False):
        identifier = st.text_input("Username or email", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button(
            "Sign in", use_container_width=True, disabled=remaining_lockout > 0
        )

    if submitted:
        try:
            user = authenticate_user(identifier, password)
        except AuthenticationError as exc:
            attempts = st.session_state["login_attempts"] + 1
            st.session_state["login_attempts"] = attempts
            if attempts >= MAX_LOGIN_ATTEMPTS:
                st.session_state["login_locked_until"] = time.monotonic() + LOCKOUT_SECONDS
                st.session_state["login_attempts"] = 0
            st.error(str(exc))
            return

        st.session_state["authenticated_user"] = user
        st.session_state["login_attempts"] = 0
        st.session_state["login_locked_until"] = 0.0
        st.rerun()


def require_authenticated_user():
    """Render the correct entry experience and stop unauthenticated execution."""
    initialize_auth_session()
    user = st.session_state["authenticated_user"]
    if user is not None:
        return user

    if has_users():
        render_login()
    else:
        render_initial_admin_setup()
    st.stop()


def render_authenticated_sidebar(user) -> None:
    """Display current identity and provide session logout."""
    with st.sidebar:
        st.divider()
        st.caption("Signed in as")
        st.markdown(f"**{user.display_name}**")
        st.caption(user.username)
        if st.button("Log out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
