"""Catalyst AI Streamlit application."""

from pathlib import Path

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


def calculate_word_count(text: str) -> int:
    """Calculate the number of words in extracted text."""
    return len(text.split())


def build_document_context(document_metadata: list[dict[str, object]]) -> str:
    """Build a combined product context from uploaded documents in upload order."""
    context_sections = []

    for document in document_metadata:
        if document["Status"] != "Extracted":
            continue

        separator = DOCUMENT_SEPARATOR.format(file_name=document["File Name"])
        extracted_text = str(document["Extracted Text"])
        context_sections.append(
            f"{separator}{extracted_text or 'No readable text was found in this document.'}"
        )

    return "".join(context_sections).strip()


def display_summary_statistics(document_metadata: list[dict[str, object]]) -> None:
    """Display summary statistics for all uploaded documents."""
    total_pages = sum(
        page_count
        for page_count in (document["Pages"] for document in document_metadata)
        if isinstance(page_count, int)
    )
    total_words = sum(int(document["Word Count"]) for document in document_metadata)

    st.subheader("Summary Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Documents", len(document_metadata))
    col2.metric("Total Pages", total_pages)
    col3.metric("Total Words", total_words)


def display_document_metadata(document_metadata: list[dict[str, object]]) -> None:
    """Display uploaded document metadata in a Streamlit table."""
    st.subheader("Document Metadata")
    st.table(
        [
            {
                "File Name": document["File Name"],
                "Type": document["Type"],
                "Size": document["Size"],
                "Pages": document["Pages"],
                "Word Count": document["Word Count"],
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
st.write("Version 1.1 - Multi-Document Upload & Text Extraction")

st.header("Upload Business Documents")
st.write("Upload one or more PDF, DOCX, or TXT files to extract text and review document metadata.")

uploaded_files = st.file_uploader(
    "Choose supported documents",
    type=sorted(SUPPORTED_FILE_TYPES),
    accept_multiple_files=True,
    help="Supported formats: PDF, DOCX, and TXT.",
)

if uploaded_files:
    document_metadata = []

    for uploaded_file in uploaded_files:
        file_type = get_file_extension(uploaded_file.name)
        file_size_kb = uploaded_file.size / 1024
        document = {
            "File Name": uploaded_file.name,
            "Type": file_type.upper() if file_type else "Unknown",
            "Size": f"{file_size_kb:.2f} KB",
            "Pages": "N/A",
            "Word Count": 0,
            "Status": "Pending",
            "Extracted Text": "",
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
            document["Pages"] = page_count
            document["Word Count"] = calculate_word_count(extracted_text)
            document["Status"] = "Extracted"
            document["Extracted Text"] = extracted_text
            document_metadata.append(document)
        except Exception as exc:
            document["Status"] = "Extraction failed"
            document_metadata.append(document)
            st.error(
                f"{uploaded_file.name}: We could not extract text from this file. Please check that "
                "the document is not password-protected or corrupted, then try again."
            )
            st.caption(f"Technical details: {exc}")

    successful_documents = [
        document for document in document_metadata if document["Status"] == "Extracted"
    ]

    if successful_documents:
        st.success(f"Extracted text from {len(successful_documents)} document(s).")

    display_document_metadata(document_metadata)
    display_summary_statistics(document_metadata)

    combined_product_context = build_document_context(document_metadata)

    if combined_product_context:
        st.subheader("Combined Product Context")
        st.text_area(
            "Review combined product context",
            value=combined_product_context,
            height=350,
            label_visibility="collapsed",
        )

st.divider()
st.header("Ready for AI Analysis (Coming in the next release)")
st.write(
    "Document text extraction is now available. AI-powered summarization, requirements review, "
    "and product analysis workflows are planned for the next release."
)
