from django.db import models

from documents.models import Document
from projects.models import Project


class DocumentAnalysis(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="analyses"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="analyses"
    )
    content_hash = models.CharField(max_length=64)
    provider = models.CharField(max_length=32, default="grounded")
    requested_agents = models.JSONField(default=list)
    scope_result = models.JSONField(null=True, blank=True)
    risk_result = models.JSONField(null=True, blank=True)
    forecast_result = models.JSONField(null=True, blank=True)
    blockers_result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
