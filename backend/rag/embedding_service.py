import logging
from typing import List

from django.conf import settings

from ingestion.exceptions import EmbeddingError

logger = logging.getLogger("rag")

_local_model = None


class LocalEmbeddingProvider:
    """Local sentence-transformers embeddings (no API key required)."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL

    def _model(self):
        global _local_model
        if _local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingError(
                    "Local embedding model is not installed. "
                    "Install sentence-transformers or configure OPENAI_API_KEY."
                ) from exc
            logger.info("Loading local embedding model: %s", self.model_name)
            _local_model = SentenceTransformer(self.model_name)
        return _local_model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            vectors = self._model().encode(texts, show_progress_bar=False)
            return vectors.tolist()
        except Exception as exc:
            raise EmbeddingError(f"Local embedding generation failed: {exc}") from exc

    def embed_query(self, text: str) -> List[float]:
        vectors = self.embed_documents([text])
        return vectors[0]


class OpenAIEmbeddingProvider:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise EmbeddingError(
                "OPENAI_API_KEY is not set. Use EMBEDDING_PROVIDER=local for development."
            )
        self.model_name = settings.OPENAI_EMBEDDING_MODEL

    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=settings.OPENAI_API_KEY)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            response = self._client().embeddings.create(model=self.model_name, input=texts)
            ordered = sorted(response.data, key=lambda item: item.index)
            return [item.embedding for item in ordered]
        except Exception as exc:
            raise EmbeddingError(f"OpenAI embedding generation failed: {exc}") from exc

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class EmbeddingService:
    def __init__(self, provider=None):
        self.provider = provider or build_embedding_provider()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        logger.info("Generating embeddings for %s chunk(s)", len(texts))
        return self.provider.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        logger.info("Generating query embedding")
        return self.provider.embed_query(text)


def build_embedding_provider():
    provider = (settings.EMBEDDING_PROVIDER or "local").lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    if provider in {"local", "sentence-transformers", "huggingface"}:
        return LocalEmbeddingProvider()
    raise EmbeddingError(
        f"Unknown EMBEDDING_PROVIDER '{provider}'. Use 'local' or 'openai'."
    )


_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service():
    global _embedding_service
    _embedding_service = None
