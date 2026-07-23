"""Backward-compatible service exports for AI Product Understanding."""

from catalyst_ai.ai.capabilities.product_understanding import (  # noqa: F401
    UnsupportedStakeholderError,
    build_final_prompt,
    generate_product_understanding,
)
