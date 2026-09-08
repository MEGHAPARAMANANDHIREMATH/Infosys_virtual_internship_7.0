import logging
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from django.conf import settings

from ingestion.chunker import Chunk
from ingestion.exceptions import VectorStoreError

logger = logging.getLogger("rag")

_client = None
_collection = None
_persist_dir = None


def _get_collection():
    global _client, _collection, _persist_dir
    persist_dir = str(settings.CHROMA_PERSIST_DIR)
    cache_key = f"{persist_dir}::{settings.CHROMA_COLLECTION_NAME}"
    if _collection is not None and _persist_dir == cache_key:
        return _collection
    try:
        chroma_settings = ChromaSettings(anonymized_telemetry=False)
        if getattr(settings, "TESTING", False):
            _client = chromadb.EphemeralClient(settings=chroma_settings)
        else:
            settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(
                path=persist_dir,
                settings=chroma_settings,
            )
        _collection = _client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        _persist_dir = cache_key
        return _collection
    except Exception as exc:
        raise VectorStoreError(f"ChromaDB initialization failed: {exc}") from exc


def reset_vector_store():
    global _client, _collection, _persist_dir, _vector_store
    _client = None
    _collection = None
    _persist_dir = None
    _vector_store = None


class VectorStoreService:
    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        file_name: str,
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Embedding count does not match chunk count.")
        collection = _get_collection()
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = []
        for chunk in chunks:
            metadata: dict[str, Any] = {
                "document_id": str(chunk.document_id),
                "project_id": str(chunk.project_id),
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "file_name": file_name,
            }
            if chunk.page_number is not None:
                metadata["page_number"] = int(chunk.page_number)
            if chunk.section:
                metadata["section"] = chunk.section
            metadatas.append(metadata)
        try:
            logger.info("Indexing %s chunk(s) in ChromaDB", len(chunks))
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise VectorStoreError(f"ChromaDB indexing failed: {exc}") from exc

    def similarity_search(
        self,
        query_embedding: list[float],
        project_id: int,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        collection = _get_collection()
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max(1, top_k),
                where={"project_id": str(project_id)},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"ChromaDB search failed: {exc}") from exc

        items: list[dict[str, Any]] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return items

        for i, chunk_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            distance = results["distances"][0][i] if results.get("distances") else None
            score = None
            if distance is not None:
                score = round(max(0.0, 1.0 - float(distance)), 4)
            page_number = metadata.get("page_number")
            items.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": metadata.get("document_id"),
                    "file_name": metadata.get("file_name"),
                    "content": results["documents"][0][i] if results.get("documents") else "",
                    "page_number": int(page_number) if page_number not in (None, "") else None,
                    "score": score,
                    "project_id": metadata.get("project_id"),
                }
            )
        return items

    def delete_by_document(self, document_id: int) -> None:
        try:
            _get_collection().delete(where={"document_id": str(document_id)})
        except Exception as exc:
            logger.warning("ChromaDB document delete failed: %s", exc)

    def delete_by_project(self, project_id: int) -> None:
        try:
            _get_collection().delete(where={"project_id": str(project_id)})
        except Exception as exc:
            logger.warning("ChromaDB project delete failed: %s", exc)


_vector_store: Optional[VectorStoreService] = None


def get_vector_store() -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
