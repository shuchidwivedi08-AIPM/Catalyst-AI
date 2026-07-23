"""Parse and validate structured LLM responses."""

import json

from pydantic import ValidationError

from catalyst_ai.ai.schemas import ProductUnderstanding


class ProductUnderstandingParseError(ValueError):
    """Raised when a product-understanding response cannot be parsed."""


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
