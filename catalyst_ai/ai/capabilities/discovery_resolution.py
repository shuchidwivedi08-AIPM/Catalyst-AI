"""Deterministic services for resolving Discovery Engine findings."""

from catalyst_ai.ai.schemas import (
    DiscoveryFinding,
    DiscoveryResolution,
    DiscoveryResult,
    ResolutionStatus,
    ValidatedProductContext,
)


INCLUDED_STATUSES = {
    ResolutionStatus.RESOLVED,
    ResolutionStatus.DEFERRED,
    ResolutionStatus.NOT_APPLICABLE,
}


def save_resolution(
    finding: DiscoveryFinding,
    status: ResolutionStatus,
    user_answer: str,
) -> DiscoveryResolution:
    """Validate and save a deterministic resolution without calling an AI service."""
    finding_id = finding.id.strip()
    if not finding_id:
        raise ValueError("This finding is missing an ID and cannot be resolved.")

    try:
        resolution_status = ResolutionStatus(status)
    except (TypeError, ValueError) as exc:
        raise ValueError("Please select a valid resolution status.") from exc

    answer = (user_answer or "").strip()
    # Discovery IDs are intentionally stable and category-prefixed by the prompt.
    is_recommendation = finding_id.upper().startswith("R")
    if (
        resolution_status == ResolutionStatus.RESOLVED
        and not answer
        and not is_recommendation
    ):
        raise ValueError(
            "Please provide a clarification before marking this item as Resolved."
        )

    return DiscoveryResolution(
        finding_id=finding_id,
        status=resolution_status,
        user_answer=answer,
        normalized_answer=answer,
    )


def _findings_by_id(discovery_result: DiscoveryResult) -> dict[str, DiscoveryFinding]:
    """Return findings keyed by ID and reject ambiguous Discovery output."""
    findings: dict[str, DiscoveryFinding] = {}
    for category in (
        discovery_result.conflicts,
        discovery_result.missing_information,
        discovery_result.assumptions,
        discovery_result.recommendations,
    ):
        for finding in category:
            finding_id = finding.id.strip()
            if not finding_id:
                raise ValueError("Discovery contains a finding without an ID.")
            if finding_id in findings:
                raise ValueError(f"Discovery contains duplicate finding ID: {finding_id}.")
            findings[finding_id] = finding
    return findings


def build_validated_product_context(
    original_context: str,
    discovery_result: DiscoveryResult,
    resolutions: dict[str, DiscoveryResolution],
) -> ValidatedProductContext:
    """Append explicit decisions to the original context without modifying it."""
    if not isinstance(original_context, str) or not original_context:
        raise ValueError("Product Context is empty. Upload and process documents first.")

    findings = _findings_by_id(discovery_result)
    included: list[DiscoveryResolution] = []
    appendix_entries: list[str] = []
    for finding_id, resolution in resolutions.items():
        if finding_id not in findings:
            raise ValueError(f"Resolution references unknown finding ID: {finding_id}.")
        if resolution.finding_id != finding_id:
            raise ValueError("Resolution finding ID does not match its saved key.")
        if resolution.status not in INCLUDED_STATUSES:
            continue

        finding = findings[finding_id]
        included.append(resolution)
        entry = [
            f"Finding ID: {finding_id}",
            f"Finding: {finding.title}",
            f"Resolution Status: {resolution.status.value}",
        ]
        if resolution.user_answer:
            entry.append(f"User Clarification: {resolution.user_answer}")
        appendix_entries.append("\n".join(entry))

    validated_context = original_context
    if appendix_entries:
        validated_context = (
            f"{original_context}\n\n--- Catalyst AI: Validated Clarifications ---\n\n"
            + "\n\n".join(appendix_entries)
        )

    return ValidatedProductContext(
        original_context=original_context,
        discovery_result=discovery_result,
        resolved_clarifications=included,
        validated_context=validated_context,
    )
