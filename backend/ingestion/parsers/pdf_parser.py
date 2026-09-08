from pathlib import Path

from pypdf import PdfReader

from ingestion.exceptions import ParsingError
from ingestion.parsers.base import ParsedSegment


class PdfParser:
    def parse(self, file_path: Path) -> list[ParsedSegment]:
        try:
            reader = PdfReader(str(file_path))
            segments: list[ParsedSegment] = []
            for index, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                segments.append(
                    ParsedSegment(
                        text=text,
                        page_number=index + 1,
                        extra={"source_type": "pdf"},
                    )
                )
            return segments
        except Exception as exc:
            raise ParsingError(f"PDF parsing failed: {exc}") from exc
