"""Orchestrate typed artifact generation from AI Product Understanding only."""
from collections.abc import Callable

from catalyst_ai.ai.openai_client import call_gpt
from catalyst_ai.ai.capabilities.artifact_normalization import normalize_generated_artifact
from catalyst_ai.ai.prompts.prd_prompt import build_prd_prompt
from catalyst_ai.ai.prompts.user_stories_prompt import build_user_stories_prompt
from catalyst_ai.ai.prompts.technical_specification_prompt import build_technical_specification_prompt
from catalyst_ai.ai.response_parser import parse_prd_response, parse_technical_specification_response, parse_user_stories_response
from catalyst_ai.ai.schemas import ArtifactMetadata, ArtifactType, GeneratedArtifact, ProductUnderstanding


def generate_artifact(
    product_understanding: ProductUnderstanding,
    artifact_type: ArtifactType,
    stakeholder: str,
    context_source: str,
    product_understanding_source_hash: str,
    on_raw_response: Callable[[str], None] | None = None,
    on_before_parse: Callable[[], None] | None = None,
) -> GeneratedArtifact:
    """Generate a schema-validated artifact and attach immutable source metadata."""
    if not isinstance(product_understanding, ProductUnderstanding):
        raise ValueError("Generate AI Product Understanding before creating an artifact.")
    if not stakeholder.strip() or not context_source.strip() or not product_understanding_source_hash.strip():
        raise ValueError("Product Understanding traceability metadata is missing. Regenerate it.")
    try:
        artifact_type = ArtifactType(artifact_type)
    except (TypeError, ValueError) as exc:
        raise ValueError("Unsupported artifact type.") from exc
    generators = {
        ArtifactType.PRD: (build_prd_prompt, parse_prd_response),
        ArtifactType.USER_STORIES: (build_user_stories_prompt, parse_user_stories_response),
        ArtifactType.TECHNICAL_SPECIFICATION: (build_technical_specification_prompt, parse_technical_specification_response),
    }
    prompt_builder, parser = generators[artifact_type]
    raw_response = call_gpt(prompt_builder(product_understanding, stakeholder, context_source))
    if on_raw_response:
        on_raw_response(raw_response)
    if on_before_parse:
        on_before_parse()
    content = parser(raw_response)
    return normalize_generated_artifact(GeneratedArtifact(metadata=ArtifactMetadata(artifact_type=artifact_type, stakeholder=stakeholder, context_source=context_source, product_understanding_source_hash=product_understanding_source_hash), content=content))
