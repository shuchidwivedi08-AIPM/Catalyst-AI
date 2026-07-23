# Catalyst AI

Catalyst AI is an AI Product Analysis Assistant designed to help product teams evaluate documents, synthesize insights, and accelerate product decision-making. This repository currently contains the foundation for the Streamlit application and supporting project structure.

## Vision

The long-term vision for Catalyst AI is to provide a focused workspace for product analysis workflows, including research synthesis, requirements review, competitive analysis, and structured AI-assisted recommendations. The first version established a clean foundation for future capabilities. The current application supports multi-document upload, text extraction, local document preprocessing, and stakeholder-specific AI Product Understanding generated through an isolated OpenAI integration.

## Current Features

- A Streamlit landing page for Catalyst AI.
- Multi-document Upload & Text Extraction for PDF, DOCX, and TXT files.
- Local document preprocessing after extraction, including duplicate blank-line removal, repeated-space normalization, leading/trailing whitespace trimming, and paragraph separation preservation where possible.
- Per-document metadata table, including file name, file type, file size, page count, word count, character count, and processing status.
- Internal Product Context object containing document metadata, cleaned text, combined text, and overall statistics for future analysis workflows.
- Combined in-memory product context that concatenates cleaned text in upload order with clear document-name separators.
- Project statistics summary card for total documents, total pages, total words, and total characters.
- Document Processing Pipeline UI that confirms upload, extraction, cleaning, and Product Context readiness.
- Stakeholder-specific AI Product Understanding for Product Owner and Technical Lead perspectives.
- Scrollable combined-text preview for uploaded business documents.
- A Python project structure for agents, services, prompts, data, models, utilities, and documentation.
- Example environment configuration.

## Document Preprocessing

After supported files are uploaded and text extraction completes, Catalyst AI runs a local preprocessing stage before any future AI analysis. The preprocessing layer:

- Cleans extracted text by removing duplicate blank lines, replacing repeated spaces with a single space, trimming leading and trailing whitespace, and preserving paragraph separation where possible.
- Preserves document boundaries by inserting clear separators with each document name when multiple documents are combined.
- Calculates per-document metadata: file name, file type, file size, page count, word count, and character count.
- Calculates overall project statistics: total documents, total pages, total words, and total characters.
- Builds an internal Product Context object with document metadata, cleaned text by file, combined text, and overall statistics.

Preprocessing runs locally in the Streamlit app. The optional AI Product Understanding step sends only the assembled Product Context through the Product Understanding Service to the OpenAI client and returns validated structured JSON to the UI.

## Project Structure

```text
Catalyst-AI/
├── app.py
├── catalyst_ai/
│   └── ai/
│       ├── __init__.py
│       ├── openai_client.py
│       ├── product_understanding_service.py
│       ├── prompts.py
│       ├── response_parser.py
│       └── schemas.py
├── requirements.txt
├── .env.example
├── README.md
├── agents/
├── services/
├── prompts/
├── knowledge_base/
├── data/
│   ├── uploads/
│   ├── outputs/
│   └── vector_db/
├── models/
├── utils/
└── docs/
```

## Requirements

- Python 3.10 or newer
- pip

## Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd Catalyst-AI
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a local environment file:

   ```bash
   cp .env.example .env
   ```

5. Run the Streamlit app:

   ```bash
   streamlit run app.py
   ```

6. Open the local URL shown by Streamlit in your browser.

## Environment Variables

The `.env.example` file documents expected local configuration values. Configure `OPENAI_API_KEY` for AI Product Understanding and optionally set `OPENAI_MODEL`; the default model is `gpt-5.5`.

## Development Notes

- Keep dependencies focused on the active Streamlit workflow.
- Add application logic under `services/`, reusable data models under `models/`, and shared helpers under `utils/` as the project grows.
- Place prompt templates in `prompts/` and product reference materials in `knowledge_base/` when those features are introduced.

## Roadmap

Planned iterations include:

- Additional AI artifacts such as PRDs, user stories, and test cases.
- Structured product requirements review workflows.
- RAG over project knowledge bases.
- Product strategy and competitive analysis agents.
- Exportable analysis outputs.
