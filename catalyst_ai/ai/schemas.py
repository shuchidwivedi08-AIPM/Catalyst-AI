"""Schemas for AI-generated product understanding artifacts."""

from pydantic import BaseModel, Field


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


class DiscoverySummary(BaseModel):
    """Counts of findings identified by the AI Discovery Engine."""

    conflicts: int = 0
    missing_information: int = 0
    assumptions: int = 0
    recommendations: int = 0


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


class DiscoveryResult(BaseModel):
    """Structured findings from the AI Discovery Engine."""

    summary: DiscoverySummary = Field(default_factory=DiscoverySummary)
    conflicts: list[DiscoveryFinding] = Field(default_factory=list)
    missing_information: list[DiscoveryFinding] = Field(default_factory=list)
    assumptions: list[DiscoveryFinding] = Field(default_factory=list)
    recommendations: list[DiscoveryFinding] = Field(default_factory=list)
