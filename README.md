# Catalyst AI

Catalyst AI is an AI Product Analysis Assistant designed to help product teams evaluate documents, synthesize insights, and accelerate product decision-making. This repository currently contains the foundation for the Streamlit application and supporting project structure.

## Vision

The long-term vision for Catalyst AI is to provide a focused workspace for product analysis workflows, including research synthesis, requirements review, competitive analysis, and structured AI-assisted recommendations. The first version establishes a clean foundation for future capabilities without implementing document upload, retrieval-augmented generation (RAG), or AI functionality yet.

## Current Scope

Version 1.0 includes:

- A basic Streamlit landing page.
- A Python project structure for agents, services, prompts, data, models, utilities, and documentation.
- Minimal dependencies required for the foundation setup.
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

The `.env.example` file documents expected local configuration values. Future AI-enabled features will use `OPENAI_API_KEY`, but the current foundation page does not call any AI services.

## Development Notes

- Keep the initial dependency set intentionally small.
- Add application logic under `services/`, reusable data models under `models/`, and shared helpers under `utils/` as the project grows.
- Place prompt templates in `prompts/` and product reference materials in `knowledge_base/` when those features are introduced.

## Roadmap

Future iterations may add:

- Document ingestion and analysis workflows.
- RAG over project knowledge bases.
- Product strategy and requirements evaluation agents.
- Exportable analysis outputs.
