"""API exception handling — user-facing messages only, no stack traces."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from agents.exceptions import AgentAnalysisError, LLMError
from ingestion.exceptions import (
    DocumentProcessingError,
    EmptyDocumentError,
    EmptyFileError,
    EmbeddingError,
    FileTooLargeError,
    ParsingError,
    SearchError,
    UnsupportedFileError,
    VectorStoreError,
)
from ingestion.parsers import UNSUPPORTED_FORMATS_MESSAGE

logger = logging.getLogger("documents")

USER_MESSAGES = {
    UnsupportedFileError: UNSUPPORTED_FORMATS_MESSAGE,
    FileTooLargeError: "File is too large. Please upload a smaller document.",
    EmptyFileError: "The uploaded file is empty.",
    EmptyDocumentError: "No readable text was found in this document.",
    ParsingError: "Document processing failed. Please retry.",
    EmbeddingError: "Document processing failed. Please retry.",
    VectorStoreError: "Document processing failed. Please retry.",
    DocumentProcessingError: "Document processing failed. Please retry.",
    SearchError: "Unable to perform semantic search. Please try again.",
    LLMError: "AI analysis is temporarily unavailable. Please try again.",
    AgentAnalysisError: "Document analysis failed. Please retry.",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, AgentAnalysisError):
        logger.error("API error: %s", exc)
        message = str(exc).strip() or USER_MESSAGES[AgentAnalysisError]
        return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

    for exc_type, message in USER_MESSAGES.items():
        if isinstance(exc, exc_type):
            logger.error("API error: %s", exc)
            if isinstance(exc, SearchError):
                code = status.HTTP_500_INTERNAL_SERVER_ERROR
            elif isinstance(exc, LLMError):
                code = status.HTTP_503_SERVICE_UNAVAILABLE
            elif isinstance(
                exc,
                (
                    UnsupportedFileError,
                    FileTooLargeError,
                    EmptyDocumentError,
                    EmptyFileError,
                ),
            ):
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
