from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from documents.models import Document, DocumentChunk, ProcessingStatus
from documents.test_helpers import PipelineTestCase, build_docx_bytes, write_simple_pdf
from ingestion.chunker import Chunker
from ingestion.cleaner import clean_segments
from ingestion.parsers import parse_file
from ingestion.parsers.base import ParsedSegment
from rag.vector_store import get_vector_store


class UploadApiTests(PipelineTestCase):
    def test_pdf_accepted(self):
        project = self.create_project("PDF Project")
        pdf_path = self.media_root / "sample.pdf"
        write_simple_pdf(pdf_path, ["Functional requirements include login and reporting."])
        response = self._upload(
            project["id"], "sample.pdf", pdf_path.read_bytes(), "application/pdf"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["processing_status"], ProcessingStatus.PROCESSED)
        self.assertEqual(response.data["file_type"], "pdf")

    def test_docx_accepted(self):
        project = self.create_project("DOCX Project")
        content = build_docx_bytes(["The main functional requirements are attendance tracking."])
        response = self._upload(
            project["id"],
            "srs.docx",
            content,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["processing_status"], ProcessingStatus.PROCESSED)

    def test_csv_accepted(self):
        project = self.create_project("CSV Project")
        csv_bytes = b"task,status\nBuild login,in progress\nWrite tests,done\n"
        response = self._upload(project["id"], "tasks.csv", csv_bytes, "text/csv")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["processing_status"], ProcessingStatus.PROCESSED)

    def test_txt_accepted(self):
        project = self.create_project("TXT Project")
        response = self._upload(
            project["id"],
            "notes.txt",
            b"Project kickoff notes mention reporting dashboards.",
            "text/plain",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["processing_status"], ProcessingStatus.PROCESSED)

    def test_unsupported_file_rejected(self):
        project = self.create_project("Bad File")
        response = self._upload(project["id"], "virus.exe", b"MZ", "application/octet-stream")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"],
            "Unsupported file format. Supported formats: PDF, DOCX, TXT, XLSX, CSV.",
        )

    def test_file_too_large_rejected(self):
        project = self.create_project("Large File")
        with override_settings(MAX_FILE_SIZE_MB=0):
            response = self._upload(
                project["id"],
                "notes.txt",
                b"too big for a zero megabyte limit",
                "text/plain",
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("too large", response.data["error"].lower())


class ParsingTests(PipelineTestCase):
    def test_pdf_extraction(self):
        path = self.media_root / "page.pdf"
        write_simple_pdf(path, ["Page one requirement text"])
        segments = parse_file(path, "pdf")
        self.assertTrue(segments)
        self.assertEqual(segments[0].page_number, 1)
        self.assertIn("requirement", segments[0].text.lower())

    def test_docx_extraction(self):
        path = self.media_root / "doc.docx"
        path.write_bytes(build_docx_bytes(["Heading One", "Body content about scope"]))
        segments = parse_file(path, "docx")
        combined = " ".join(segment.text for segment in segments)
        self.assertIn("Body content about scope", combined)

    def test_csv_extraction(self):
        path = self.media_root / "rows.csv"
        path.write_text("name,role\nAda,Lead\n", encoding="utf-8")
        segments = parse_file(path, "csv")
        self.assertTrue(segments)
        combined = "\n".join(segment.text for segment in segments)
        self.assertIn("Ada", combined)
        labeled = next(segment for segment in segments if segment.extra.get("row_number") == 1)
        self.assertIn("Ada", labeled.text)

    def test_xlsx_extraction(self):
        from openpyxl import Workbook

        path = self.media_root / "sheet.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Tasks"
        sheet.append(["Task", "Owner", "Status"])
        sheet.append(["Build login", "Ada", "Delayed"])
        workbook.save(path)
        segments = parse_file(path, "xlsx")
        combined = "\n".join(segment.text for segment in segments)
        self.assertIn("Build login", combined)
        self.assertIn("Ada", combined)
        self.assertIn("Task | Owner | Status", combined)


class ChunkingTests(PipelineTestCase):
    def test_text_becomes_multiple_chunks(self):
        chunker = Chunker(chunk_size=40, chunk_overlap=10)
        text = "Requirement one. " * 20
        parts = chunker.split_text(text)
        self.assertGreater(len(parts), 1)

    def test_chunk_metadata_exists(self):
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        segments = [
            ParsedSegment(text="Alpha section content " * 10, page_number=3, section="Intro")
        ]
        chunks = chunker.chunk_segments(segments, document_id=11, project_id=22)
        self.assertTrue(chunks)
        self.assertEqual(chunks[0].document_id, 11)
        self.assertEqual(chunks[0].project_id, 22)
        self.assertEqual(chunks[0].page_number, 3)
        self.assertEqual(chunks[0].section, "Intro")
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertTrue(chunks[0].chunk_id)


class VectorStoreAndSearchTests(PipelineTestCase):
    def _upload_text(self, project_id, filename, text):
        uploaded = SimpleUploadedFile(filename, text.encode("utf-8"), content_type="text/plain")
        response = self.client.post(
            f"/api/projects/{project_id}/documents/",
            {"file": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_chunks_indexed_and_project_metadata_stored(self):
        project = self.create_project("Index Project")
        doc = self._upload_text(
            project["id"],
            "alpha.txt",
            "UniqueAlphaToken describes campus attendance tracking requirements.",
        )
        self.assertEqual(DocumentChunk.objects.filter(document_id=doc["id"]).count(), 1)
        stored = get_vector_store().similarity_search(
            query_embedding=__import__(
                "rag.embedding_service", fromlist=["get_embedding_service"]
            ).get_embedding_service().embed_query("UniqueAlphaToken attendance"),
            project_id=project["id"],
            top_k=3,
        )
        self.assertTrue(stored)
        self.assertEqual(str(stored[0]["project_id"]), str(project["id"]))
        self.assertEqual(stored[0]["file_name"], "alpha.txt")

    def test_semantic_search_returns_results(self):
        project = self.create_project("Search Project")
        self._upload_text(
            project["id"],
            "requirements.txt",
            "The main functional requirements are student login and QR attendance.",
        )
        response = self.client.post(
            f"/api/projects/{project['id']}/search/",
            {"query": "What are the main functional requirements?", "top_k": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["query"], "What are the main functional requirements?")
        self.assertTrue(response.data["results"])
        result = response.data["results"][0]
        self.assertEqual(result["file_name"], "requirements.txt")
        self.assertIn("content", result)
        self.assertIn("score", result)

    def test_project_filtering_and_isolation(self):
        project_a = self.create_project("Project A")
        project_b = self.create_project("Project B")
        self._upload_text(
            project_a["id"],
            "alpha.txt",
            "ProjectASecretToken is only in the alpha knowledge base about library hours.",
        )
        self._upload_text(
            project_b["id"],
            "beta.txt",
            "ProjectBSecretToken is only in the beta knowledge base about cafeteria menus.",
        )
        response = self.client.post(
            f"/api/projects/{project_a['id']}/search/",
            {"query": "ProjectBSecretToken cafeteria menus", "top_k": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        for item in response.data["results"]:
            self.assertNotEqual(item.get("file_name"), "beta.txt")
            self.assertNotIn("ProjectBSecretToken", item["content"])
            self.assertEqual(item["document_id"], Document.objects.get(file_name="alpha.txt").id)

    def test_empty_file_rejected(self):
        project = self.create_project("Empty bytes")
        response = self._upload(project["id"], "empty.txt", b"", "text/plain")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "The uploaded file is empty.")

    def test_duplicate_upload_reused(self):
        project = self.create_project("Dupes")
        payload = b"Unique duplicate token for campus reporting."
        first = self._upload(project["id"], "notes.txt", payload, "text/plain")
        self.assertEqual(first.status_code, 201, first.data)
        second = self._upload(project["id"], "notes.txt", payload, "text/plain")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertTrue(second.data.get("duplicate"))
        self.assertEqual(second.data["id"], first.data["id"])

    def test_xlsx_accepted(self):
        from io import BytesIO

        from openpyxl import Workbook

        project = self.create_project("XLSX Project")
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Task", "Owner"])
        sheet.append(["Build login", "Ada"])
        buffer = BytesIO()
        workbook.save(buffer)
        response = self._upload(
            project["id"],
            "tasks.xlsx",
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["processing_status"], ProcessingStatus.PROCESSED)
        self.assertEqual(response.data["file_type"], "xlsx")


class WhitespaceDocumentTests(PipelineTestCase):
    def test_empty_document_fails_clearly(self):
        project = self.create_project("Empty")
        uploaded = SimpleUploadedFile("empty.txt", b"   \n\n  ", content_type="text/plain")
        response = self.client.post(
            f"/api/projects/{project['id']}/documents/",
            {"file": uploaded},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"],
            "No readable text was found in this document.",
        )
        document = Document.objects.get(file_name="empty.txt")
        self.assertEqual(document.processing_status, ProcessingStatus.FAILED)
