"""Minimal access helpers so authentication can be added later."""

from rest_framework.exceptions import NotFound, PermissionDenied

from django.conf import settings

from projects.models import Project


def get_actor_id(request) -> str:
    header = request.headers.get("X-User-Id")
    if header and header.strip():
        return header.strip()
    return "anonymous"


def get_accessible_project(request, project_id: int) -> Project:
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        raise NotFound("Project not found.")

    if settings.ENFORCE_PROJECT_ACCESS:
        actor = get_actor_id(request)
        if project.created_by and project.created_by != actor:
            raise PermissionDenied("You do not have access to this project.")
    return project
