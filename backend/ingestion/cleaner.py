import re

from ingestion.parsers.base import ParsedSegment

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
MULTI_SPACE = re.compile(r"[ \t]+")
MULTI_NEWLINE = re.compile(r"\n{3,}")
PDF_ARTIFACTS = re.compile(r"(?:\uf0b7|\uf0a7|\u2022)")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = CONTROL_CHARS.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = PDF_ARTIFACTS.sub("-", text)
    text = MULTI_SPACE.sub(" ", text)
    text = MULTI_NEWLINE.sub("\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def is_meaningful(text: str) -> bool:
    if not text or not text.strip():
        return False
    letters = sum(1 for ch in text if ch.isalnum())
    return letters >= 3


def clean_segments(segments: list[ParsedSegment]) -> list[ParsedSegment]:
    cleaned: list[ParsedSegment] = []
    for segment in segments:
        text = clean_text(segment.text)
        if not is_meaningful(text):
            continue
        cleaned.append(
            ParsedSegment(
                text=text,
                page_number=segment.page_number,
                section=segment.section,
                extra=segment.extra,
            )
        )
    return cleaned
