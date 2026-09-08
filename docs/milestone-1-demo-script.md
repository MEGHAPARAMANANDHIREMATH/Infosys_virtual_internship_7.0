# Milestone 1 — Explanation & Demo Script

Read this naturally. Replace `[Your Name]` and greet according to the session.

App URL: http://localhost:5173/

---

## 1. Opening (about 45 seconds)

Good morning / good afternoon. My name is [Your Name]. Today I am presenting **Milestone 1** of **AI Project Intelligence and Risk Advisor**.

This project helps student teams and software teams use their own project documents as a searchable knowledge base. Teams usually have PDFs, Word files, CSV task lists, and notes, but finding one fact means opening every file by hand.

Milestone 1 does **not** detect risks or generate reports yet. It builds the foundation: **upload documents, extract text, clean it, chunk it, create embeddings, store them in ChromaDB, and run semantic search inside one project**.

---

## 2. Problem (about 30 seconds)

During a project we create proposals, SRS documents, meeting notes, and task lists. The information is scattered.

A question like “What are the main functional requirements?” should not require reading every file. This milestone turns those files into a **project-scoped search index** so we can retrieve the relevant paragraphs, with the source filename and a similarity score.

---

## 3. What Milestone 1 includes vs later work (about 40 seconds)

In this milestone I implemented:

- Project create, list, open, and update
- Document upload for **PDF, DOCX, CSV, and TXT**
- A processing pipeline: validate, parse, clean, chunk, embed, index
- **ChromaDB** vector storage with **project_id** on every chunk
- Semantic search that returns chunks, not an LLM-written answer
- A React UI and a Django REST API
- MySQL-compatible database settings, with SQLite for local development

**Not in Milestone 1:** risk agent, scope agent, blocker agent, forecasting, documentation generator, health score, full dashboard, and conversational AI. Those come later. This demo proves **retrieval** works.

---

## 4. Architecture (about 1 minute)

The flow is:

**React frontend → REST API → Django REST Framework.**

Django stores project and document metadata in the database. Uploaded files are saved on disk.

The RAG side is modular, not one giant function:

1. **Parsers** — PDF page by page with PyPDF, DOCX paragraphs and tables, CSV rows with Pandas, TXT with encoding handling  
2. **Cleaner** — whitespace and extraction noise, without destroying headings or table meaning  
3. **Chunker** — overlapping chunks, size and overlap from environment variables  
4. **Embedding service** — real vectors. Default is local **sentence-transformers** (`all-MiniLM-L6-v2`). OpenAI is optional via environment variables. No API keys in code.  
5. **ChromaDB** — stores the embedding, chunk text, document ID, project ID, chunk ID, page number, and filename  

Search always filters by **project_id**. A search in Project A cannot return Project B chunks. That isolation is a core requirement.

---

## 5. RAG in simple words (about 45 seconds)

**Retrieval** here means: convert the user question into an embedding, find the nearest document chunks in ChromaDB, and show those chunks.

I am **not** calling an LLM to write a summary in this milestone. If I generated an answer without retrieval, it could hallucinate. Milestone 1 proves we can find the right **source text**. Later milestones can put those chunks into an LLM.

**Embeddings** are number lists that capture meaning. Similar sentences sit close together, even if the wording is different.

**Chunking** is needed because a whole document is too large and mixed. Smaller overlapping pieces retrieve more precisely.

---

## 6. Live demo (follow the UI)

### Open the app

Open **http://localhost:5173/**.

The header should show the backend as **connected**. If it is red, Django is not running on port 8000.

### Create a project

Click through **Create Project**.

Say: “I will create a project. I enter the name, description, start date, expected completion date, and status.”

Example:

- Name: Smart Campus Management System  
- Description: Student records, attendance, and scheduling  
- Status: ACTIVE  

Then click **Create Project**, then **Open Project**.

### Upload four file types

In **Document Upload**, drag and drop or click to select. Sample files are in `sample_data/`.

Say while uploading:

1. **PDF** — “Text is extracted page by page, and page numbers are kept.”  
2. **DOCX** — “Paragraphs and tables are extracted.”  
3. **CSV** — “Each row becomes searchable text with column names.”  
4. **TXT** — “Plain text is read with encoding handling.”

Point at the table: filename, type, processing status **PROCESSED**, and chunk count.

If a file has no readable text, status becomes **FAILED** with: “No readable text was found in this document.”  
If the type is wrong, the API returns: “Unsupported file format. Supported formats: PDF, DOCX, CSV, TXT.”

### Explain the pipeline once (10 seconds)

“For each file the backend validated the type and size, parsed it, cleaned the text, split it into chunks, generated embeddings, and indexed them in ChromaDB. Status PROCESSED means that pipeline finished.”

### Semantic search

In **Semantic Search**, use:

**What are the main project requirements?**

Click **Search**.

Point to each result:

- **Source document** (filename)  
- **Chunk text**  
- **Page number** if it is a PDF  
- **Similarity score**

Say: “This is retrieval only. I am showing the relevant chunks, not a generated essay.”

Optional second query: “What tasks are in progress?” (uses the CSV).

### Project isolation (if time)

Create **Project B**, upload a different file (for example `meeting_notes.txt`). Go back to Project A and search for something unique to B. Explain: “No Project B chunks appear, because every vector is stored with project_id and search is filtered.”

---

## 7. Short viva answers

**What is Milestone 1?**  
Document ingestion plus vector search. No agents, no LLM answers.

**Stack?**  
React, Django, Django REST Framework, MySQL or SQLite, PyPDF, python-docx, Pandas, ChromaDB, sentence-transformers.

**Why not FastAPI?**  
The required stack for this milestone is Django REST Framework.

**Why ChromaDB?**  
It stores embeddings locally, supports metadata filters, and does not need a separate server.

**How do you stop mixing projects?**  
`where: { project_id: ... }` on every search. Tests create Project A and Project B and assert B never appears in A.

**Why local embeddings?**  
They are real embeddings without putting API keys in the repo. First run may download the model.

**Chunk size?**  
`CHUNK_SIZE` and `CHUNK_OVERLAP` in `.env`, default 800 and 100.

---

## 8. Closing (about 20 seconds)

In Milestone 1 I built a working pipeline: documents go in, they are parsed and indexed, and semantic search returns the right chunks for that project only.

The next milestones can add risk detection, forecasting, and a conversational assistant **on top of this retrieval layer**.

Thank you. I am happy to take questions.
