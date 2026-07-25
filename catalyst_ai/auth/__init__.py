"""Authentication and identity services for Catalyst AI."""

from catalyst_ai.auth.models import User
from catalyst_ai.auth.service import (
    AuthenticationError,
    BootstrapError,
    authenticate_user,
    bootstrap_initial_admin,
    has_users,
)

__all__ = [
    "AuthenticationError",
    "BootstrapError",
    "User",
    "authenticate_user",
    "bootstrap_initial_admin",
    "has_users",
]
