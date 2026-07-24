"""Schemas for AI-generated product understanding and delivery artifacts."""
from enum import Enum
from typing import ClassVar
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ProductUnderstanding(BaseModel):
    executive_summary: str = Field(default="", description="Concise product summary.")
    business_problem: str = Field(default="", description="Problem the product addresses.")
    business_goals: list[str] = Field(default_factory=list); functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list); risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list); open_questions: list[str] = Field(default_factory=list); recommendations: list[str] = Field(default_factory=list)

class ArtifactType(str, Enum): PRD="Product Requirements Document"; USER_STORIES="User Stories"; TECHNICAL_SPECIFICATION="Technical Specification"
class StrictArtifactModel(BaseModel): model_config=ConfigDict(extra="forbid")
class ArtifactMetadata(StrictArtifactModel):
    artifact_type: ArtifactType; stakeholder: str; context_source: str; product_understanding_source_hash: str

class TraceabilityReference(StrictArtifactModel):
    source_type: str = Field(default="Product Understanding", description="Type of source, such as Product Understanding, Requirement, Risk, or Assumption.")
    reference: str = Field(default="", description="Readable source reference or source path.")

class StructuredArtifactItem(StrictArtifactModel):
    """Common safe coercion shared by all generated child models."""
    string_field: ClassVar[str] = "description"
    @model_validator(mode="before")
    @classmethod
    def coerce_string_and_traceability(cls, value):
        if isinstance(value, str): return {cls.string_field: value}
        if not isinstance(value, dict): return value
        value=dict(value); trace=value.get("traceability")
        if isinstance(trace, str): value["traceability"]=[{"reference": trace}]
        elif isinstance(trace, list): value["traceability"]=[{"reference": x} if isinstance(x,str) else x for x in trace]
        return value

class BusinessObjective(StructuredArtifactItem):
    string_field: ClassVar[str]="objective"; id:str=""; objective:str=""; rationale:str=""; priority:str="Medium"; success_indicator:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class TargetUser(StructuredArtifactItem):
    string_field: ClassVar[str]="description"; user_group:str=""; description:str=""; needs:list[str]=Field(default_factory=list); pain_points:list[str]=Field(default_factory=list); traceability:list[TraceabilityReference]=Field(default_factory=list)
class Persona(StructuredArtifactItem):
    string_field: ClassVar[str]="description"; name:str=""; role:str=""; description:str=""; goals:list[str]=Field(default_factory=list); pain_points:list[str]=Field(default_factory=list); behaviors:list[str]=Field(default_factory=list); traceability:list[TraceabilityReference]=Field(default_factory=list)
class ScopeItem(StructuredArtifactItem):
    string_field: ClassVar[str]="item"; id:str=""; item:str=""; description:str=""; rationale:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class FunctionalRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="description"; id:str=""; name:str=""; description:str=""; priority:str="Medium"; rationale:str=""; acceptance_criteria:list[str]=Field(default_factory=list); dependencies:list[str]=Field(default_factory=list); traceability:list[TraceabilityReference]=Field(default_factory=list)
class NonFunctionalRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="requirement"; id:str=""; category:str=""; requirement:str=""; measurable_target:str=""; priority:str="Medium"; rationale:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class ArtifactDependency(StructuredArtifactItem):
    string_field: ClassVar[str]="dependency"; id:str=""; dependency:str=""; dependency_type:str=""; impact:str=""; owner:str=""; status:str="Unconfirmed"; traceability:list[TraceabilityReference]=Field(default_factory=list)
class ArtifactRisk(StructuredArtifactItem):
    string_field: ClassVar[str]="risk"; id:str=""; risk:str=""; impact:str=""; likelihood:str="Medium"; severity:str="Medium"; mitigation:str=""; owner:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class ArtifactAssumption(StructuredArtifactItem):
    string_field: ClassVar[str]="assumption"; id:str=""; assumption:str=""; validation_needed:bool=True; validation_method:str=""; impact_if_false:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class SuccessMetric(StructuredArtifactItem):
    string_field: ClassVar[str]="metric"; id:str=""; metric:str=""; target:str=""; measurement_method:str=""; reporting_frequency:str=""; owner:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class ArtifactOpenQuestion(StructuredArtifactItem):
    string_field: ClassVar[str]="question"; id:str=""; question:str=""; owner:str=""; priority:str="Medium"; impact:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)

class ProductRequirementsDocument(StrictArtifactModel):
    title:str=""; document_version:str="1.0"; executive_summary:str=""; problem_statement:str=""
    business_objectives:list[BusinessObjective]=Field(default_factory=list); target_users:list[TargetUser]=Field(default_factory=list); personas:list[Persona]=Field(default_factory=list); in_scope:list[ScopeItem]=Field(default_factory=list); out_of_scope:list[ScopeItem]=Field(default_factory=list); functional_requirements:list[FunctionalRequirement]=Field(default_factory=list); non_functional_requirements:list[NonFunctionalRequirement]=Field(default_factory=list); dependencies:list[ArtifactDependency]=Field(default_factory=list); risks:list[ArtifactRisk]=Field(default_factory=list); assumptions:list[ArtifactAssumption]=Field(default_factory=list); success_metrics:list[SuccessMetric]=Field(default_factory=list); open_questions:list[ArtifactOpenQuestion]=Field(default_factory=list)

class AcceptanceCriterion(StructuredArtifactItem):
    string_field: ClassVar[str]="criterion"; id:str=""; scenario:str=""; given:str=""; when:str=""; then:str=""; criterion:str=""
class UserStory(StructuredArtifactItem):
    string_field: ClassVar[str]="story"; id:str=""; title:str=""; persona:str=""; need:str=""; benefit:str=""; story:str=""; priority:str="Medium"; status:str="Draft"; acceptance_criteria:list[AcceptanceCriterion]=Field(default_factory=list); dependencies:list[ArtifactDependency]=Field(default_factory=list); risks:list[ArtifactRisk]=Field(default_factory=list); assumptions:list[ArtifactAssumption]=Field(default_factory=list); business_value:str=""; estimation_notes:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
    @model_validator(mode="after")
    def nonempty_story(self):
        if not any((self.id.strip(),self.title.strip(),self.persona.strip(),self.story.strip())): raise ValueError("Each user story requires meaningful content.")
        return self
class CrossCuttingRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="requirement"; id:str=""; category:str=""; requirement:str=""; affected_story_ids:list[str]=Field(default_factory=list); traceability:list[TraceabilityReference]=Field(default_factory=list)
class UserStoryArtifact(StrictArtifactModel):
    title:str=""; overview:str=""; stories:list[UserStory]=Field(default_factory=list); cross_cutting_requirements:list[CrossCuttingRequirement]=Field(default_factory=list); assumptions:list[ArtifactAssumption]=Field(default_factory=list); open_questions:list[ArtifactOpenQuestion]=Field(default_factory=list)

class ArchitectureComponent(StructuredArtifactItem):
    string_field: ClassVar[str]="responsibility"; id:str=""; name:str=""; responsibility:str=""; interfaces:list[str]=Field(default_factory=list); dependencies:list[str]=Field(default_factory=list); technology_assumption:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class IntegrationSpecification(StructuredArtifactItem):
    string_field: ClassVar[str]="purpose"; id:str=""; system_name:str=""; purpose:str=""; direction:str=""; protocol_or_method:str=""; data_exchanged:list[str]=Field(default_factory=list); authentication:str=""; failure_handling:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class ApiRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="purpose"; id:str=""; name:str=""; purpose:str=""; method:str=""; endpoint:str=""; request_summary:str=""; response_summary:str=""; authentication:str=""; error_handling:list[str]=Field(default_factory=list); traceability:list[TraceabilityReference]=Field(default_factory=list)
class DataRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="description"; id:str=""; data_entity:str=""; description:str=""; key_fields:list[str]=Field(default_factory=list); source:str=""; retention:str=""; privacy_classification:str=""; validation_rules:list[str]=Field(default_factory=list); traceability:list[TraceabilityReference]=Field(default_factory=list)
class SecurityRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="requirement"; id:str=""; category:str=""; requirement:str=""; control:str=""; verification_method:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class DeploymentConsideration(StructuredArtifactItem):
    string_field: ClassVar[str]="consideration"; id:str=""; area:str=""; consideration:str=""; recommendation:str=""; dependency:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class ObservabilityRequirement(StructuredArtifactItem):
    string_field: ClassVar[str]="metric_or_event"; id:str=""; category:str=""; signal:str=""; metric_or_event:str=""; alert_condition:str=""; dashboard_requirement:str=""; traceability:list[TraceabilityReference]=Field(default_factory=list)
class OpenTechnicalDecision(StructuredArtifactItem):
    string_field: ClassVar[str]="decision"; id:str=""; decision:str=""; options:list[str]=Field(default_factory=list); evaluation_criteria:list[str]=Field(default_factory=list); owner:str=""; priority:str="Medium"; traceability:list[TraceabilityReference]=Field(default_factory=list)
class TechnicalSpecification(StrictArtifactModel):
    title:str=""; document_version:str="1.0"; solution_overview:str=""; architecture_summary:str=""; architecture_components:list[ArchitectureComponent]=Field(default_factory=list); integrations:list[IntegrationSpecification]=Field(default_factory=list); api_requirements:list[ApiRequirement]=Field(default_factory=list); data_requirements:list[DataRequirement]=Field(default_factory=list); security_requirements:list[SecurityRequirement]=Field(default_factory=list); non_functional_requirements:list[NonFunctionalRequirement]=Field(default_factory=list); deployment_considerations:list[DeploymentConsideration]=Field(default_factory=list); observability_requirements:list[ObservabilityRequirement]=Field(default_factory=list); dependencies:list[ArtifactDependency]=Field(default_factory=list); technical_risks:list[ArtifactRisk]=Field(default_factory=list); assumptions:list[ArtifactAssumption]=Field(default_factory=list); open_decisions:list[OpenTechnicalDecision]=Field(default_factory=list)
ArtifactContent=ProductRequirementsDocument|UserStoryArtifact|TechnicalSpecification
class GeneratedArtifact(StrictArtifactModel): metadata:ArtifactMetadata; content:ArtifactContent
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
