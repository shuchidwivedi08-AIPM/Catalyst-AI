import json
import pytest
from catalyst_ai.ai.capabilities.artifact_normalization import normalize_generated_artifact
from catalyst_ai.ai.response_parser import parse_prd_response
from catalyst_ai.ai.schemas import (
    AcceptanceCriterion,
    ArtifactMetadata,
    ArtifactType,
    FunctionalRequirement,
    GeneratedArtifact,
    ProductRequirementsDocument,
    TargetUser,
    TraceabilityReference,
    UserStory,
    UserStoryArtifact,
)

def test_prd_accepts_structured_content_and_traceability_variants():
    raw_response = json.dumps({"title":"P","executive_summary":"S","problem_statement":"Problem","business_objectives":[{"objective":"Adoption","traceability":"functional_requirements[1]"}],"functional_requirements":[{"id":"FR-001","description":"Sign in","acceptance_criteria":[" User can sign in. "],"dependencies":[" DEP-001 "],"traceability":["business_goals[0]", {"source_type":"Requirement","reference":"BO-001"}]}],"risks":["Vendor outage"]})
    prd = parse_prd_response(raw_response)
    artifact = GeneratedArtifact(
        metadata=ArtifactMetadata(artifact_type=ArtifactType.PRD, stakeholder="Owner", context_source="Context", product_understanding_source_hash="hash"),
        content=prd,
    )
    normalized = normalize_generated_artifact(artifact)

    assert prd.business_objectives[0].traceability[0].reference == "functional_requirements[1]"
    assert prd.functional_requirements[0].traceability[1].source_type == "Requirement"
    assert prd.risks[0].risk == "Vendor outage"
    assert normalized.content.functional_requirements[0].acceptance_criteria == ["User can sign in."]
    assert normalized.content.functional_requirements[0].dependencies == ["DEP-001"]

def test_strings_are_safe_but_invalid_scalars_are_not_coerced():
    with pytest.raises(Exception):
        ProductRequirementsDocument(functional_requirements=[42])

def test_normalization_generates_ids_and_normalizes_duplicate_values():
    artifact = GeneratedArtifact(metadata=ArtifactMetadata(artifact_type=ArtifactType.PRD, stakeholder="Owner", context_source="Context", product_understanding_source_hash="hash"), content=ProductRequirementsDocument(functional_requirements=[{"id":" FR-001 ","description":" first ","priority":"high"},{"id":"FR-001","description":"second"}]))
    normalized=normalize_generated_artifact(artifact)
    requirements=normalized.content.functional_requirements
    assert [item.id for item in requirements] == ["FR-001", "FR-002"]
    assert requirements[0].description == "first" and requirements[0].priority == "High"


def test_normalization_preserves_and_trims_string_lists():
    requirement = FunctionalRequirement(
        id="FR-001",
        acceptance_criteria=[" User can log in. ", " Invalid credentials are rejected. "],
        dependencies=[" DEP-001 "],
    )
    target_user = TargetUser(
        needs=[" Need one ", " Need two "],
        pain_points=[" Pain one "],
    )
    artifact = GeneratedArtifact(
        metadata=ArtifactMetadata(artifact_type=ArtifactType.PRD, stakeholder="Owner", context_source="Context", product_understanding_source_hash="hash"),
        content=ProductRequirementsDocument(functional_requirements=[requirement], target_users=[target_user]),
    )

    normalized = normalize_generated_artifact(artifact)

    requirement = normalized.content.functional_requirements[0]
    assert requirement.acceptance_criteria == ["User can log in.", "Invalid credentials are rejected."]
    assert requirement.dependencies == ["DEP-001"]
    assert all(isinstance(item, str) for item in requirement.acceptance_criteria)
    assert normalized.content.target_users[0].needs == ["Need one", "Need two"]
    assert normalized.content.target_users[0].pain_points == ["Pain one"]


def test_normalization_generates_nested_ids_and_skips_traceability_ids():
    traceability = TraceabilityReference(
        source_type=" Product Understanding ", reference=" functional_requirements[0] "
    )
    artifact = GeneratedArtifact(
        metadata=ArtifactMetadata(artifact_type=ArtifactType.PRD, stakeholder="Owner", context_source="Context", product_understanding_source_hash="hash"),
        content=ProductRequirementsDocument(
            business_objectives=[{"objective": "Objective"}],
            functional_requirements=[{"description": "First"}, {"description": "Second"}],
            risks=[{"risk": "Risk"}],
            open_questions=[{"question": "Question", "traceability": [traceability]}],
        ),
    )

    normalized = normalize_generated_artifact(artifact)
    content = normalized.content

    assert [item.id for item in content.business_objectives] == ["BO-001"]
    assert [item.id for item in content.functional_requirements] == ["FR-001", "FR-002"]
    assert [item.id for item in content.risks] == ["RISK-001"]
    assert [item.id for item in content.open_questions] == ["OQ-001"]
    assert content.open_questions[0].traceability[0].source_type == "Product Understanding"
    assert content.open_questions[0].traceability[0].reference == "functional_requirements[0]"
    assert "id" not in content.open_questions[0].traceability[0].__class__.model_fields


def test_acceptance_criteria_models_receive_ids_while_prd_strings_remain_strings():
    artifact = GeneratedArtifact(
        metadata=ArtifactMetadata(artifact_type=ArtifactType.USER_STORIES, stakeholder="Owner", context_source="Context", product_understanding_source_hash="hash"),
        content=UserStoryArtifact(
            stories=[UserStory(title="Story", acceptance_criteria=[AcceptanceCriterion(criterion=" Criterion ")])]
        ),
    )

    normalized = normalize_generated_artifact(artifact)

    criterion = normalized.content.stories[0].acceptance_criteria[0]
    assert criterion.id == "AC-001"
    assert criterion.criterion == "Criterion"
