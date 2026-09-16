import logging
from pathlib import Path

from django.conf import settings
from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from config.access import get_accessible_project
from documents.models import Document, ProcessingStatus
from documents.serializers import DocumentSerializer
from documents.services import delete_document_artifacts, hash_uploaded_file, store_uploaded_file
from ingestion.exceptions import EmptyDocumentError, EmptyFileError, FileTooLargeError, UnsupportedFileError
from ingestion.parsers import UNSUPPORTED_FORMATS_MESSAGE
from ingestion.processor import process_document

logger = logging.getLogger("documents")

UNSUPPORTED_MESSAGE = UNSUPPORTED_FORMATS_MESSAGE


def _extension_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


class ProjectDocumentListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, project_id):
        project = get_accessible_project(request, project_id)
        documents = project.documents.annotate(chunk_count=Count("chunks"))
        return Response(DocumentSerializer(documents, many=True).data)

    def post(self, request, project_id):
        project = get_accessible_project(request, project_id)
        uploaded = request.FILES.get("file") or request.FILES.get("document")
        if uploaded is None:
            return Response(
                {"error": "A file is required. Upload using the 'file' form field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension = _extension_of(uploaded.name)
        content_type = (uploaded.content_type or "").lower()
        allowed_types = {
            "pdf": {"application/pdf"},
            "docx": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/octet-stream",
            },
            "csv": {"text/csv", "application/vnd.ms-excel", "application/octet-stream", "text/plain"},
            "txt": {"text/plain", "application/octet-stream"},
            "xlsx": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/octet-stream",
            },
        }
        if extension not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileError(UNSUPPORTED_MESSAGE)
        if content_type and content_type not in allowed_types[extension] and content_type != "application/octet-stream":
            # Some browsers send generic types; extension remains the source of truth.
            if (
                not content_type.startswith("text/")
                and "pdf" not in content_type
                and "word" not in content_type
                and "spreadsheet" not in content_type
                and "excel" not in content_type
            ):
                raise UnsupportedFileError(UNSUPPORTED_MESSAGE)

        if uploaded.size == 0:
            raise EmptyFileError("The uploaded file is empty.")

        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if uploaded.size > max_bytes:
            raise FileTooLargeError(
                f"File is too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB."
            )

        file_hash = hash_uploaded_file(uploaded)
        existing = (
            Document.objects.filter(
                project=project,
                file_hash=file_hash,
                processing_status=ProcessingStatus.PROCESSED,
            )
            .order_by("-uploaded_at")
            .first()
        )
        if existing:
            logger.info(
                "Duplicate upload project_id=%s file=%s hash=%s existing_id=%s",
                project.id,
                uploaded.name,
                file_hash,
                existing.id,
            )
            payload = DocumentSerializer(existing).data
            payload["duplicate"] = True
            payload["message"] = (
                "This document was already uploaded. Reusing the existing processed file."
            )
            return Response(payload, status=status.HTTP_200_OK)

        logger.info(
            "Document upload project_id=%s file=%s size=%s",
            project.id,
            uploaded.name,
            uploaded.size,
        )
        stored_path = store_uploaded_file(project.id, uploaded)
        document = Document.objects.create(
            project=project,
            file_name=uploaded.name,
            file_type=extension,
            file_path=str(stored_path),
            processing_status="UPLOADED",
            file_hash=file_hash,
        )
        process_document(document)
        document.refresh_from_db()
        payload = DocumentSerializer(document).data
        payload["duplicate"] = False
        return Response(payload, status=status.HTTP_201_CREATED)


class DocumentDeleteView(APIView):
    def delete(self, request, pk):
        try:
            document = Document.objects.select_related("project").get(pk=pk)
        except Document.DoesNotExist:
            raise NotFound({"error": "Document not found."})
        get_accessible_project(request, document.project_id)
        delete_document_artifacts(document)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
