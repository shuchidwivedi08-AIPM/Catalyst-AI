"""Unit tests for deterministic Discovery Resolution business logic."""

import pytest
from pydantic import ValidationError

from catalyst_ai.ai.capabilities.discovery_resolution import (
    build_validated_product_context,
    save_resolution,
)
from catalyst_ai.ai.schemas import (
    DiscoveryFinding,
    DiscoveryResolution,
    DiscoveryResult,
    ResolutionStatus,
)


def finding(finding_id="C001"):
    return DiscoveryFinding(
        id=finding_id,
        title="Conflicting Identity Provider",
        description="Azure AD and Okta are both named.",
    )


def result():
    return DiscoveryResult(
        conflicts=[finding()],
        missing_information=[DiscoveryFinding(id="M001", title="Retention period")],
        assumptions=[DiscoveryFinding(id="A001", title="Availability assumption")],
        recommendations=[DiscoveryFinding(id="R001", title="Schedule a workshop")],
    )


def test_existing_discovery_json_without_resolution_parses():
    parsed = DiscoveryResult.model_validate({"conflicts": [finding().model_dump()]})
    assert parsed.conflicts[0].resolution is None


def test_valid_resolution_parses_and_invalid_status_fails():
    resolution = DiscoveryResolution.model_validate(
        {"finding_id": "C001", "status": "Resolved", "user_answer": "Azure AD"}
    )
    assert resolution.status is ResolutionStatus.RESOLVED
    with pytest.raises(ValidationError):
        DiscoveryResolution.model_validate({"finding_id": "C001", "status": "Invalid"})


def test_resolved_conflict_requires_and_trims_answer():
    resolution = save_resolution(finding(), ResolutionStatus.RESOLVED, "  Azure AD  ")
    assert resolution.user_answer == "Azure AD"
    assert resolution.normalized_answer == "Azure AD"
    with pytest.raises(ValueError, match="Please provide a clarification"):
        save_resolution(finding(), ResolutionStatus.RESOLVED, "   ")


def test_deferred_finding_allows_blank_answer():
    resolution = save_resolution(finding(), ResolutionStatus.DEFERRED, "")
    assert resolution.user_answer == ""


def test_validated_context_preserves_original_and_appends_decisions():
    original = "Original context\nwith exact content."
    resolutions = {
        "C001": save_resolution(finding(), ResolutionStatus.RESOLVED, "Azure AD"),
        "M001": DiscoveryResolution(finding_id="M001", status=ResolutionStatus.DEFERRED),
        "A001": DiscoveryResolution(
            finding_id="A001", status=ResolutionStatus.NOT_APPLICABLE
        ),
        "R001": DiscoveryResolution(finding_id="R001", status=ResolutionStatus.UNRESOLVED),
    }
    validated = build_validated_product_context(original, result(), resolutions)
    assert validated.original_context == original
    assert validated.validated_context.startswith(original)
    assert "Finding ID: C001" in validated.validated_context
    assert "User Clarification: Azure AD" in validated.validated_context
    assert "Resolution Status: Deferred" in validated.validated_context
    assert "Resolution Status: Not Applicable" in validated.validated_context
    assert "Finding ID: R001" not in validated.validated_context
    assert [item.finding_id for item in validated.resolved_clarifications] == [
        "C001", "M001", "A001"
    ]


def test_multiple_resolution_ids_remain_stable():
    resolutions = {
        "C001": save_resolution(finding("C001"), ResolutionStatus.RESOLVED, "Azure AD"),
        "M001": DiscoveryResolution(finding_id="M001", status=ResolutionStatus.DEFERRED),
    }
    validated = build_validated_product_context("Source", result(), resolutions)
    assert [item.finding_id for item in validated.resolved_clarifications] == ["C001", "M001"]
