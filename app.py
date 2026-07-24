"""Catalyst AI Streamlit application."""

import hashlib
from pathlib import Path
import re
from typing import Any

from docx import Document
from pypdf import PdfReader
import streamlit as st

from catalyst_ai.ai.capabilities.discovery_engine import run_discovery
from catalyst_ai.ai.capabilities.discovery_resolution import (
    build_validated_product_context,
    save_resolution,
)
from catalyst_ai.ai.openai_client import OpenAIConfigurationError
from catalyst_ai.ai.product_understanding_service import generate_product_understanding
from catalyst_ai.ai.response_parser import DiscoveryParseError, ProductUnderstandingParseError
from catalyst_ai.ai.schemas import ResolutionStatus


SUPPORTED_FILE_TYPES = {"pdf", "docx", "txt"}
DOCUMENT_SEPARATOR = "\n\n--- Document: {file_name} ---\n\n"


def get_file_extension(file_name: str) -> str:
    """Return the lowercase file extension without the leading dot."""
    return Path(file_name).suffix.lower().lstrip(".")


def extract_pdf_text(uploaded_file) -> tuple[str, int]:
    """Extract text and page count from a PDF upload."""
    reader = PdfReader(uploaded_file)
    page_text = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page_text).strip(), len(reader.pages)


def extract_docx_text(uploaded_file) -> str:
    """Extract text from a DOCX upload."""
    document = Document(uploaded_file)
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text]
    return "\n".join(paragraphs).strip()


def extract_txt_text(uploaded_file) -> str:
    """Extract text from a TXT upload using standard Python decoding."""
    raw_text = uploaded_file.getvalue()
    try:
        return raw_text.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_text.decode("latin-1").strip()


def extract_text(uploaded_file, file_type: str) -> tuple[str, int | str]:
    """Extract document text and return text plus PDF page count or N/A."""
    if file_type == "pdf":
        return extract_pdf_text(uploaded_file)
    if file_type == "docx":
        return extract_docx_text(uploaded_file), "N/A"
    if file_type == "txt":
        return extract_txt_text(uploaded_file), "N/A"
    raise ValueError("Unsupported file type")


def clean_extracted_text(text: str) -> str:
    """Clean extracted text while preserving paragraph separation where possible."""
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized_text = re.sub(r"[ \t]+", " ", normalized_text)
    normalized_text = re.sub(r" *\n *", "\n", normalized_text)
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)
    return normalized_text.strip()


def calculate_word_count(text: str) -> int:
    """Calculate the number of words in text."""
    return len(text.split())


def format_file_size(size_bytes: int) -> str:
    """Format bytes as a readable KB string."""
    return f"{size_bytes / 1024:.2f} KB"


def build_document_context(document_metadata: list[dict[str, Any]]) -> str:
    """Build a combined product context from uploaded documents in upload order."""
    context_sections = []

    for document in document_metadata:
        if document["Status"] != "Processed":
            continue

        separator = DOCUMENT_SEPARATOR.format(file_name=document["File Name"])
        cleaned_text = str(document["Cleaned Text"])
        context_sections.append(
            f"{separator}{cleaned_text or 'No readable text was found in this document.'}"
        )

    return "".join(context_sections).strip()


def calculate_overall_statistics(document_metadata: list[dict[str, Any]]) -> dict[str, int]:
    """Calculate product context statistics across successfully processed documents."""
    processed_documents = [
        document for document in document_metadata if document["Status"] == "Processed"
    ]
    total_pages = sum(
        page_count
        for page_count in (document["Page Count"] for document in processed_documents)
        if isinstance(page_count, int)
    )

    return {
        "Total Documents": len(processed_documents),
        "Total Pages": total_pages,
        "Total Words": sum(int(document["Word Count"]) for document in processed_documents),
        "Total Characters": sum(
            int(document["Character Count"]) for document in processed_documents
        ),
    }


def build_product_context(document_metadata: list[dict[str, Any]]) -> dict[str, Any]:
    """Create the internal Product Context object for future local AI analysis."""
    processed_documents = [
        document for document in document_metadata if document["Status"] == "Processed"
    ]
    combined_text = build_document_context(processed_documents)

    return {
        "document_metadata": processed_documents,
        "cleaned_text": {
            str(document["File Name"]): document["Cleaned Text"]
            for document in processed_documents
        },
        "combined_text": combined_text,
        "overall_statistics": calculate_overall_statistics(processed_documents),
    }


def display_processing_pipeline(product_context: dict[str, Any] | None) -> None:
    """Display the local document processing pipeline completion state."""
    st.subheader("Document Processing Pipeline")
    pipeline_steps = [
        "Upload Complete",
        "Text Extraction Complete",
        "Text Cleaning Complete",
        "Product Context Ready",
    ]

    if product_context:
        for step in pipeline_steps:
            st.markdown(f"✓ {step}")
    else:
        st.info("Upload supported documents to start the local processing pipeline.")


def display_summary_statistics(overall_statistics: dict[str, int]) -> None:
    """Display summary statistics for all processed documents."""
    st.subheader("Project Statistics")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)
        col1.metric("Total Documents", overall_statistics["Total Documents"])
        col2.metric("Total Pages", overall_statistics["Total Pages"])
        col3.metric("Total Words", overall_statistics["Total Words"])
        col4.metric("Total Characters", overall_statistics["Total Characters"])


def display_stakeholder_perspective() -> str:
    """Display stakeholder perspective selection and return the selected stakeholder."""
    st.header("👤 Stakeholder Perspective")
    st.write("Select the stakeholder perspective for future AI analysis.")

    selected_stakeholder = st.radio(
        "Stakeholder",
        ["Product Owner", "Technical Lead"],
        index=0,
    )

    stakeholder_focus = {
        "Product Owner": [
            "Business Goals",
            "Functional Requirements",
            "Risks",
            "Assumptions",
            "Open Questions",
        ],
        "Technical Lead": [
            "Technical Dependencies",
            "APIs & Integrations",
            "Non-functional Requirements",
            "Technical Risks",
            "Technical Constraints",
        ],
    }

    focus_items = "\n".join(f"• {item}" for item in stakeholder_focus[selected_stakeholder])
    st.info(f"👤 {selected_stakeholder}\n\nPrimary Focus\n\n{focus_items}")

    return selected_stakeholder


def initialize_session_state() -> None:
    """Initialize state that must survive Streamlit's widget reruns."""
    st.session_state.setdefault("discovery_result", None)
    st.session_state.setdefault("discovery_resolutions", {})
    st.session_state.setdefault("validated_product_context", None)
    st.session_state.setdefault("product_context_hash", None)


def reset_context_dependent_state() -> None:
    """Remove findings and decisions that belong to a different Product Context."""
    st.session_state["discovery_result"] = None
    st.session_state["discovery_resolutions"] = {}
    st.session_state["validated_product_context"] = None
    for key in list(st.session_state):
        if key.startswith(("status_", "answer_", "save_")):
            del st.session_state[key]


def get_all_discovery_findings(discovery_result) -> list[tuple[str, object]]:
    """Return all findings with their category, rejecting duplicate IDs."""
    all_findings = []
    finding_ids = set()
    for category, findings in (
        ("conflicts", discovery_result.conflicts),
        ("missing_information", discovery_result.missing_information),
        ("assumptions", discovery_result.assumptions),
        ("recommendations", discovery_result.recommendations),
    ):
        for finding in findings:
            if not finding.id or finding.id in finding_ids:
                raise ValueError("Discovery findings must have unique, non-empty IDs.")
            finding_ids.add(finding.id)
            all_findings.append((category, finding))
    return all_findings


def display_resolution_summary(discovery_result) -> None:
    """Display the existing discovery counts and the resolution progress."""
    summary = discovery_result.summary
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    col1.metric("Conflicts", summary.conflicts)
    col2.metric("Missing Information", summary.missing_information)
    col3.metric("Assumptions", summary.assumptions)
    col4.metric("Recommendations", summary.recommendations)

    findings = get_all_discovery_findings(discovery_result)
    resolutions = st.session_state["discovery_resolutions"]
    resolved = sum(
        resolution.status == ResolutionStatus.RESOLVED
        for resolution in resolutions.values()
    )
    deferred = sum(
        resolution.status == ResolutionStatus.DEFERRED
        for resolution in resolutions.values()
    )
    remaining = len(findings) - sum(
        resolution.status in {
            ResolutionStatus.RESOLVED,
            ResolutionStatus.DEFERRED,
            ResolutionStatus.NOT_APPLICABLE,
        }
        for resolution in resolutions.values()
    )
    metrics = st.columns(3)
    metrics[0].metric("Resolved", resolved)
    metrics[1].metric("Remaining", max(remaining, 0))
    metrics[2].metric("Deferred", deferred)
    st.progress(resolved / len(findings) if findings else 0.0)


def _status_indicator(status: ResolutionStatus) -> str:
    return {
        ResolutionStatus.RESOLVED: "✅ Resolved",
        ResolutionStatus.DEFERRED: "⏸ Deferred",
        ResolutionStatus.NOT_APPLICABLE: "➖ Not Applicable",
        ResolutionStatus.UNRESOLVED: "⚠ Unresolved",
    }[status]


def display_resolution_controls(title: str, findings, is_recommendation: bool = False) -> None:
    """Render structured controls for one category of persisted findings."""
    with st.expander(title, expanded=False):
        if not findings:
            st.write("No findings identified.")
            return

        for finding in findings:
            with st.container(border=True):
                st.markdown(f"**{finding.id}: {finding.title}**")
                st.caption(f"Severity: {finding.severity}")
                st.write(finding.description or "No description provided.")
                if finding.source_documents:
                    st.caption("Source documents: " + ", ".join(finding.source_documents))
                saved = st.session_state["discovery_resolutions"].get(finding.id)
                current_status = saved.status if saved else ResolutionStatus.UNRESOLVED
                st.caption(_status_indicator(current_status))

                if is_recommendation:
                    choices = ["Pending", "Accepted", "Dismissed"]
                    mapping = {
                        "Pending": ResolutionStatus.UNRESOLVED,
                        "Accepted": ResolutionStatus.RESOLVED,
                        "Dismissed": ResolutionStatus.NOT_APPLICABLE,
                    }
                    reverse_mapping = {value: key for key, value in mapping.items()}
                    selected = st.selectbox(
                        "Decision",
                        choices,
                        index=choices.index(reverse_mapping.get(current_status, "Pending")),
                        key=f"status_{finding.id}",
                    )
                    selected_status = mapping[selected]
                else:
                    statuses = list(ResolutionStatus)
                    selected_status = st.selectbox(
                        "Status",
                        statuses,
                        index=statuses.index(current_status),
                        format_func=lambda status: status.value,
                        key=f"status_{finding.id}",
                    )
                answer = st.text_area(
                    "Your clarification" if not is_recommendation else "Optional note",
                    value=saved.user_answer if saved else "",
                    key=f"answer_{finding.id}",
                )
                if st.button("Save Resolution", key=f"save_{finding.id}"):
                    try:
                        resolution = save_resolution(finding, selected_status, answer)
                        st.session_state["discovery_resolutions"][finding.id] = resolution
                        st.success("Resolution saved.")
                    except ValueError as exc:
                        st.error(str(exc))


def display_discovery_result(discovery_result, product_context: dict[str, Any]) -> None:
    """Display persistent findings, their structured controls, and validation action."""
    try:
        display_resolution_summary(discovery_result)
        display_resolution_controls("Conflicts", discovery_result.conflicts)
        display_resolution_controls("Missing Information", discovery_result.missing_information)
        display_resolution_controls("Assumptions", discovery_result.assumptions)
        display_resolution_controls(
            "Recommendations", discovery_result.recommendations, is_recommendation=True
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    st.subheader("Build Validated Product Context")
    if st.button("Create Validated Context"):
        try:
            validated = build_validated_product_context(
                product_context["combined_text"],
                discovery_result,
                st.session_state["discovery_resolutions"],
            )
            st.session_state["validated_product_context"] = validated
            unresolved = len(get_all_discovery_findings(discovery_result)) - len(
                validated.resolved_clarifications
            )
            st.success("Validated Product Context created.")
            if unresolved:
                st.warning(f"Validated Context created with {unresolved} unresolved findings.")
        except ValueError as exc:
            st.error(str(exc))

    display_validated_context()


def display_validated_context() -> None:
    """Show the generated context without allowing edits to its source content."""
    validated = st.session_state["validated_product_context"]
    if validated:
        st.text_area(
            "Validated Product Context",
            value=validated.validated_context,
            height=350,
            disabled=True,
        )


def display_ai_discovery_engine(product_context: dict[str, Any]) -> None:
    """Display controls and results for the independent AI Discovery Engine."""
    st.header("🔍 AI Discovery Engine")
    st.write("Analyze the uploaded Product Context before generating Product Understanding.")

    if st.button("Run Discovery"):
        try:
            with st.spinner("Analyzing Product Context..."):
                discovery_result = run_discovery(product_context)
            reset_context_dependent_state()
            st.session_state["discovery_result"] = discovery_result
            st.success("AI Discovery completed.")
        except (OpenAIConfigurationError, DiscoveryParseError, ValueError):
            st.error(
                "Unable to complete Discovery.\n\n"
                "Please check API configuration and try again."
            )
        except Exception:
            st.error(
                "Unable to complete Discovery.\n\n"
                "Please check API configuration and try again."
            )

    discovery_result = st.session_state["discovery_result"]
    if discovery_result:
        display_discovery_result(discovery_result, product_context)


def display_product_understanding(product_understanding) -> None:
    """Display structured AI Product Understanding in the Streamlit UI."""
    st.subheader("Executive Summary")
    st.write(product_understanding.executive_summary or "No executive summary provided.")

    st.subheader("Business Problem")
    st.write(product_understanding.business_problem or "No business problem provided.")

    sections = {
        "Business Goals": product_understanding.business_goals,
        "Functional Requirements": product_understanding.functional_requirements,
        "Non-functional Requirements": product_understanding.non_functional_requirements,
        "Risks": product_understanding.risks,
        "Assumptions": product_understanding.assumptions,
        "Open Questions": product_understanding.open_questions,
        "Recommendations": product_understanding.recommendations,
    }

    for title, items in sections.items():
        st.subheader(title)
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.write("No items identified in the provided Product Context.")


def display_ai_product_understanding(product_context: dict[str, Any], selected_stakeholder: str) -> None:
    """Display controls and results for stakeholder-specific AI Product Understanding."""
    st.header("🤖 AI Product Understanding")
    st.write(f"Selected Stakeholder: **{selected_stakeholder}**")

    validated = st.session_state["validated_product_context"]
    context_options = ["Original Product Context"]
    if validated:
        context_options.append("Validated Product Context")
    selected_context = st.radio(
        "Context used for AI Product Understanding",
        context_options,
        index=0,
    )
    apu_context = product_context
    if selected_context == "Validated Product Context":
        apu_context = {**product_context, "combined_text": validated.validated_context}

    if st.button("Analyze Product Context", type="primary"):
        try:
            with st.spinner("Analyzing Product Context..."):
                product_understanding = generate_product_understanding(
                    apu_context,
                    selected_stakeholder,
                )
            st.success("AI Product Understanding generated.")
            display_product_understanding(product_understanding)
        except OpenAIConfigurationError as exc:
            st.error(str(exc))
        except (ProductUnderstandingParseError, ValueError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error("AI Product Understanding failed. Please retry or check configuration.")
            st.caption(f"Technical details: {exc}")


def display_document_metadata(document_metadata: list[dict[str, Any]]) -> None:
    """Display uploaded document metadata in a Streamlit table."""
    st.subheader("Document Metadata")
    st.table(
        [
            {
                "File Name": document["File Name"],
                "File Type": document["File Type"],
                "File Size": document["File Size"],
                "Page Count": document["Page Count"],
                "Word Count": document["Word Count"],
                "Character Count": document["Character Count"],
                "Status": document["Status"],
            }
            for document in document_metadata
        ]
    )


st.set_page_config(
    page_title="Catalyst AI",
    page_icon="🚀",
    layout="centered",
)

initialize_session_state()

st.title("Catalyst AI")
st.subheader("AI Product Analysis Assistant")
st.write("Version 1.3 - AI Product Understanding")

st.header("Upload Business Documents")
st.write(
    "Upload one or more PDF, DOCX, or TXT files to extract and locally preprocess text "
    "before future AI analysis."
)

uploaded_files = st.file_uploader(
    "Choose supported documents",
    type=sorted(SUPPORTED_FILE_TYPES),
    accept_multiple_files=True,
    help="Supported formats: PDF, DOCX, and TXT.",
)

product_context = None

if uploaded_files:
    document_metadata = []

    for uploaded_file in uploaded_files:
        file_type = get_file_extension(uploaded_file.name)
        document = {
            "File Name": uploaded_file.name,
            "File Type": file_type.upper() if file_type else "Unknown",
            "File Size": format_file_size(uploaded_file.size),
            "File Size Bytes": uploaded_file.size,
            "Page Count": "N/A",
            "Word Count": 0,
            "Character Count": 0,
            "Status": "Pending",
            "Extracted Text": "",
            "Cleaned Text": "",
        }

        if file_type not in SUPPORTED_FILE_TYPES:
            document["Status"] = "Unsupported file type"
            document_metadata.append(document)
            st.error(
                f"{uploaded_file.name}: That file type is not supported yet. "
                "Please upload a PDF, DOCX, or TXT file."
            )
            continue

        try:
            extracted_text, page_count = extract_text(uploaded_file, file_type)
            cleaned_text = clean_extracted_text(extracted_text)
            document["Page Count"] = page_count
            document["Word Count"] = calculate_word_count(cleaned_text)
            document["Character Count"] = len(cleaned_text)
            document["Status"] = "Processed"
            document["Extracted Text"] = extracted_text
            document["Cleaned Text"] = cleaned_text
            document_metadata.append(document)
        except Exception as exc:
            document["Status"] = "Processing failed"
            document_metadata.append(document)
            st.error(
                f"{uploaded_file.name}: We could not process this file. Please check that "
                "the document is not password-protected or corrupted, then try again."
            )
            st.caption(f"Technical details: {exc}")

    successful_documents = [
        document for document in document_metadata if document["Status"] == "Processed"
    ]

    if successful_documents:
        product_context = build_product_context(document_metadata)
        context_hash = hashlib.sha256(
            product_context["combined_text"].encode("utf-8")
        ).hexdigest()
        if st.session_state["product_context_hash"] != context_hash:
            reset_context_dependent_state()
            st.session_state["product_context_hash"] = context_hash
        st.success(f"Processed {len(successful_documents)} document(s) locally.")

    display_processing_pipeline(product_context)
    display_document_metadata(document_metadata)

    if product_context:
        display_summary_statistics(product_context["overall_statistics"])

        st.subheader("Combined Product Context")
        st.text_area(
            "Review combined product context",
            value=product_context["combined_text"],
            height=350,
            label_visibility="collapsed",
        )

        st.divider()
        display_ai_discovery_engine(product_context)

        st.divider()
        selected_stakeholder = display_stakeholder_perspective()

        st.divider()
        display_ai_product_understanding(product_context, selected_stakeholder)
else:
    if st.session_state["product_context_hash"] is not None:
        reset_context_dependent_state()
        st.session_state["product_context_hash"] = None
    display_processing_pipeline(product_context)
