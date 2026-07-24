"""User story prompt builder."""
import json
from catalyst_ai.ai.prompts.artifact_prompt_common import shared_rules
from catalyst_ai.ai.schemas import ProductUnderstanding, UserStoryArtifact
def build_user_stories_prompt(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
 return "Generate User Stories as valid JSON only. Use US-001 IDs and structured acceptance criteria (AC-001); use Given/When/Then where appropriate. Each story should use 'As a [persona], I want [need], so that [benefit].' Include Product Understanding traceability when supported, and do not invent unsupported technical details. Concrete expected JSON Schema: "+json.dumps(UserStoryArtifact.model_json_schema(),separators=(",",":"))+"\n\n"+shared_rules(product_understanding,stakeholder,context_source)
