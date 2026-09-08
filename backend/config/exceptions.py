"""API exception handling — user-facing messages only, no stack traces."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from ingestion.exceptions import (
    DocumentProcessingError,
    EmptyDocumentError,
    EmbeddingError,
    FileTooLargeError,
    ParsingError,
    SearchError,
    UnsupportedFileError,
    VectorStoreError,
)

logger = logging.getLogger("documents")

USER_MESSAGES = {
    UnsupportedFileError: "Unsupported file format. Supported formats: PDF, DOCX, CSV, TXT.",
    FileTooLargeError: "File is too large. Please upload a smaller document.",
    EmptyDocumentError: "No readable text was found in this document.",
    ParsingError: "Document processing failed. Please retry.",
    EmbeddingError: "Document processing failed. Please retry.",
    VectorStoreError: "Document processing failed. Please retry.",
    DocumentProcessingError: "Document processing failed. Please retry.",
    SearchError: "Unable to perform semantic search. Please try again.",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    for exc_type, message in USER_MESSAGES.items():
        if isinstance(exc, exc_type):
            logger.error("API error: %s", exc)
            if isinstance(exc, SearchError):
                code = status.HTTP_500_INTERNAL_SERVER_ERROR
            elif isinstance(exc, (UnsupportedFileError, FileTooLargeError, EmptyDocumentError)):
                code = status.HTTP_400_BAD_REQUEST
            else:
                code = status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response({"error": message}, status=code)

    if response is not None:
        data = response.data
        if isinstance(data, dict) and "detail" in data and "error" not in data:
            detail = data["detail"]
            if isinstance(detail, list):
                detail = " ".join(str(item) for item in detail)
            data = {"error": str(detail)}
        elif isinstance(data, dict) and "error" not in data:
            data = {"error": "Request could not be processed.", "details": data}
        return Response(data, status=response.status_code)

    logger.exception("Unhandled API error: %s", exc)
    return Response(
        {"error": "An unexpected error occurred. Please try again."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
