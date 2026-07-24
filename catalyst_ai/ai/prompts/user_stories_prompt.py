"""User Stories prompt builder."""
from catalyst_ai.ai.prompts.artifact_prompt_common import shared_rules
from catalyst_ai.ai.schemas import ProductUnderstanding


def build_user_stories_prompt(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
    return """Generate User Stories. Required JSON schema fields: title, overview, stories, cross_cutting_requirements, assumptions, open_questions. Every story requires id, title, persona, need, benefit, story, acceptance_criteria, priority, dependencies, notes. Use stable unique IDs; story normally follows 'As a [persona], I want [need], so that [benefit].'; acceptance criteria must be independently testable.\n\n""" + shared_rules(product_understanding, stakeholder, context_source)
