from types import SimpleNamespace

from catalyst_ai.ai.schemas import (
    DiscoveryFinding,
    DiscoveryResolution,
    DiscoveryResult,
    ProductUnderstanding,
    ResolutionStatus,
)
from catalyst_ai.projects import workflow_persistence as persistence


def test_uploaded_files_round_trip():
    original = persistence.RestoredUploadedFile(
        "requirements.txt", b"Business requirement", "text/plain"
    )

    records = persistence._serialize_uploaded_files([original])
    restored = persistence._deserialize_uploaded_files(records)

    assert len(restored) == 1
    assert restored[0].name == "requirements.txt"
    assert restored[0].type == "text/plain"
    assert restored[0].size == len(b"Business requirement")
    assert restored[0].getvalue() == b"Business requirement"


def test_session_models_round_trip(monkeypatch):
    session_state = {
        "discovery_result": DiscoveryResult(
            conflicts=[DiscoveryFinding(id="CON-001", title="Conflict")]
        ),
        "discovery_resolutions": {
            "CON-001": DiscoveryResolution(
                finding_id="CON-001",
                status=ResolutionStatus.RESOLVED,
                user_answer="Approved",
            )
        },
        "validated_product_context": None,
        "product_context_hash": "hash",
        "product_understanding": ProductUnderstanding(
            executive_summary="Summary"
        ),
        "product_understanding_context_source": "Original Product Context",
        "product_understanding_stakeholder": "Product Owner",
        "product_understanding_source_hash": "source-hash",
        "generated_artifact": None,
        "generated_artifact_type": None,
        "generated_artifact_metadata": None,
    }
    monkeypatch.setattr(persistence, "st", SimpleNamespace(session_state=session_state))

    payload = persistence._serialize_session()
    restored = persistence._deserialize_session(payload)

    assert isinstance(restored["discovery_result"], DiscoveryResult)
    assert restored["discovery_result"].conflicts[0].id == "CON-001"
    assert isinstance(restored["discovery_resolutions"]["CON-001"], DiscoveryResolution)
    assert restored["discovery_resolutions"]["CON-001"].status == ResolutionStatus.RESOLVED
    assert isinstance(restored["product_understanding"], ProductUnderstanding)
    assert restored["product_understanding"].executive_summary == "Summary"


def test_workflow_stage_uses_furthest_completed_milestone(monkeypatch):
    session_state = {
        "discovery_result": DiscoveryResult(),
        "discovery_resolutions": {},
        "validated_product_context": None,
        "product_understanding": None,
        "generated_artifact": None,
    }
    monkeypatch.setattr(persistence, "st", SimpleNamespace(session_state=session_state))

    assert persistence.determine_workflow_stage({"combined_text": "Context"}) == "DISCOVERY"

    session_state["discovery_resolutions"] = {
        "MIS-001": DiscoveryResolution(finding_id="MIS-001")
    }
    assert persistence.determine_workflow_stage({"combined_text": "Context"}) == "DISCOVERY_RESOLUTION"

    session_state["product_understanding"] = ProductUnderstanding()
    assert persistence.determine_workflow_stage({"combined_text": "Context"}) == "PRODUCT_UNDERSTANDING"
