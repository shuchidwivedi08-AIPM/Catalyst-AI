"""Pure source-fingerprint helpers for Product Understanding state."""
import hashlib
import json


def build_product_understanding_source_hash(source_context_text: str, stakeholder: str, context_source: str) -> str:
    payload = {"context": source_context_text, "stakeholder": stakeholder, "context_source": context_source}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def is_product_understanding_stale(stored_hash: str | None, source_context_text: str, stakeholder: str, context_source: str) -> bool:
    return not stored_hash or stored_hash != build_product_understanding_source_hash(source_context_text, stakeholder, context_source)
