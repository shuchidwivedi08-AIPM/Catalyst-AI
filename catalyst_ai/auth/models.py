"""Authentication domain models."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    """Authenticated Catalyst AI user."""

    id: int
    username: str
    email: str
    display_name: str
    status: str
    created_at: str
    last_login_at: str | None = None
