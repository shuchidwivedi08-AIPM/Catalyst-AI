"""Parse and validate structured LLM responses."""

import json

from pydantic import ValidationError

from catalyst_ai.ai.schemas import (
    DiscoveryResult,
    ProductRequirementsDocument,
    ProductUnderstanding,
    TechnicalSpecification,
    UserStoryArtifact,
)


class ProductUnderstandingParseError(ValueError):
    """Raised when a product-understanding response cannot be parsed."""


class DiscoveryParseError(ValueError):
    """Raised when a Discovery Engine response cannot be parsed."""


class ArtifactParseError(ValueError):
    """Raised when an artifact response cannot be parsed or validated."""


def _load_artifact_json(response_text: str) -> object:
    """Load model JSON, accepting harmless whitespace and accidental JSON fences."""
    text = (response_text or "").strip()
    if not text:
        raise ArtifactParseError("The AI returned an empty artifact response. Please retry.")
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            raise ArtifactParseError("The AI artifact response was not valid JSON.")
        text = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ArtifactParseError("The AI artifact response was not valid JSON.") from exc


def _parse_artifact(response_text: str, schema, label: str):
    payload = _load_artifact_json(response_text)
    if not isinstance(payload, dict):
        raise ArtifactParseError(f"The AI response did not match the expected {label} schema.")
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise ArtifactParseError(
            f"The AI response did not match the expected {label} schema."
        ) from exc


def parse_prd_response(response_text: str) -> ProductRequirementsDocument:
    artifact = _parse_artifact(response_text, ProductRequirementsDocument, "PRD")
    if not all((artifact.title.strip(), artifact.executive_summary.strip(), artifact.problem_statement.strip())):
        raise ArtifactParseError("The AI response did not contain the required PRD sections.")
    return artifact


def parse_user_stories_response(response_text: str) -> UserStoryArtifact:
    return _parse_artifact(response_text, UserStoryArtifact, "User Stories")


def parse_technical_specification_response(response_text: str) -> TechnicalSpecification:
    artifact = _parse_artifact(response_text, TechnicalSpecification, "Technical Specification")
    if not all((artifact.title.strip(), artifact.solution_overview.strip(), artifact.architecture_summary.strip())):
        raise ArtifactParseError(
            "The AI response did not contain the required Technical Specification sections."
        )
    return artifact


def parse_product_understanding(raw_response: str) -> ProductUnderstanding:
    """Validate raw JSON and return a ProductUnderstanding object."""
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ProductUnderstandingParseError(
            "The AI response was not valid JSON. Please retry the analysis."
        ) from exc

    try:
        return ProductUnderstanding.model_validate(payload)
    except AttributeError:
        try:
            return ProductUnderstanding.parse_obj(payload)
        except ValidationError as exc:
            raise ProductUnderstandingParseError(
                "The AI response did not match the expected Product Understanding schema."
            ) from exc
    except ValidationError as exc:
        raise ProductUnderstandingParseError(
            "The AI response did not match the expected Product Understanding schema."
        ) from exc


def parse_discovery_result(raw_response: str) -> DiscoveryResult:
    """Validate raw JSON and return a DiscoveryResult object."""
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise DiscoveryParseError(
            "The AI Discovery response was not valid JSON. Please retry discovery."
        ) from exc

    try:
        return DiscoveryResult.model_validate(payload)
    except AttributeError:
        try:
            return DiscoveryResult.parse_obj(payload)
        except ValidationError as exc:
            raise DiscoveryParseError(
                "The AI response did not match the expected Discovery Result schema."
            ) from exc
    except ValidationError as exc:
        raise DiscoveryParseError(
            "The AI response did not match the expected Discovery Result schema."
        ) from exc
