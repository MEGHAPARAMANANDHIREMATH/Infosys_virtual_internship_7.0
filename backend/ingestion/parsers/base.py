from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParsedSegment:
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
