"""Catalyst AI Streamlit application."""

from pathlib import Path
import re
from typing import Any

from docx import Document
from pypdf import PdfReader
import streamlit as st


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


def display_ai_analysis_placeholder(selected_stakeholder: str) -> None:
    """Display a visual placeholder for future stakeholder-specific AI analysis."""
    st.header("🤖 AI Analysis")
    st.info(
        f"Selected Stakeholder:\n{selected_stakeholder}\n\n"
        "Status:\n🚧 Coming in the next iteration"
    )


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

st.title("Catalyst AI")
st.subheader("AI Product Analysis Assistant")
st.write("Version 1.2 - Document Pre-processing")

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
        selected_stakeholder = display_stakeholder_perspective()

        st.divider()
        display_ai_analysis_placeholder(selected_stakeholder)
else:
    display_processing_pipeline(product_context)
