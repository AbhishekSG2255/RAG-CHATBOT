# RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers user queries by retrieving relevant documents from a vector store and using them (optionally with persona context) to generate accurate, context-aware responses.

## Overview

- Purpose: Provide a local, end-to-end RAG demo combining a React frontend and a Django backend. The backend handles embeddings, nearest-neighbor retrieval (FAISS), optional summarization/persona logic, and generation. The frontend provides a simple chat UI.
- Primary users: developers, researchers, or hobbyists who want a self-hosted RAG pipeline for experimentation.

## Features

- Query embedding and retrieval (FAISS)
- Persona extraction and storage
- Optional summarization of retrieved passages
- Simple chat UI (React + Vite)
- Local persistence: `db.sqlite3`, `conversations.csv`, and `faiss_meta.json`

## Quick links
- Backend entrypoint: [backend/manage.py](backend/manage.py)
- Backend API endpoints: [backend/api/views.py](backend/api/views.py)
- Pipeline orchestration: [backend/api/pipeline.py](backend/api/pipeline.py)
- Retriever: [backend/rag_engine/retriever.py](backend/rag_engine/retriever.py)
- Embedder: [backend/rag_engine/embedder.py](backend/rag_engine/embedder.py)
- Frontend app: [frontend/src/App.jsx](frontend/src/App.jsx)
- Frontend chat UI: [frontend/src/components/ChatWindow.jsx](frontend/src/components/ChatWindow.jsx)

## Requirements / Prerequisites

- Python 3.8+ (for backend)
- Node.js 16+ and npm/yarn (for frontend)
- Optional: `gh` (GitHub CLI) if you want to create a remote repo from the CLI

## Backend (Django) — Setup and run

1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Apply Django migrations and create a superuser (if needed):

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser   # optional
```

4. Run the development server:

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/` by default.

## Frontend (React + Vite) — Setup and run

1. Install frontend dependencies and run dev server:

```bash
cd frontend
npm install
npm run dev
```

2. Open the provided local URL (usually `http://localhost:5173`) to use the chat UI.

## Data, Index & Persistence

- `db.sqlite3` — Django SQLite database storing models and (optionally) conversations.
- `faiss_meta.json` — metadata describing the FAISS/vector index.
- `conversations.csv` — exported/archived conversation logs.

If you need to rebuild the FAISS index, see `backend/rag_engine` for the scripts that ingest documents, build embeddings, and write the FAISS index and metadata.

## How the system works (high level)

1. The frontend sends a user query to the backend API.
2. The backend preprocesses the query, computes an embedding (`embedder.py`).
3. The embedding is used by the retriever (`retriever.py`) to find nearest passages in FAISS.
4. Retrieved passages are optionally summarized (`summarizer.py`) or augmented with persona context (`persona/*`).
5. The combined context is used to generate a response (via an LLM or a configured generator component).
6. The response is returned to the frontend and optionally recorded in `conversations.csv` / the database.

## API & Key files

- [backend/api/views.py](backend/api/views.py): HTTP endpoints for chat and management.
- [backend/api/pipeline.py](backend/api/pipeline.py): Orchestrates preprocessing → retrieval → summarization → generation.
- [backend/rag_engine/embedder.py](backend/rag_engine/embedder.py): Creates embeddings for queries/documents.
- [backend/rag_engine/retriever.py](backend/rag_engine/retriever.py): FAISS lookup and result ranking.
- [backend/rag_engine/summarizer.py](backend/rag_engine/summarizer.py): Summarizes or condenses retrieved context.
- [backend/persona/extractor.py](backend/persona/extractor.py) and [backend/persona/store.py](backend/persona/store.py): Persona extraction and storage utilities.

## Development notes

- Keep an eye on `faiss_meta.json` when moving or rebuilding the FAISS index.
- If you change embedding models or dimensions, you must rebuild the FAISS index.
- Use `conversations.csv` for lightweight exports; use Django admin for richer DB inspection.

## Testing

- Backend unit tests (if present) can be run from the `backend` folder using Django's test runner:

```bash
cd backend
python manage.py test
```

## Contributing

1. Fork and create a feature branch.
2. Make your changes and add tests where appropriate.
3. Run linters/tests locally.
4. Open a pull request with a clear description of changes.

## License

This project does not include a license file by default. Add a `LICENSE` file in the repository root if you want to clarify usage terms.

## Contact / Questions

If you want me to run setup commands, commit this README, or push to your remote, tell me which steps to execute and I will run them.

