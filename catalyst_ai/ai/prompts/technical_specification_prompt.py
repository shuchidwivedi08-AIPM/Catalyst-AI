"""Technical specification prompt builder."""
from catalyst_ai.ai.prompts.artifact_prompt_common import shared_rules
from catalyst_ai.ai.schemas import ProductUnderstanding


def build_technical_specification_prompt(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
    return """Generate a Technical Specification. Required JSON schema fields: title, solution_overview, architecture_summary, architecture_components, integrations, api_requirements, data_requirements, security_requirements, non_functional_requirements, deployment_considerations, observability_requirements, dependencies, technical_risks, assumptions, open_decisions. Do not fabricate APIs, technologies, or deployment platforms.\n\n""" + shared_rules(product_understanding, stakeholder, context_source)
