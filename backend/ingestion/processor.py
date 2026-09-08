import logging
from pathlib import Path

from documents.models import Document, DocumentChunk, ProcessingStatus
from ingestion.chunker import Chunker
from ingestion.cleaner import clean_segments
from ingestion.exceptions import (
    DocumentProcessingError,
    EmptyDocumentError,
    EmbeddingError,
    ParsingError,
    VectorStoreError,
)
from ingestion.parsers import parse_file
from rag.embedding_service import get_embedding_service
from rag.vector_store import get_vector_store

logger = logging.getLogger("ingestion")


def process_document(document: Document) -> Document:
    logger.info(
        "Processing start document_id=%s file=%s type=%s",
        document.id,
        document.file_name,
        document.file_type,
    )
    document.processing_status = ProcessingStatus.PROCESSING
    document.error_message = ""
    document.save(update_fields=["processing_status", "error_message"])

    try:
        logger.info("Parsing start document_id=%s", document.id)
        segments = parse_file(Path(document.file_path), document.file_type)
        logger.info("Parsing end document_id=%s segments=%s", document.id, len(segments))

        cleaned = clean_segments(segments)
        if not cleaned:
            raise EmptyDocumentError("No readable text was found in this document.")

        chunks = Chunker().chunk_segments(
            cleaned,
            document_id=document.id,
            project_id=document.project_id,
        )
        logger.info("Chunk count document_id=%s chunks=%s", document.id, len(chunks))
        if not chunks:
            raise EmptyDocumentError("No readable text was found in this document.")

        embeddings = get_embedding_service().embed_documents(
            [chunk.content for chunk in chunks]
        )
        get_vector_store().add_chunks(chunks, embeddings, file_name=document.file_name)

        DocumentChunk.objects.filter(document=document).delete()
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    document=document,
                    project=document.project,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section=chunk.section or "",
                    embedding_reference=chunk.chunk_id,
                )
                for chunk in chunks
            ]
        )

        document.processing_status = ProcessingStatus.PROCESSED
        document.error_message = ""
        document.save(update_fields=["processing_status", "error_message"])
        logger.info("Processing complete document_id=%s", document.id)
        return document
    except EmptyDocumentError as exc:
        _mark_failed(document, str(exc))
        raise
    except (ParsingError, EmbeddingError, VectorStoreError, DocumentProcessingError) as exc:
        logger.exception("Processing failed document_id=%s error=%s", document.id, exc)
        _mark_failed(document, "Document processing failed. Please retry.")
        raise
    except Exception as exc:
        logger.exception("Processing failed document_id=%s error=%s", document.id, exc)
        _mark_failed(document, "Document processing failed. Please retry.")
        raise DocumentProcessingError(str(exc)) from exc


def _mark_failed(document: Document, user_message: str) -> None:
    document.processing_status = ProcessingStatus.FAILED
    document.error_message = user_message
    document.save(update_fields=["processing_status", "error_message"])
