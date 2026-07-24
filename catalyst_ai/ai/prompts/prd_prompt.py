"""PRD prompt builder."""
import json
from catalyst_ai.ai.prompts.artifact_prompt_common import shared_rules
from catalyst_ai.ai.schemas import ProductUnderstanding, ProductRequirementsDocument
def build_prd_prompt(product_understanding: ProductUnderstanding, stakeholder: str, context_source: str) -> str:
    schema=json.dumps(ProductRequirementsDocument.model_json_schema(), separators=(",", ":"))
    return """Generate a Product Requirements Document as valid JSON only. Use structured objects, never plain strings. Give requirements FR-001, NFR-001, risks RISK-001, metrics METRIC-001, and questions OQ-001 IDs. Include traceability only where source support exists; never invent source references or exact numeric targets. Leave unknown fields blank and put uncertainty in assumptions or open questions. Concrete expected JSON Schema: """+schema+"\n\n"+shared_rules(product_understanding,stakeholder,context_source)
