from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("documents", "0002_document_file_hash"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content_hash", models.CharField(max_length=64)),
                ("provider", models.CharField(default="grounded", max_length=32)),
                ("requested_agents", models.JSONField(default=list)),
                ("scope_result", models.JSONField(blank=True, null=True)),
                ("risk_result", models.JSONField(blank=True, null=True)),
                ("forecast_result", models.JSONField(blank=True, null=True)),
                ("blockers_result", models.JSONField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to="documents.document",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analyses",
                        to="projects.project",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
