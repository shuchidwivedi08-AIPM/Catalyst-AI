import json
import pytest
from catalyst_ai.ai.capabilities.artifact_normalization import normalize_generated_artifact
from catalyst_ai.ai.response_parser import parse_prd_response
from catalyst_ai.ai.schemas import ArtifactMetadata, ArtifactType, GeneratedArtifact, ProductRequirementsDocument

def test_prd_accepts_structured_content_and_traceability_variants():
    prd = parse_prd_response(json.dumps({"title":"P","executive_summary":"S","problem_statement":"Problem","business_objectives":[{"objective":"Adoption","traceability":"functional_requirements[1]"}],"functional_requirements":[{"id":"FR-001","description":"Sign in","traceability":["business_goals[0]", {"source_type":"Requirement","reference":"BO-001"}]}],"risks":["Vendor outage"]}))
    assert prd.business_objectives[0].traceability[0].reference == "functional_requirements[1]"
    assert prd.functional_requirements[0].traceability[1].source_type == "Requirement"
    assert prd.risks[0].risk == "Vendor outage"

def test_strings_are_safe_but_invalid_scalars_are_not_coerced():
    with pytest.raises(Exception):
        ProductRequirementsDocument(functional_requirements=[42])

def test_normalization_generates_ids_and_normalizes_duplicate_values():
    artifact = GeneratedArtifact(metadata=ArtifactMetadata(artifact_type=ArtifactType.PRD, stakeholder="Owner", context_source="Context", product_understanding_source_hash="hash"), content=ProductRequirementsDocument(functional_requirements=[{"id":" FR-001 ","description":" first ","priority":"high"},{"id":"FR-001","description":"second"}]))
    normalized=normalize_generated_artifact(artifact)
    requirements=normalized.content.functional_requirements
    assert [item.id for item in requirements] == ["FR-001", "FR-002"]
    assert requirements[0].description == "first" and requirements[0].priority == "High"
