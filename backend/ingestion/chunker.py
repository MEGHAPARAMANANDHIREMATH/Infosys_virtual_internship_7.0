from dataclasses import dataclass
from typing import Optional

from django.conf import settings


@dataclass
class Chunk:
    content: str
    chunk_index: int
    page_number: Optional[int] = None
    section: Optional[str] = None
    document_id: Optional[int] = None
    project_id: Optional[int] = None

    @property
    def chunk_id(self) -> str:
        return f"{self.document_id}_{self.chunk_index}"


class Chunker:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = max(0, self.chunk_size // 5)
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def split_text(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        if len(text) <= self.chunk_size:
            return [text.strip()]
        return self._recursive_split(text.strip())

    def _recursive_split(self, text: str, separators: list[str] | None = None) -> list[str]:
        separators = list(separators if separators is not None else self.separators)
        if not separators:
            return self._window(text)

        separator = separators[0]
        remaining = separators[1:]
        pieces = text.split(separator) if separator else list(text)
        current = ""
        chunks: list[str] = []

        for piece in pieces:
            candidate = piece if not current else (
                current + (separator if separator else "") + piece
            )
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.extend(self._recursive_split(current, remaining) if remaining else self._window(current))
            current = piece
        if current:
            chunks.extend(self._recursive_split(current, remaining) if remaining else self._window(current))
        return [chunk for chunk in chunks if chunk.strip()]

    def _window(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks = []
        start = 0
        step = max(1, self.chunk_size - self.chunk_overlap)
        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += step
        return chunks

    def chunk_segments(
        self,
        segments,
        document_id: int,
        project_id: int,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        index = 0
        for segment in segments:
            parts = self.split_text(segment.text)
            for part in parts:
                chunks.append(
                    Chunk(
                        content=part,
                        chunk_index=index,
                        page_number=segment.page_number,
                        section=segment.section,
                        document_id=document_id,
                        project_id=project_id,
                    )
                )
                index += 1
        return chunks
