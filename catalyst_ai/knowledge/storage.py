"""Private Supabase Storage access for durable knowledge documents."""
from __future__ import annotations

import json
import os
from urllib import error, parse, request

KNOWLEDGE_BUCKET = "catalyst-knowledge"


class KnowledgeStorageError(RuntimeError):
    """Raised when durable object storage cannot complete an operation."""


def _optional_secret(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None
    return str(value).strip() if value else None


def _required_secret(name: str) -> str:
    value = _optional_secret(name)
    if not value:
        raise KnowledgeStorageError(f"{name} is not configured in Streamlit secrets.")
    return value.rstrip("/")


def _backend_api_key() -> str:
    """Return the preferred Supabase backend key.

    New Supabase projects should use ``SUPABASE_SECRET_KEY`` (``sb_secret_...``).
    The legacy service-role JWT remains supported temporarily for existing
    deployments and can be removed once all environments have migrated.
    """
    key = _optional_secret("SUPABASE_SECRET_KEY")
    if key:
        return key

    legacy_key = _optional_secret("SUPABASE_SERVICE_ROLE_KEY")
    if legacy_key:
        return legacy_key

    raise KnowledgeStorageError(
        "SUPABASE_SECRET_KEY is not configured in Streamlit secrets. "
        "A legacy SUPABASE_SERVICE_ROLE_KEY is also accepted during migration."
    )


def _call(method: str, path: str, data: bytes | None = None, content_type: str = "application/json") -> bytes:
    url = f"{_required_secret('SUPABASE_URL')}{path}"
    key = _backend_api_key()
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    if data is not None:
        headers["Content-Type"] = content_type
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=45) as response:
            return response.read()
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise KnowledgeStorageError(f"Supabase Storage request failed ({exc.code}): {details}") from exc
    except error.URLError as exc:
        raise KnowledgeStorageError("Unable to connect to Supabase Storage.") from exc


def ensure_knowledge_bucket() -> None:
    """Create the private bucket when it does not yet exist."""
    payload = json.dumps({"id": KNOWLEDGE_BUCKET, "name": KNOWLEDGE_BUCKET, "public": False}).encode()
    try:
        _call("POST", "/storage/v1/bucket", payload)
    except KnowledgeStorageError as exc:
        if "already exists" not in str(exc).lower() and "duplicate" not in str(exc).lower():
            raise


def upload_object(storage_path: str, content: bytes, content_type: str) -> None:
    ensure_knowledge_bucket()
    encoded_path = parse.quote(storage_path, safe="/")
    _call("POST", f"/storage/v1/object/{KNOWLEDGE_BUCKET}/{encoded_path}", content, content_type)


def download_object(storage_path: str) -> bytes:
    encoded_path = parse.quote(storage_path, safe="/")
    return _call("GET", f"/storage/v1/object/authenticated/{KNOWLEDGE_BUCKET}/{encoded_path}")


def delete_object(storage_path: str) -> None:
    encoded_path = parse.quote(storage_path, safe="/")
    _call("DELETE", f"/storage/v1/object/{KNOWLEDGE_BUCKET}/{encoded_path}")