"""Project domain models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: int
    name: str
    description: str
    owner_user_id: int
    created_by_user_id: int
    status: str
    workflow_stage: str
    created_at: str
    updated_at: str
    last_activity_at: str
    user_role: str


@dataclass(frozen=True)
class ProjectMembership:
    project_id: int
    user_id: int
    role: str
    status: str
