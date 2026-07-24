"""PRD prompt builder."""
from catalyst_ai.ai.prompts.artifact_prompt_common import shared_rules
from catalyst_ai.ai.schemas import ProductUnderstanding


def build_prd_prompt(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
    return """Generate a Product Requirements Document. Required JSON schema fields: title, executive_summary, problem_statement, business_objectives, target_users, personas, in_scope, out_of_scope, functional_requirements, non_functional_requirements, dependencies, risks, assumptions, success_metrics, open_questions. Emphasize business value, scope, priorities, and metrics for Product Owner; emphasize technical constraints and risks for Technical Lead while retaining a complete PRD.\n\n""" + shared_rules(product_understanding, stakeholder, context_source)
