# Milestone 1 Submission Report

## AI Project Intelligence & Risk Advisor

---

## 1. Project Title

**AI Project Intelligence & Risk Advisor**

---

## 2. Introduction

Software development teams and student project groups often produce many documents during a project — proposals, SRS documents, meeting notes, task lists, and progress reports. However, extracting useful insights from these scattered documents manually is time-consuming and frequently neglected.

The AI Project Intelligence & Risk Advisor is designed to solve this problem by allowing teams to upload their project documents and receive automated insights through a Retrieval-Augmented Generation (RAG) pipeline. Milestone 1 focuses on building the foundational document ingestion and RAG query system.

---

## 3. Problem Statement

Project teams struggle with:
- Incomplete planning and missed deadlines
- Undetected risks and blockers
- Poor documentation practices
- Difficulty finding information across multiple documents
- No centralized way to query project knowledge

Existing documents contain valuable information, but there is no automated system to extract, index, and query this knowledge effectively.

---

## 4. Motivation

Manual review of project documents is:
- **Time-consuming**: Reading through dozens of pages to find one fact
- **Error-prone**: Important risks or deadlines can be overlooked
- **Not scalable**: As projects grow, document volume increases exponentially
- **Reactive**: Teams discover problems too late

An AI-powered system that ingests documents and allows natural language querying can transform how teams manage project knowledge.

---

## 5. Objectives

### Overall Project Objectives
- Build a unified project knowledge base using RAG
- Extract scope, deliverables, risks, and blockers automatically
- Forecast schedule challenges and score project health
- Provide a conversational project assistant and insights dashboard

### Milestone 1 Objectives
- Design system architecture and agent roles
- Implement document ingestion for PDF, DOCX, CSV, and TXT
- Build the RAG pipeline (chunking, embedding, vector storage, retrieval)
- Create a simple UI for document upload and RAG querying
- Establish extensible interfaces for future agent modules

---

## 6. Proposed Solution

The system accepts project documents in multiple formats, extracts and cleans text, splits it into searchable chunks, generates vector embeddings, and stores them in ChromaDB. Users can then ask natural language questions about their project, and the system retrieves relevant document chunks and generates grounded answers using an LLM.

**Milestone 1 Pipeline:**
```
Document → Ingestion → Text Extraction → Cleaning → Chunking → Embedding → Vector Store → Retrieval → RAG → Answer + Sources
```

---

## 7. Scope of Milestone 1

### In Scope
- System architecture design
- Document ingestion (PDF, DOCX, CSV, TXT)
- Text extraction and cleaning
- Configurable chunking
- Embedding generation (local model)
- ChromaDB vector storage with persistence
- Semantic retrieval with project filtering
- Basic RAG query pipeline
- Simple React frontend for upload and query
- API endpoints for projects, documents, and RAG
- Agent placeholders for future modules
- Sample data and testing

### Out of Scope (Future Milestones)
- Scope and Deliverable Extraction Agent
- Risk Detection Agent
- Delivery Forecasting Agent
- Blocker and Action Item Agent
- Documentation Generation Agent
- Project Health Scoring
- Advanced Dashboard
- Full Conversational Assistant

---

## 8. Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-01 | Upload single/multiple documents | Implemented |
| FR-02 | Support PDF file format | Implemented |
| FR-03 | Support DOCX file format | Implemented |
| FR-04 | Support CSV file format | Implemented |
| FR-05 | Support TXT file format | Implemented |
| FR-06 | Validate file type and size | Implemented |
| FR-07 | Extract text from documents | Implemented |
| FR-08 | Generate document chunks | Implemented |
| FR-09 | Generate embeddings | Implemented |
| FR-10 | Store in vector database | Implemented |
| FR-11 | Semantic retrieval | Implemented |
| FR-12 | RAG query with grounded answers | Implemented |
| FR-13 | Display source documents | Implemented |
| FR-14 | Create and list projects | Implemented |
| FR-15 | Delete documents | Implemented |

---

## 9. Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-01 | Modular architecture | Implemented |
| NFR-02 | Configurable via environment variables | Implemented |
| NFR-03 | Replaceable embedding provider | Implemented |
| NFR-04 | Replaceable LLM provider | Implemented |
| NFR-05 | Persistent vector storage | Implemented |
| NFR-06 | Safe filename handling | Implemented |
| NFR-07 | CORS support for frontend | Implemented |
| NFR-08 | Error handling for invalid files | Implemented |

---

## 10. System Architecture

The system uses a three-tier architecture:

1. **Frontend**: React + Vite + Tailwind CSS
2. **Backend**: Python FastAPI with modular services
3. **Storage**: ChromaDB (vectors) + JSON (metadata) + filesystem (uploads)

See `docs/architecture.md` for the detailed architecture diagram.

---

## 11. RAG Architecture

The RAG (Retrieval-Augmented Generation) pipeline works as follows:

1. **Indexing Phase**: Documents are parsed, chunked, embedded, and stored in ChromaDB
2. **Query Phase**: User question is embedded, similar chunks are retrieved, context is constructed, and an LLM generates a grounded answer

See `docs/rag-pipeline.md` for detailed pipeline design.

---

## 12. Document Ingestion Workflow

1. User selects a project and uploads files via the frontend
2. Frontend sends multipart form data to `POST /api/documents/upload`
3. Backend validates file type, size, and project existence
4. File is saved temporarily and a document record is created
5. Parser extracts text based on file type
6. Text is cleaned and split into chunks
7. Chunks are embedded using sentence-transformers
8. Embeddings and metadata are stored in ChromaDB
9. Document status is updated to "indexed" with chunk count

---

## 13. Supported Document Types

| Format | Library | Extraction Method |
|--------|---------|-------------------|
| PDF | PyMuPDF (fitz) | Page-by-page text extraction with page numbers |
| DOCX | python-docx | Paragraphs and tables |
| CSV | Python csv module | Row-to-text conversion with column labels |
| TXT | Python file I/O | Direct text reading with encoding fallback |

---

## 14. Text Extraction Process

- **PDF**: Opens with PyMuPDF, iterates pages, extracts text per page, preserves page_number metadata
- **DOCX**: Reads paragraphs and table rows, joins with separators
- **CSV**: Converts each row to "Column: Value" format for semantic searchability
- **TXT**: Reads with UTF-8 encoding, falls back to error replacement
- All extracted text passes through a cleaning function that normalizes whitespace and removes control characters

---

## 15. Chunking Strategy

- **Tool**: LangChain RecursiveCharacterTextSplitter
- **Default chunk size**: 800 characters
- **Default overlap**: 100 characters
- **Separators**: Paragraph breaks, line breaks, sentences, words
- **Metadata preserved**: document_id, project_id, page_number, chunk_index
- **Configurable**: via CHUNK_SIZE and CHUNK_OVERLAP environment variables

---

## 16. Embedding Generation

- **Model**: all-MiniLM-L6-v2 (Hugging Face sentence-transformers)
- **Dimensions**: 384
- **Execution**: Local (no API key required)
- **Interface**: Abstract EmbeddingProvider class allows swapping models
- **Methods**: embed_documents (batch) and embed_query (single)

---

## 17. Vector Database

- **Engine**: ChromaDB (persistent client)
- **Storage path**: backend/data/chroma/
- **Similarity metric**: Cosine
- **Collection**: project_documents
- **Metadata filtering**: By project_id for scoped retrieval
- **Persistence**: Survives application restarts

---

## 18. Semantic Retrieval

1. User query is converted to an embedding vector
2. ChromaDB performs cosine similarity search
3. Results are filtered by project_id
4. Top-k chunks (default 5) are returned with metadata and distance scores

---

## 19. Basic RAG Pipeline

1. Query received via `POST /api/rag/query`
2. Query embedded using the same model as documents
3. Top-k relevant chunks retrieved from ChromaDB
4. Context string constructed from chunk texts
5. LLM prompt includes system instructions (use only context, no hallucination)
6. LLM generates answer (OpenAI, Ollama, or mock provider)
7. Response includes answer, source documents, and retrieved chunk details

---

## 20. Data Model

Three primary entities: Project, Document, DocumentChunk. See `docs/data-model.md` for full schema.

---

## 21. API Design

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | Health check |
| POST | /api/projects | Create project |
| GET | /api/projects | List projects |
| GET | /api/projects/{id} | Get project |
| POST | /api/documents/upload | Upload documents |
| GET | /api/documents | List documents |
| DELETE | /api/documents/{id} | Delete document |
| POST | /api/rag/query | RAG query |

Interactive API docs available at `/docs` when backend is running.

---

## 22. Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite 6, Tailwind CSS 3, Axios |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| RAG | LangChain text splitters, sentence-transformers |
| Vector DB | ChromaDB 0.6 |
| PDF | PyMuPDF |
| DOCX | python-docx |
| CSV | Python csv module |
| LLM | OpenAI / Ollama / Mock (configurable) |
| Config | python-dotenv, pydantic-settings |

---

## 23. Project Structure

```
ai-project-intelligence-risk-advisor/
├── frontend/          # React UI
├── backend/           # FastAPI server
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── services/  # Business logic
│   │   ├── models/    # Data models
│   │   ├── agents/    # Future agent placeholders
│   │   └── core/      # Config and dependencies
│   └── data/          # Uploads, ChromaDB, metadata
├── docs/              # Documentation
├── sample_data/       # Test documents
└── README.md
```

---

## 24. Implementation Details

### Backend Services
- **ParserService**: Handles PDF, DOCX, CSV, TXT parsing
- **ChunkingService**: Configurable text splitting with metadata
- **EmbeddingService**: Pluggable embedding provider
- **VectorStoreService**: ChromaDB operations
- **IngestionService**: Orchestrates the full upload pipeline
- **RAGService**: Query embedding, retrieval, and LLM generation
- **MetadataStore**: JSON-backed project/document persistence

### Frontend Components
- **ProjectSection**: Create and select projects
- **UploadSection**: Multi-file upload with status display
- **RAGSection**: Query input, answer display, source citations

### Future Agent Placeholders
- ScopeAgent, RiskAgent, BlockerAgent, DocumentationAgent
- All inherit from BaseAgent abstract class
- Return "not_implemented" status in Milestone 1

---

## 25. Testing and Test Cases

| # | Test Case | Expected Result |
|---|-----------|-----------------|
| 1 | Upload PDF | Text extracted, chunks created, indexed |
| 2 | Upload DOCX | Paragraphs and tables extracted |
| 3 | Upload CSV | Rows converted to searchable text |
| 4 | Upload TXT | Plain text read and indexed |
| 5 | Upload multiple files | All files processed independently |
| 6 | RAG query after upload | Relevant answer with sources |
| 7 | Upload invalid file type | 400 error with message |
| 8 | Upload empty file | 400 error |
| 9 | Query without documents | "Could not find" message |
| 10 | Delete document | Removed from store and vector DB |
| 11 | Backend restart | Data persists in ChromaDB |
| 12 | Frontend/backend communication | API calls succeed via proxy |

---

## 26. Results

Milestone 1 successfully implements:
- Full document ingestion pipeline for 4 file formats
- Configurable chunking and local embedding generation
- Persistent ChromaDB vector storage
- Semantic retrieval with project-level filtering
- RAG query pipeline with source grounding
- Simple professional UI for upload and query
- RESTful API with 8 endpoints
- Extensible agent architecture for future milestones

The system was tested with sample project proposal (TXT), task list (CSV), and meeting notes (TXT) files. RAG queries return relevant answers with source document references.

---

## 27. Limitations

- LLM mock mode provides basic extractive answers (not generative)
- No user authentication or multi-user support
- Metadata stored in JSON files (not a production database)
- PDF extraction may miss complex layouts or scanned images
- No OCR support for image-based PDFs
- Single embedding model (no model comparison)
- No batch re-indexing or document update support
- Agent modules are placeholders only

---

## 28. Future Scope

**Milestone 2 planned features:**
- Scope and Deliverable Extraction Agent
- Risk Detection and Classification Agent
- Blocker and Action Item Identification Agent
- Documentation Generation Agent
- Project Health Scoring Module
- Enhanced dashboard with risk summaries
- Improved conversational assistant
- User authentication and multi-project management

---

## 29. Milestone 2 Plan

1. Implement Scope Agent using RAG + structured output
2. Implement Risk Agent with severity classification
3. Implement Blocker Agent for meeting notes and task lists
4. Build project health scoring algorithm
5. Create enhanced dashboard with charts and summaries
6. Add user authentication
7. Improve LLM integration with structured prompts
8. Add document versioning and update support

---

## 30. Conclusion

Milestone 1 establishes the foundational infrastructure for the AI Project Intelligence & Risk Advisor. The document ingestion pipeline, RAG query system, and extensible architecture provide a solid base for implementing intelligent agent modules in subsequent milestones. The system demonstrates that uploaded project documents can be automatically indexed and queried using natural language, validating the core concept of the project.

---

*Submitted as part of Milestone 1 — AI Project Intelligence & Risk Advisor*
