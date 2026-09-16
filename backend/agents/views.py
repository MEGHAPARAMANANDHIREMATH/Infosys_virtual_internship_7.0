from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from config.access import get_accessible_project
from documents.models import Document
from documents.serializers import DocumentSerializer

from agents.exceptions import AgentAnalysisError
from agents.orchestrator import ingest_uploaded_file, latest_analysis, normalize_agent_keys, run_intelligence


class ProjectIntelligenceView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, project_id):
        project = get_accessible_project(request, project_id)
        document_id = request.query_params.get("document_id")
        if not document_id:
            raise AgentAnalysisError("A document_id query parameter is required.")
        document = _get_document(project, document_id)
        payload = latest_analysis(document)
        if payload is None:
            return Response(
                {"error": "No analysis results are stored for this document yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(payload)

    def post(self, request, project_id):
        project = get_accessible_project(request, project_id)
        agent_keys = normalize_agent_keys(
            request.data.get("agents") or request.data.get("agent") or "all"
        )
        uploaded = request.FILES.get("file") or request.FILES.get("document")
        document_id = request.data.get("document_id")
        duplicate = False

        if uploaded is not None:
            document, duplicate = ingest_uploaded_file(project, uploaded)
        elif document_id:
            document = _get_document(project, document_id)
        else:
            raise AgentAnalysisError(
                "Upload a file or provide document_id for a processed document."
            )

        payload = run_intelligence(document, agent_keys)
        payload["duplicate"] = duplicate
        payload["document"] = DocumentSerializer(document).data
        return Response(payload, status=status.HTTP_200_OK)


def _get_document(project, document_id):
    try:
        return Document.objects.get(pk=document_id, project=project)
    except (Document.DoesNotExist, ValueError, TypeError):
        raise NotFound({"error": "Document not found in this project."})
