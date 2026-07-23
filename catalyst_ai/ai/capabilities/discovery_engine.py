"""Service for running the AI Discovery Engine over Product Context."""

from typing import Any

from catalyst_ai.ai.openai_client import call_gpt
from catalyst_ai.ai.prompts.discovery_prompt import build_discovery_prompt
from catalyst_ai.ai.response_parser import parse_discovery_result
from catalyst_ai.ai.schemas import DiscoveryResult


def _extract_product_context_text(product_context: dict[str, Any] | str) -> str:
    """Normalize Product Context input to text suitable for discovery prompting."""
    if isinstance(product_context, str):
        return product_context.strip()
    return str(product_context.get("combined_text", "")).strip()


def run_discovery(product_context: dict[str, Any] | str) -> DiscoveryResult:
    """Analyze Product Context and return structured discovery findings."""
    product_context_text = _extract_product_context_text(product_context)
    if not product_context_text:
        raise ValueError("Product Context is empty. Upload and process documents first.")

    final_prompt = build_discovery_prompt(product_context_text)
    raw_response = call_gpt(final_prompt)
    return parse_discovery_result(raw_response)
