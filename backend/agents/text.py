from pathlib import Path

from ingestion.cleaner import clean_segments, clean_text
from ingestion.parsers import parse_file


def extract_document_text(file_path: str, file_type: str) -> str:
    segments = parse_file(Path(file_path), file_type)
    cleaned = clean_segments(segments)
    parts = []
    for segment in cleaned:
        prefix = []
        if segment.page_number:
            prefix.append(f"[Page {segment.page_number}]")
        if segment.section:
            prefix.append(f"[{segment.section}]")
        heading = " ".join(prefix)
        if heading:
            parts.append(f"{heading}\n{segment.text}")
        else:
            parts.append(segment.text)
    return clean_text("\n\n".join(parts))
