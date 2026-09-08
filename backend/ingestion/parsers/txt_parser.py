from pathlib import Path

from ingestion.exceptions import ParsingError
from ingestion.parsers.base import ParsedSegment


class TxtParser:
    def parse(self, file_path: Path) -> list[ParsedSegment]:
        try:
            text = file_path.read_bytes()
            decoded = None
            for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    decoded = text.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded is None:
                decoded = text.decode("utf-8", errors="replace")
            return [
                ParsedSegment(
                    text=decoded,
                    extra={"source_type": "txt"},
                )
            ]
        except Exception as exc:
            raise ParsingError(f"TXT parsing failed: {exc}") from exc
