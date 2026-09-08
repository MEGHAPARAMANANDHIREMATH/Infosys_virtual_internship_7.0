from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.access import get_accessible_project
from rag.retrieval import semantic_search


class SearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, allow_blank=False)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)


class ProjectSearchView(APIView):
    def post(self, request, project_id):
        project = get_accessible_project(request, project_id)
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = semantic_search(
            project_id=project.id,
            query=serializer.validated_data["query"],
            top_k=serializer.validated_data["top_k"],
        )
        payload = []
        for item in results:
            document_id = item.get("document_id")
            payload.append(
                {
                    "document_id": int(document_id) if str(document_id).isdigit() else document_id,
                    "file_name": item.get("file_name"),
                    "chunk_id": item.get("chunk_id"),
                    "content": item.get("content"),
                    "page_number": item.get("page_number"),
                    "score": item.get("score"),
                }
            )
        return Response(
            {
                "query": serializer.validated_data["query"],
                "results": payload,
            },
            status=status.HTTP_200_OK,
        )
