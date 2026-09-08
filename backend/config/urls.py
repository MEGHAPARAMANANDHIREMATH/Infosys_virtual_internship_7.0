from django.urls import path

from documents.views import DocumentDeleteView, ProjectDocumentListCreateView
from projects.views import HealthView, ProjectDetailView, ProjectListCreateView
from rag.views import ProjectSearchView

urlpatterns = [
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("api/projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "api/projects/<int:project_id>/documents/",
        ProjectDocumentListCreateView.as_view(),
        name="project-documents",
    ),
    path(
        "api/projects/<int:project_id>/search/",
        ProjectSearchView.as_view(),
        name="project-search",
    ),
    path("api/documents/<int:pk>/", DocumentDeleteView.as_view(), name="document-delete"),
]
