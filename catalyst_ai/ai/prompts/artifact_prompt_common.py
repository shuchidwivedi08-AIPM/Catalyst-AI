"""Shared construction helpers for artifact-generation prompts."""

from catalyst_ai.ai.schemas import ProductUnderstanding


def serialize_understanding(product_understanding: ProductUnderstanding) -> str:
    """Serialize using either supported Pydantic API version."""
    try:
        return product_understanding.model_dump_json(indent=2)
    except AttributeError:  # pragma: no cover - Pydantic v1 compatibility
        return product_understanding.json(indent=2)


def shared_rules(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
    return f'''\
Use only the structured AI Product Understanding below as the generation source. Do not
use raw uploaded documents or raw Product Context. Preserve traceability to this source
understanding, do not invent unsupported facts, and put uncertainty in assumptions or
open questions. Return valid JSON only, exactly matching the requested schema; do not
use markdown code fences, conversational text, or statements such as "based on the
information provided." Stakeholder emphasis must not remove required sections.

Stakeholder Perspective: {stakeholder}
Context Source: {context_source}

AI Product Understanding (structured JSON):
{serialize_understanding(product_understanding)}
'''
