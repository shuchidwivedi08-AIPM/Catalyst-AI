"""Streamlit authentication and signup UI for Catalyst AI."""

from __future__ import annotations

import time

import streamlit as st

from catalyst_ai.auth.service import (
    AuthenticationError,
    BootstrapError,
    RegistrationError,
    authenticate_user,
    bootstrap_initial_admin,
    has_users,
    register_user,
)


MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 30


def initialize_auth_session() -> None:
    """Initialize authentication keys that survive Streamlit reruns."""
    st.session_state.setdefault("authenticated_user", None)
    st.session_state.setdefault("login_attempts", 0)
    st.session_state.setdefault("login_locked_until", 0.0)
    st.session_state.setdefault("auth_view", "login")
    st.session_state.setdefault("registration_success", False)


def _render_branding() -> None:
    st.title("Catalyst AI")
    st.subheader("Understand. Validate. Reason. Generate.")
    st.caption("Enterprise AI-powered product discovery and requirement intelligence.")


def _account_form(form_key: str, submit_label: str):
    with st.form(form_key, clear_on_submit=False):
        display_name = st.text_input("Display name", autocomplete="name")
        username = st.text_input("Username", autocomplete="username")
        email = st.text_input("Email", autocomplete="email")
        password = st.text_input(
            "Password",
            type="password",
            autocomplete="new-password",
            help="Use at least 12 characters.",
        )
        confirm_password = st.text_input(
            "Confirm password", type="password", autocomplete="new-password"
        )
        submitted = st.form_submit_button(submit_label, use_container_width=True)
    return display_name, username, email, password, confirm_password, submitted


def render_initial_admin_setup() -> None:
    """Render one-time administrator creation when the database is empty."""
    _render_branding()
    st.info(
        "Create the initial administrator account. This setup screen is disabled "
        "after the first account is created."
    )
    values = _account_form("initial_admin_setup", "Create administrator")
    display_name, username, email, password, confirm_password, submitted = values
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


def render_signup() -> None:
    """Render public self-service account creation."""
    _render_branding()
    st.write("Create your Catalyst AI account.")
    values = _account_form("signup_form", "Create account")
    display_name, username, email, password, confirm_password, submitted = values
    if submitted:
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
        try:
            register_user(username, email, display_name, password)
        except RegistrationError as exc:
            st.error(str(exc))
            return
        st.session_state["registration_success"] = True
        st.session_state["auth_view"] = "login"
        st.rerun()
    st.divider()
    if st.button("Back to sign in", use_container_width=True):
        st.session_state["auth_view"] = "login"
        st.rerun()


def render_login() -> None:
    """Render username/password authentication with basic attempt throttling."""
    _render_branding()
    st.write("Sign in to access your Catalyst AI projects and product workflows.")
    if st.session_state.get("registration_success"):
        st.success("Account created successfully. Sign in with your new credentials.")
        st.session_state["registration_success"] = False

    remaining_lockout = max(
        0, int(st.session_state["login_locked_until"] - time.monotonic())
    )
    if remaining_lockout:
        st.warning(f"Too many unsuccessful attempts. Try again in {remaining_lockout} seconds.")

    with st.form("login_form", clear_on_submit=False):
        identifier = st.text_input("Username or email", autocomplete="username")
        password = st.text_input(
            "Password", type="password", autocomplete="current-password"
        )
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

    st.divider()
    st.caption("New to Catalyst AI?")
    if st.button("Create an account", use_container_width=True):
        st.session_state["auth_view"] = "signup"
        st.rerun()


def require_authenticated_user():
    """Render the correct entry experience and stop unauthenticated execution."""
    initialize_auth_session()
    user = st.session_state["authenticated_user"]
    if user is not None:
        return user

    if not has_users():
        render_initial_admin_setup()
    elif st.session_state.get("auth_view") == "signup":
        render_signup()
    else:
        render_login()
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
