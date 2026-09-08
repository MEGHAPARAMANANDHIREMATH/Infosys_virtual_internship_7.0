# RAG pipeline (Milestone 1)

```
UPLOAD → VALIDATE → PARSE → CLEAN → CHUNK → EMBED → CHROMADB → PROCESSED
```

Search:

```
query → query embedding → ChromaDB similarity search filtered by project_id → top_k chunks
```

No LLM answer generation in this milestone.
