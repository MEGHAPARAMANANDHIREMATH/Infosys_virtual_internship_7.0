# AI Project Intelligence & Risk Advisor

Milestone 1 builds the **document ingestion and RAG foundation**: upload project files, extract and clean text, chunk it, generate embeddings, store them in ChromaDB, and run project-scoped semantic search.

Milestone 2 adds **document intelligence agents** on that foundation: scope and deliverable extraction, risk detection with a delivery forecast, and blocker / action-item identification. Health scoring and a conversational assistant remain later work.

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
            ├── File parsers (PDF, DOCX, CSV, TXT, XLSX)
            ├── Intelligence agents (scope, risk/forecast, blockers)
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

Sample files are in `sample_data/` (Milestone 1: `project_proposal.txt`, `meeting_notes.txt`, `task_list.csv`) and `sample_data/milestone2/` after generating the Milestone 2 set.

## How to run Milestone 2 document intelligence

1. Open a project and upload a document, or pick a processed file under **Document Intelligence**.
2. Choose **Scope & Deliverables**, **Risk & Delivery Forecast**, **Blockers & Action Items**, or **Run All Agents**.
3. Review the tabbed results dashboard. Missing fields show as `Not specified`.

Optional OpenAI chat enrichment uses `OPENAI_API_KEY` with `LLM_PROVIDER=auto` or `openai`. Leave the key empty, or set `LLM_PROVIDER=grounded`, to use document-grounded extraction only (no invented answers).

```bash
cd backend
venv\Scripts\activate
python ..\sample_data\generate_milestone2_samples.py
```

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
| `OPENAI_API_KEY` | OpenAI embeddings and optional Milestone 2 chat analysis |
| `LLM_PROVIDER` | `auto` (OpenAI if a key is set), `openai`, or `grounded` |
| `OPENAI_CHAT_MODEL` | Chat model for optional agent enrichment |
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
| GET, POST | `/api/projects/{id}/intelligence/` |

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

Coverage includes project CRUD, PDF/DOCX/CSV/TXT/XLSX parsers, chunking, ChromaDB metadata, semantic search, **project isolation**, and Milestone 2 agent extraction.

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Backend disconnected in the UI | Start Django on port 8000; confirm `/api/health/` |
| `No readable text was found` | File may be scanned/image-only PDF or empty |
| Unsupported file format | Use PDF, DOCX, CSV, TXT, or XLSX |
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
