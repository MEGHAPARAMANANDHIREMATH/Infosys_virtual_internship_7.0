# Milestone 1 architecture

React (Vite) talks to Django REST Framework over `/api`.

- **MySQL** (SQLite fallback) stores projects, documents, and chunk metadata.
- **MEDIA_ROOT** stores original uploaded files.
- **Ingestion** parses PDF/DOCX/CSV/TXT, cleans text, and chunks it.
- **Embedding service** creates real vectors (`local` sentence-transformers or OpenAI).
- **ChromaDB** stores vectors with `project_id` metadata. Search is always filtered by project.

See the root README for setup and endpoints.
