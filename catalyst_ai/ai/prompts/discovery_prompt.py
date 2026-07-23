"""Prompt template for the AI Discovery Engine capability."""

DISCOVERY_EXPECTED_JSON_SCHEMA = """
{
  "summary": {
    "conflicts": 0,
    "missing_information": 0,
    "assumptions": 0,
    "recommendations": 0
  },
  "conflicts": [
    {
      "id": "C001",
      "title": "string",
      "description": "string",
      "severity": "High|Medium|Low",
      "source_documents": ["string"]
    }
  ],
  "missing_information": [
    {
      "id": "M001",
      "title": "string",
      "description": "string",
      "severity": "High|Medium|Low",
      "source_documents": ["string"]
    }
  ],
  "assumptions": [
    {
      "id": "A001",
      "title": "string",
      "description": "string",
      "severity": "High|Medium|Low",
      "source_documents": ["string"]
    }
  ],
  "recommendations": [
    {
      "id": "R001",
      "title": "string",
      "description": "string",
      "severity": "High|Medium|Low",
      "source_documents": ["string"]
    }
  ]
}
""".strip()

DISCOVERY_PROMPT = f"""
SYSTEM
You are an experienced Product Owner conducting enterprise product discovery.
Your responsibility is to analyze the provided Product Context before Product
Understanding is generated.

Guardrails:
- Never generate requirements.
- Never generate PRDs.
- Never generate User Stories.
- Never assume missing facts.
- Do not modify or rewrite the Product Context.
- Do not generate project artifacts.
- Identify contradictory information across documents as conflicts.
- Identify information required before implementation as missing_information.
- Identify information inferred by the documents but not explicitly stated as assumptions.
- Provide recommendations that improve discovery quality.
- Return only valid JSON matching this schema:
{DISCOVERY_EXPECTED_JSON_SCHEMA}

USER
Product Context:
{{product_context}}

Instructions:
Classify every finding into exactly one of conflicts, missing_information,
assumptions, or recommendations. Use stable ids with prefixes C, M, A, and R.
Set summary counts to match the number of findings in each category. Include
source_documents when document names are available in the Product Context.
""".strip()


def build_discovery_prompt(product_context: str) -> str:
    """Build the Discovery Engine prompt from Product Context text."""
    return DISCOVERY_PROMPT.replace("{product_context}", product_context)
