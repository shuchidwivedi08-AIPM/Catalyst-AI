"""Catalyst AI Streamlit application."""

from pathlib import Path

from docx import Document
from pypdf import PdfReader
import streamlit as st


SUPPORTED_FILE_TYPES = {"pdf", "docx", "txt"}


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


def display_document_metadata(
    file_name: str,
    file_type: str,
    file_size_kb: float,
    page_count: int | str,
    word_count: int,
) -> None:
    """Display uploaded document metadata in Streamlit."""
    st.subheader("Document Metadata")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("File Name", file_name)
        st.metric("File Type", file_type.upper())
        st.metric("File Size", f"{file_size_kb:.2f} KB")

    with col2:
        st.metric("Number of Pages", page_count)
        st.metric("Word Count", word_count)


st.set_page_config(
    page_title="Catalyst AI",
    page_icon="🚀",
    layout="centered",
)

st.title("Catalyst AI")
st.subheader("AI Product Analysis Assistant")
st.write("Version 1.1 - Document Upload & Text Extraction")

st.header("Upload a Business Document")
st.write("Upload a PDF, DOCX, or TXT file to extract its text and review document metadata.")

uploaded_file = st.file_uploader(
    "Choose a supported document",
    type=sorted(SUPPORTED_FILE_TYPES),
    help="Supported formats: PDF, DOCX, and TXT.",
)

if uploaded_file is not None:
    file_type = get_file_extension(uploaded_file.name)

    if file_type not in SUPPORTED_FILE_TYPES:
        st.error("That file type is not supported yet. Please upload a PDF, DOCX, or TXT file.")
    else:
        try:
            extracted_text, page_count = extract_text(uploaded_file, file_type)
            word_count = calculate_word_count(extracted_text)
            file_size_kb = uploaded_file.size / 1024

            st.success("Document uploaded and text extracted successfully.")
            display_document_metadata(
                uploaded_file.name,
                file_type,
                file_size_kb,
                page_count,
                word_count,
            )

            st.subheader("Extracted Text")
            st.text_area(
                "Review extracted text",
                value=extracted_text or "No readable text was found in this document.",
                height=350,
                label_visibility="collapsed",
            )
        except Exception as exc:
            st.error(
                "We could not extract text from this file. Please check that the document is not "
                "password-protected or corrupted, then try again."
            )
            st.caption(f"Technical details: {exc}")

st.divider()
st.header("Ready for AI Analysis (Coming in the next release)")
st.write(
    "Document text extraction is now available. AI-powered summarization, requirements review, "
    "and product analysis workflows are planned for the next release."
)
