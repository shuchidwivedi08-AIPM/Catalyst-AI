"""Technical specification prompt builder."""
import json
from catalyst_ai.ai.prompts.artifact_prompt_common import shared_rules
from catalyst_ai.ai.schemas import ProductUnderstanding, TechnicalSpecification
def build_technical_specification_prompt(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
 return "Generate a Technical Specification as valid JSON only. Use IDs for components, integrations, APIs, security requirements, and decisions. Do not invent technologies, endpoints, vendors, protocols, or deployment platforms; leave unsupported values blank or use open decisions. Distinguish confirmed information from assumptions and include traceability when supported. Concrete expected JSON Schema: "+json.dumps(TechnicalSpecification.model_json_schema(),separators=(",",":"))+"\n\n"+shared_rules(product_understanding,stakeholder,context_source)
