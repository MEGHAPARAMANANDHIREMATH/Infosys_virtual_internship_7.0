from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.access import get_accessible_project, get_actor_id
from projects.models import Project
from projects.serializers import ProjectSerializer


class HealthView(APIView):
    def get(self, request):
        return Response({"status": "ok", "milestone": 2})


class ProjectListCreateView(APIView):
    def get(self, request):
        queryset = Project.objects.all()
        from django.conf import settings

        if settings.ENFORCE_PROJECT_ACCESS:
            queryset = queryset.filter(created_by=get_actor_id(request))
        serializer = ProjectSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(created_by=get_actor_id(request))
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    def get(self, request, pk):
        project = get_accessible_project(request, pk)
        return Response(ProjectSerializer(project).data)

    def put(self, request, pk):
        project = get_accessible_project(request, pk)
        serializer = ProjectSerializer(project, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        project = get_accessible_project(request, pk)
        from documents.services import delete_project_artifacts

        delete_project_artifacts(project)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
