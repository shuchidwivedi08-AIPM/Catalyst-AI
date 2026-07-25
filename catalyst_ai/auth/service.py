"""Authentication use cases and password security."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import re
import secrets
import sqlite3

from catalyst_ai.auth.database import database_connection, initialize_database
from catalyst_ai.auth.models import User


_PASSWORD_SCHEME = "scrypt"
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,50}$")


class AuthenticationError(ValueError):
    """Raised when credentials cannot be authenticated."""


class BootstrapError(ValueError):
    """Raised when initial administrator creation is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str) -> str:
    """Hash a password using scrypt with a unique random salt."""
    if not password:
        raise ValueError("Password is required.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64
    )
    return f"{_PASSWORD_SCHEME}$16384$8$1${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against a stored scrypt hash."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded_hash.split("$")
        if scheme != _PASSWORD_SCHEME:
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(digest_hex)),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=int(row["id"]),
        username=str(row["username"]),
        email=str(row["email"]),
        display_name=str(row["display_name"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        last_login_at=row["last_login_at"],
    )


def has_users() -> bool:
    """Return whether the identity store already contains an account."""
    initialize_database()
    with database_connection() as connection:
        row = connection.execute("SELECT EXISTS(SELECT 1 FROM users) AS present").fetchone()
        return bool(row["present"])


def bootstrap_initial_admin(
    username: str,
    email: str,
    display_name: str,
    password: str,
) -> User:
    """Create the first account; disabled permanently after bootstrap."""
    initialize_database()
    username = username.strip()
    email = email.strip().lower()
    display_name = display_name.strip()

    if has_users():
        raise BootstrapError("Initial administrator setup has already been completed.")
    if not _USERNAME_PATTERN.fullmatch(username):
        raise BootstrapError(
            "Username must be 3–50 characters and use letters, numbers, dots, dashes, or underscores."
        )
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise BootstrapError("Enter a valid email address.")
    if not display_name:
        raise BootstrapError("Display name is required.")
    if len(password) < 12:
        raise BootstrapError("Password must contain at least 12 characters.")

    now = _utc_now()
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (
                    username, email, password_hash, display_name, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (username, email, hash_password(password), display_name, now, now),
            )
            user_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        raise BootstrapError("That username or email is already in use.") from exc

    return _row_to_user(row)


def authenticate_user(identifier: str, password: str) -> User:
    """Authenticate an active user by username or email."""
    initialize_database()
    normalized_identifier = identifier.strip()
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE
            LIMIT 1
            """,
            (normalized_identifier, normalized_identifier),
        ).fetchone()

        if row is None or row["status"] != "ACTIVE" or not verify_password(
            password, row["password_hash"]
        ):
            raise AuthenticationError("The username or password is incorrect.")

        last_login_at = _utc_now()
        connection.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (last_login_at, last_login_at, row["id"]),
        )
        refreshed = connection.execute(
            "SELECT * FROM users WHERE id = ?", (row["id"],)
        ).fetchone()

    return _row_to_user(refreshed)
