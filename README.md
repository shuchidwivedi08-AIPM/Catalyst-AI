# Catalyst AI

Catalyst AI is an AI Product Analysis Assistant designed to help product teams evaluate documents, synthesize insights, and accelerate product decision-making. This repository currently contains the foundation for the Streamlit application and supporting project structure.

## Vision

The long-term vision for Catalyst AI is to provide a focused workspace for product analysis workflows, including research synthesis, requirements review, competitive analysis, and structured AI-assisted recommendations. The first version established a clean foundation for future capabilities. The current application now supports multi-document upload and text extraction as the first functional workflow before retrieval-augmented generation (RAG) and AI analysis are introduced.

## Current Features

- A Streamlit landing page for Catalyst AI.
- Multi-document Upload & Text Extraction for PDF, DOCX, and TXT files.
- Per-document metadata table, including file name, file type, file size, page count, word count, and extraction status.
- Combined in-memory product context that concatenates extracted text in upload order with clear document separators.
- Summary statistics for total documents, total pages, and total words.
- Scrollable combined-text preview for uploaded business documents.
- A Python project structure for agents, services, prompts, data, models, utilities, and documentation.
- Example environment configuration.

## Project Structure

```text
Catalyst-AI/
├── app.py
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

The `.env.example` file documents expected local configuration values. Future AI-enabled features will use `OPENAI_API_KEY`, but the current document extraction workflow does not call any AI services.

## Development Notes

- Keep dependencies focused on the active Streamlit workflow.
- Add application logic under `services/`, reusable data models under `models/`, and shared helpers under `utils/` as the project grows.
- Place prompt templates in `prompts/` and product reference materials in `knowledge_base/` when those features are introduced.

## Roadmap

Planned iterations include:

- AI analysis of extracted document text, including summarization and insight generation.
- Structured product requirements review workflows.
- RAG over project knowledge bases.
- Product strategy and competitive analysis agents.
- Exportable analysis outputs.
