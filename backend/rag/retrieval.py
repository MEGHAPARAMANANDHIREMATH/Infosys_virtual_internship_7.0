import logging

from ingestion.exceptions import SearchError
from rag.embedding_service import get_embedding_service
from rag.vector_store import get_vector_store

logger = logging.getLogger("rag")


def semantic_search(project_id: int, query: str, top_k: int = 5) -> list[dict]:
    logger.info("Search request project_id=%s top_k=%s", project_id, top_k)
    try:
        embedding = get_embedding_service().embed_query(query)
        results = get_vector_store().similarity_search(
            query_embedding=embedding,
            project_id=project_id,
            top_k=top_k,
        )
        isolated = [
            item for item in results if str(item.get("project_id")) == str(project_id)
        ]
        logger.info("Search result count=%s", len(isolated))
        return isolated
    except SearchError:
        raise
    except Exception as exc:
        logger.exception("Semantic search failed")
        raise SearchError(f"Search failed: {exc}") from exc
