"""Service for generating stakeholder-specific AI Product Understanding."""

from typing import Any

from catalyst_ai.ai.openai_client import call_gpt
from catalyst_ai.ai.prompts.product_understanding_prompt import PROMPTS_BY_STAKEHOLDER
from catalyst_ai.ai.response_parser import parse_product_understanding
from catalyst_ai.ai.schemas import ProductUnderstanding


class UnsupportedStakeholderError(ValueError):
    """Raised when no prompt exists for a selected stakeholder."""


def _extract_product_context_text(product_context: dict[str, Any] | str) -> str:
    """Normalize Product Context input to text suitable for prompting."""
    if isinstance(product_context, str):
        return product_context.strip()
    return str(product_context.get("combined_text", "")).strip()


def build_final_prompt(product_context: dict[str, Any] | str, stakeholder: str) -> str:
    """Build the stakeholder-specific prompt from Product Context."""
    prompt_template = PROMPTS_BY_STAKEHOLDER.get(stakeholder)
    if prompt_template is None:
        raise UnsupportedStakeholderError(f"Unsupported stakeholder: {stakeholder}")

    product_context_text = _extract_product_context_text(product_context)
    if not product_context_text:
        raise ValueError("Product Context is empty. Upload and process documents first.")

    return (
        prompt_template.replace("{stakeholder}", stakeholder)
        .replace("{product_context}", product_context_text)
    )


def generate_product_understanding(
    product_context: dict[str, Any] | str,
    stakeholder: str,
) -> ProductUnderstanding:
    """Generate structured Product Understanding for the selected stakeholder."""
    final_prompt = build_final_prompt(product_context, stakeholder)
    raw_response = call_gpt(final_prompt)
    return parse_product_understanding(raw_response)
