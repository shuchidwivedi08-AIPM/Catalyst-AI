"""OpenAI client wrapper for Catalyst AI."""

import os

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_OPENAI_MODEL = "gpt-5.5"


class OpenAIConfigurationError(RuntimeError):
    """Raised when OpenAI configuration is missing or invalid."""


def get_openai_model() -> str:
    """Return the configured OpenAI model name."""
    load_dotenv()
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def create_openai_client() -> OpenAI:
    """Create an OpenAI client from environment configuration."""
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise OpenAIConfigurationError(
            "OPENAI_API_KEY is not configured. Add it to your environment or .env file."
        )
    return OpenAI()


def call_gpt(prompt: str) -> str:
    """Call GPT and return the raw text response."""
    client = create_openai_client()
    response = client.chat.completions.create(
        model=get_openai_model(),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""
