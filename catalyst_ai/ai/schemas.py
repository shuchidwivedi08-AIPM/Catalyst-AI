"""Schemas for AI-generated product understanding artifacts."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic import model_validator


class ProductUnderstanding(BaseModel):
    """Structured stakeholder-specific product understanding."""

    executive_summary: str = Field(default="", description="Concise product summary.")
    business_problem: str = Field(default="", description="Problem the product addresses.")
    business_goals: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class ArtifactType(str, Enum):
    """Artifact types supported by the MVP artifact-generation flow."""

    PRD = "Product Requirements Document"
    USER_STORIES = "User Stories"
    TECHNICAL_SPECIFICATION = "Technical Specification"


class StrictArtifactModel(BaseModel):
    """Base model that rejects fields outside an artifact's documented schema."""

    model_config = ConfigDict(extra="forbid")


class ArtifactMetadata(StrictArtifactModel):
    """Traceability metadata for an artifact generated from an understanding."""

    artifact_type: ArtifactType
    stakeholder: str
    context_source: str
    product_understanding_source_hash: str


class ProductRequirementsDocument(StrictArtifactModel):
    title: str = ""
    executive_summary: str = ""
    problem_statement: str = ""
    business_objectives: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    personas: list[str] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class UserStory(StrictArtifactModel):
    id: str = ""
    title: str = ""
    persona: str = ""
    need: str = ""
    benefit: str = ""
    story: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    priority: str = "Medium"
    dependencies: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_story_fields(self):
        if not all((self.id.strip(), self.title.strip(), self.persona.strip())):
            raise ValueError("Each user story requires an ID, title, and persona.")
        if not any(item.strip() for item in self.acceptance_criteria):
            raise ValueError("Each user story requires acceptance criteria.")
        return self


class UserStoryArtifact(StrictArtifactModel):
    title: str = ""
    overview: str = ""
    stories: list[UserStory] = Field(default_factory=list)
    cross_cutting_requirements: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_story_ids(self):
        ids = [story.id for story in self.stories]
        if len(ids) != len(set(ids)):
            raise ValueError("User story IDs must be unique.")
        return self


class TechnicalSpecification(StrictArtifactModel):
    title: str = ""
    solution_overview: str = ""
    architecture_summary: str = ""
    architecture_components: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    api_requirements: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    deployment_considerations: list[str] = Field(default_factory=list)
    observability_requirements: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    technical_risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_decisions: list[str] = Field(default_factory=list)


ArtifactContent = ProductRequirementsDocument | UserStoryArtifact | TechnicalSpecification


class GeneratedArtifact(StrictArtifactModel):
    metadata: ArtifactMetadata
    content: ArtifactContent


class DiscoverySummary(BaseModel):
    """Counts of findings identified by the AI Discovery Engine."""

    conflicts: int = 0
    missing_information: int = 0
    assumptions: int = 0
    recommendations: int = 0


class ResolutionStatus(str, Enum):
    """The lifecycle status assigned to an individual discovery finding."""

    UNRESOLVED = "Unresolved"
    RESOLVED = "Resolved"
    DEFERRED = "Deferred"
    NOT_APPLICABLE = "Not Applicable"


class DiscoveryResolution(BaseModel):
    """A user's structured decision or clarification for a discovery finding."""

    finding_id: str
    status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    user_answer: str = ""
    normalized_answer: str = ""
    resolution_note: str = ""


class DiscoveryFinding(BaseModel):
    """A single Discovery Engine finding."""

    id: str = Field(default="", description="Stable finding identifier.")
    title: str = Field(default="", description="Short finding title.")
    description: str = Field(default="", description="Detailed finding description.")
    severity: str = Field(
        default="Medium",
        description="Finding severity: High, Medium, or Low.",
    )
    source_documents: list[str] = Field(
        default_factory=list,
        description="Optional source document names supporting the finding.",
    )
    resolution: DiscoveryResolution | None = None


class DiscoveryResult(BaseModel):
    """Structured findings from the AI Discovery Engine."""

    summary: DiscoverySummary = Field(default_factory=DiscoverySummary)
    conflicts: list[DiscoveryFinding] = Field(default_factory=list)
    missing_information: list[DiscoveryFinding] = Field(default_factory=list)
    assumptions: list[DiscoveryFinding] = Field(default_factory=list)
    recommendations: list[DiscoveryFinding] = Field(default_factory=list)


class ValidatedProductContext(BaseModel):
    """Product Context plus an immutable appendix of explicit user decisions."""

    original_context: str
    discovery_result: DiscoveryResult
    resolved_clarifications: list[DiscoveryResolution]
    validated_context: str
