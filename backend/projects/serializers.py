from rest_framework import serializers

from projects.models import Project, ProjectStatus


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "start_date",
            "end_date",
            "status",
            "created_by",
            "created_at",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def validate_status(self, value):
        allowed = {choice[0] for choice in ProjectStatus.choices}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid status. Allowed: {', '.join(sorted(allowed))}."
            )
        return value

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if self.instance:
            start_date = attrs.get("start_date", self.instance.start_date)
            end_date = attrs.get("end_date", self.instance.end_date)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "Expected completion date cannot be before the start date."}
            )
        return attrs
