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
