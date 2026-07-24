"""Deterministic, non-AI cleanup for generated delivery artifacts."""

from pydantic import BaseModel

from catalyst_ai.ai.schemas import GeneratedArtifact


# A prefix only identifies the kind of *field* being normalized.  Every list
# still needs to be checked for models that declare an ``id`` field before an
# identifier can be assigned (for example, PRD acceptance criteria are strings
# while user-story acceptance criteria are structured models).
ID_PREFIXES = {
    "business_objectives": "BO-",
    "in_scope": "SCOPE-",
    "out_of_scope": "OOS-",
    "functional_requirements": "FR-",
    "non_functional_requirements": "NFR-",
    "dependencies": "DEP-",
    "risks": "RISK-",
    "technical_risks": "RISK-",
    "assumptions": "ASM-",
    "success_metrics": "METRIC-",
    "open_questions": "OQ-",
    "stories": "US-",
    "acceptance_criteria": "AC-",
    "cross_cutting_requirements": "CCR-",
    "architecture_components": "COMP-",
    "integrations": "INT-",
    "api_requirements": "API-",
    "data_requirements": "DATA-",
    "security_requirements": "SEC-",
    "deployment_considerations": "DEPLOY-",
    "observability_requirements": "OBS-",
    "open_decisions": "DEC-",
}

NORMALIZED_LEVELS = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def supports_id(item: object) -> bool:
    """Return whether a Pydantic model explicitly declares an ID field."""
    return isinstance(item, BaseModel) and "id" in item.__class__.model_fields


def normalize_ids(items: list[object], prefix: str) -> None:
    """Normalize blank or duplicate IDs without changing non-model list items."""
    eligible_items = [item for item in items if supports_id(item)]

    if not eligible_items:
        return

    used_ids: set[str] = set()

    for index, item in enumerate(eligible_items, start=1):
        current_id = str(item.id or "").strip()

        if current_id and current_id not in used_ids:
            item.id = current_id
            used_ids.add(current_id)
            continue

        candidate_index = index
        candidate = f"{prefix}{candidate_index:03d}"

        while candidate in used_ids:
            candidate_index += 1
            candidate = f"{prefix}{candidate_index:03d}"

        item.id = candidate
        used_ids.add(candidate)


def normalize_string_list(items: list[object]) -> None:
    """Trim strings in place while retaining ordering and empty entries."""
    for index, item in enumerate(items):
        if isinstance(item, str):
            items[index] = item.strip()


def normalize_value(value: object) -> None:
    """Recursively normalize nested models, lists, and dictionaries safely."""
    if value is None:
        return

    if isinstance(value, BaseModel):
        normalize_model(value)
        return

    if isinstance(value, list):
        normalize_string_list(value)
        for item in value:
            if isinstance(item, (BaseModel, list, dict)):
                normalize_value(item)
        return

    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str):
                value[key] = item.strip()
            elif isinstance(item, (BaseModel, list, dict)):
                normalize_value(item)


def normalize_model(model: BaseModel) -> None:
    """Normalize a Pydantic artifact model without assuming list item types."""
    for field_name in model.__class__.model_fields:
        value = getattr(model, field_name, None)

        if isinstance(value, str):
            cleaned_value = value.strip()
            if field_name in {"priority", "severity", "likelihood"}:
                cleaned_value = NORMALIZED_LEVELS.get(
                    cleaned_value.lower(), cleaned_value
                )
            setattr(model, field_name, cleaned_value)
            continue

        if isinstance(value, list):
            normalize_string_list(value)

            prefix = ID_PREFIXES.get(field_name)
            if prefix:
                normalize_ids(value, prefix)

            for item in value:
                if isinstance(item, (BaseModel, list, dict)):
                    normalize_value(item)
            continue

        if isinstance(value, (BaseModel, dict)):
            normalize_value(value)


def normalize_generated_artifact(artifact: GeneratedArtifact) -> GeneratedArtifact:
    """Normalize IDs, whitespace, and display casing without adding facts."""
    normalize_model(artifact.content)
    return artifact
