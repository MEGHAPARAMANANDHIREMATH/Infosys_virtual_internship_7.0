"""Shared helpers for Milestone 1 tests."""

import os
import tempfile
from io import BytesIO
from pathlib import Path

from django.test import override_settings
from docx import Document as DocxDocument
from rest_framework.test import APITestCase

from rag.embedding_service import reset_embedding_service
from rag.vector_store import reset_vector_store

_counter = 0


def _next_collection_name():
    global _counter
    _counter += 1
    return f"test_{os.getpid()}_{_counter}"


def write_simple_pdf(path: Path, lines: list[str]) -> None:
    escaped_lines = []
    for line in lines:
        escaped = (
            line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        escaped_lines.append(escaped)
    text_ops = "BT /F1 12 Tf 72 720 Td\n"
    for escaped in escaped_lines:
        text_ops += f"({escaped}) Tj\n0 -18 Td\n"
    text_ops += "ET\n"
    stream = text_ops.encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(bytes(pdf))


def build_docx_bytes(paragraphs: list[str]) -> bytes:
    document = DocxDocument()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class PipelineTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        self._temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self._temp_dir.name)
        self.media_root = root / "media"
        self.chroma_dir = root / "chroma"
        self.media_root.mkdir()
        self.chroma_dir.mkdir()
        self._settings = override_settings(
            MEDIA_ROOT=self.media_root,
            CHROMA_PERSIST_DIR=self.chroma_dir,
            CHROMA_COLLECTION_NAME=_next_collection_name(),
            ENFORCE_PROJECT_ACCESS=False,
            EMBEDDING_PROVIDER="local",
            LLM_PROVIDER="grounded",
            OPENAI_API_KEY="",
        )
        self._settings.enable()
        reset_vector_store()
        reset_embedding_service()

    def tearDown(self):
        reset_vector_store()
        self._settings.disable()
        self._temp_dir.cleanup()
        super().tearDown()

    def _upload(self, project_id, filename, content, content_type):
        from django.core.files.uploadedfile import SimpleUploadedFile

        uploaded = SimpleUploadedFile(filename, content, content_type=content_type)
        return self.client.post(
            f"/api/projects/{project_id}/documents/",
            {"file": uploaded},
            format="multipart",
        )

    def create_project(self, name="Alpha", **extra):
        payload = {
            "name": name,
            "description": extra.get("description", f"{name} description"),
            "start_date": extra.get("start_date", "2026-01-01"),
            "end_date": extra.get("end_date", "2026-12-31"),
            "status": extra.get("status", "ACTIVE"),
        }
        response = self.client.post("/api/projects/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data
