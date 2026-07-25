"""SQLite persistence for Catalyst AI identity and project data."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Iterator


DEFAULT_DATABASE_PATH = Path("data/catalyst_ai.db")


def get_database_path() -> Path:
    """Return the configured SQLite database path."""
    configured_path = os.getenv("CATALYST_DATABASE_PATH")
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


@contextmanager
def database_connection(database_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a transaction-aware SQLite connection."""
    path = database_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path: Path | None = None) -> None:
    """Create identity and project tables when they do not exist."""
    with database_connection(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'INACTIVE', 'LOCKED')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                owner_user_id INTEGER NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'ON_HOLD', 'COMPLETED', 'ARCHIVED')),
                workflow_stage TEXT NOT NULL DEFAULT 'DOCUMENT_UPLOAD',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                archived_at TEXT,
                FOREIGN KEY (owner_user_id) REFERENCES users(id),
                FOREIGN KEY (created_by_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS project_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('OWNER', 'ADMIN', 'EDITOR', 'REVIEWER')),
                status TEXT NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REMOVED')),
                added_by_user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (project_id, user_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (added_by_user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id);
            CREATE INDEX IF NOT EXISTS idx_project_memberships_user
                ON project_memberships(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_project_memberships_project
                ON project_memberships(project_id, status);
            """
        )