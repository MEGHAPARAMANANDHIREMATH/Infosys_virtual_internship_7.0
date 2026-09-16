# AI Project Intelligence & Risk Advisor

Milestone 1 builds the **document ingestion and RAG foundation**: upload project files, extract and clean text, chunk it, generate embeddings, store them in ChromaDB, and run project-scoped semantic search.

Milestone 2 extends this foundation with **project document intelligence and risk management** while preserving all Milestone 1 capabilities. The application continues to support document upload, processing, and semantic search, and adds a new intelligence layer for scope extraction, risk detection, delivery forecasting, and blocker/action tracking.

## Milestone 2 overview

Milestone 2 adds three document-analysis agents to the existing project workflow:

- Scope & Deliverable Extraction Agent: extracts the project name, objective, scope, major deliverables, tasks, milestones, dates, owners, and dependencies from uploaded project documents.
- Risk Detection & Delivery Forecasting Agent: identifies schedule risks, delayed tasks, dependency gaps, missing resources, unrealistic deadlines, and delivery challenges, then produces a forecast with status, reason, key risks, impacted milestones, and recommended actions.
- Blocker & Action Item Identification Agent: extracts blockers, pending decisions, open issues, and action items with evidence, owners, due dates, priorities, and status.

The Milestone 2 dashboard is added alongside the existing Milestone 1 project workspace rather than replacing it. This keeps the original project ingestion and retrieval features intact while adding structured intelligence on top of the same uploaded document data.

## Milestone 1 vs Milestone 2

| Milestone | Focus | Included functionality |
| --- | --- | --- |
| Milestone 1 | Document ingestion and retrieval | Upload, validation, text extraction, chunking, embeddings, ChromaDB indexing, and semantic search |
| Milestone 2 | Project intelligence and risk management | Scope extraction, deliverable analysis, risk detection, delivery forecasting, blocker/action identification, and structured dashboard output |

Milestone 1 remains the base layer, and Milestone 2 builds directly on top of it without removing or altering the original workflow.

Sample validation inputs are in `sample_data/milestone2/`, and the validation summary is captured in `VALIDATION_REPORT.md`.

## Architecture

```
React Frontend
      |
      | REST API
      ↓
Django REST API
      |
      ├── MySQL (or SQLite in development)
      ├── File storage (MEDIA_ROOT)
      └── RAG service
            ├── File parsers (PDF, DOCX, CSV, TXT)
            ├── Text cleaner
            ├── Chunker
            ├── Embedding service
            └── ChromaDB (filtered by project_id)
```

## Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Optional: MySQL 8 if you do not want the SQLite development fallback
- Disk space for the local embedding model (`all-MiniLM-L6-v2`) on first run

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS
pip install -r requirements.txt
copy .env.example .env         # Windows
# cp .env.example .env         # Linux / macOS
```

Edit `backend/.env` as needed. Do not put real API keys in source control.

## Frontend setup

```bash
cd frontend
npm install
```

## MySQL configuration

The API is MySQL-compatible. For local development, `DATABASE_ENGINE=sqlite` is the default fallback.

To use MySQL:

1. Create a database, for example `project_intelligence`.
2. Set in `.env`:

```
DATABASE_ENGINE=mysql
MYSQL_DATABASE=project_intelligence
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

## ChromaDB setup

ChromaDB runs **embedded** (no separate server). Vectors persist under `CHROMA_PERSIST_DIR` (default `backend/data/chroma`).

Every indexed chunk stores `project_id`. Search always filters by that field so Project A cannot retrieve Project B chunks.

## Embedding configuration

Set `EMBEDDING_PROVIDER` in `.env`:

| Value | Behavior |
|-------|----------|
| `local` (default) | Real embeddings via `sentence-transformers` and `EMBEDDING_MODEL` (default `all-MiniLM-L6-v2`). No API key. First run downloads the model. |
| `openai` | Uses `OPENAI_API_KEY` and `OPENAI_EMBEDDING_MODEL`. Never commit the key. |

This project does **not** generate fake or random embeddings.

## Database migrations

```bash
cd backend
venv\Scripts\activate
python manage.py migrate
```

## How to start the backend

```bash
cd backend
venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```

Health check: http://localhost:8000/api/health/

## How to start the frontend

```bash
cd frontend
npm run dev
```

App: http://localhost:5173

Vite proxies `/api` to `http://localhost:8000`.

## How to upload a document

1. Open the app and create a project (name, description, dates, status).
2. Click **Open Project**.
3. Drag and drop or select a PDF, DOCX, CSV, or TXT file.
4. Wait for processing. Status should become `PROCESSED` (or `FAILED` with a clear error).

Sample files are in `sample_data/` (`project_proposal.txt`, `meeting_notes.txt`, `task_list.csv`).

## How to perform semantic search

1. Open a project that has processed documents.
2. In **Semantic Search**, enter a query such as `What are the main project requirements?`
3. Review retrieved chunks, source filename, page number (when available), and similarity score.

Milestone 1 does **not** call an LLM to generate an answer. Retrieval is the deliverable.

## Environment variables

See `.env.example` (repo root) and `backend/.env.example`.

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret (use a unique value outside class demos) |
| `DJANGO_DEBUG` | `true` / `false` |
| `DATABASE_ENGINE` | `sqlite` or `mysql` |
| `MYSQL_*` | MySQL connection when engine is mysql |
| `MEDIA_ROOT` | Uploaded file storage |
| `MAX_FILE_SIZE_MB` | Upload size limit |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking |
| `EMBEDDING_PROVIDER` | `local` or `openai` |
| `EMBEDDING_MODEL` | Local sentence-transformers model |
| `OPENAI_API_KEY` | Only if using OpenAI embeddings |
| `CHROMA_PERSIST_DIR` | Vector store path |
| `ENFORCE_PROJECT_ACCESS` | If `true`, `X-User-Id` must match `created_by` |
| `CORS_ORIGINS` | Allowed frontend origins |

## API endpoints

| Method | Path |
|--------|------|
| GET | `/api/health/` |
| GET, POST | `/api/projects/` |
| GET, PUT, DELETE | `/api/projects/{id}/` |
| GET, POST | `/api/projects/{id}/documents/` |
| DELETE | `/api/documents/{id}/` |
| POST | `/api/projects/{id}/search/` |

Search body:

```json
{ "query": "What are the main functional requirements?", "top_k": 5 }
```

## Tests

```bash
cd backend
venv\Scripts\activate
python manage.py test
```

Coverage includes project CRUD, all four file types, parsers, chunking, ChromaDB metadata, semantic search, and **project isolation** (Project A vs Project B).

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Backend disconnected in the UI | Start Django on port 8000; confirm `/api/health/` |
| `No readable text was found` | File may be scanned/image-only PDF or empty |
| Unsupported file format | Use PDF, DOCX, CSV, or TXT |
| File too large | Raise `MAX_FILE_SIZE_MB` or use a smaller file |
| Embedding download is slow | First `local` run fetches the Hugging Face model; keep network available once |
| OpenAI embedding errors | Check `OPENAI_API_KEY` or switch to `EMBEDDING_PROVIDER=local` |
| MySQL connection errors | Verify server, credentials, and database name, or use `DATABASE_ENGINE=sqlite` |
| Search returns nothing | Confirm documents are `PROCESSED` and you are searching the same project |
| Chroma path permission errors | Ensure `CHROMA_PERSIST_DIR` is writable |

## Project structure

```
backend/
  manage.py
  config/                 # Django settings and URLs
  projects/               # Project CRUD
  documents/              # Document upload and metadata
  ingestion/              # Parsers, cleaner, chunker, processor
  rag/                    # Embeddings, ChromaDB, retrieval
frontend/
  src/pages/
  src/components/
  src/services/
media/                    # Uploaded files (local)
sample_data/              # Demo documents
```

## Known limitations (Milestone 1)

- Authentication is a stub (`X-User-Id` / `created_by`). Full auth belongs later.
- No OCR for scanned PDFs.
- Processing runs in the upload request (no background worker).
- No LLM answers, risk agents, dashboards, or health scoring.

