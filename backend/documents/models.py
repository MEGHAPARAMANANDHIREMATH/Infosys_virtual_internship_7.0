from django.db import models

from projects.models import Project


class ProcessingStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Uploaded"
    PROCESSING = "PROCESSING", "Processing"
    PROCESSED = "PROCESSED", "Processed"
    FAILED = "FAILED", "Failed"


class Document(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="documents"
    )
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=16)
    file_path = models.CharField(max_length=1024)
    processing_status = models.CharField(
        max_length=16,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
    )
    error_message = models.TextField(blank=True, default="")
    file_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file_name


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="chunks"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="chunks"
    )
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section = models.CharField(max_length=255, blank=True, default="")
    embedding_reference = models.CharField(max_length=255)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        unique_together = ("document", "chunk_index")
