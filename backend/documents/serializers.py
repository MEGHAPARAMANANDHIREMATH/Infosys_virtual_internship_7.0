from rest_framework import serializers

from documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True)
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "project_id",
            "file_name",
            "file_type",
            "file_path",
            "processing_status",
            "error_message",
            "uploaded_at",
            "chunk_count",
        ]
        read_only_fields = fields

    def get_chunk_count(self, obj):
        if hasattr(obj, "chunk_count"):
            return obj.chunk_count
        return obj.chunks.count()
