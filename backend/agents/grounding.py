import re
import unicodedata

from agents.constants import NOT_SPECIFIED

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[“”\"'`]+")


def normalize(text: str) -> str:
    if not text:
        return ""
    value = unicodedata.normalize("NFKC", str(text))
    value = _PUNCT.sub("", value)
    value = value.replace("–", "-").replace("—", "-")
    return _WS.sub(" ", value).strip().lower()


def in_document(value: str, document_text: str) -> bool:
    if not value or normalize(value) == normalize(NOT_SPECIFIED):
        return True
    haystack = normalize(document_text)
    needle = normalize(value)
    if not needle:
        return False
    if needle in haystack:
        return True
    tokens = [token for token in re.split(r"[^\w]+", needle) if len(token) > 2]
    if len(tokens) >= 2:
        return all(token in haystack for token in tokens[:4])
    return False


def ground_value(value, document_text: str) -> str:
    if value is None:
        return NOT_SPECIFIED
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "n/a", "na", "unknown", "-"}:
        return NOT_SPECIFIED
    if normalize(text) == normalize(NOT_SPECIFIED):
        return NOT_SPECIFIED
    if in_document(text, document_text):
        return text
    return NOT_SPECIFIED


def ground_evidence(value, document_text: str, fallback_query: str = "") -> str:
    text = str(value or "").strip()
    if text and in_document(text, document_text):
        return _clip(text)
    snippet = find_snippet(document_text, fallback_query or text)
    return snippet or NOT_SPECIFIED


def find_snippet(document_text: str, query: str, width: int = 220) -> str:
    if not document_text:
        return ""
    haystack = document_text
    lowered = haystack.lower()
    tokens = [token for token in re.split(r"[^\w]+", (query or "").lower()) if len(token) > 3]
    index = -1
    matched = ""
    for token in tokens:
        index = lowered.find(token)
        if index >= 0:
            matched = token
            break
    if index < 0:
        return ""
    start = max(0, index - 40)
    end = min(len(haystack), index + width)
    snippet = haystack[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(haystack):
        snippet = snippet + "..."
    return snippet if matched else snippet


def _clip(text: str, limit: int = 280) -> str:
    text = _WS.sub(" ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
