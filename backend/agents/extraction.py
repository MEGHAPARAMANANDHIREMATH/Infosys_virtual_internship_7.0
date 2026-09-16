import re
from typing import Iterable

from agents.constants import NOT_SPECIFIED
from agents.grounding import ground_value, normalize

SECTION_TITLES = {
    "overview": ("project overview", "overview"),
    "objective": ("objective", "objectives", "goals", "project goals", "project objective"),
    "scope": ("scope", "project scope", "in scope", "out of scope"),
    "deliverables": ("deliverables", "major deliverables"),
    "milestones": ("milestones", "milestone"),
    "tasks": ("tasks", "task list", "work items"),
    "dependencies": ("dependencies", "dependency"),
    "responsibilities": ("responsibilities", "owners", "team members", "raci"),
    "risks": ("risks", "risk", "schedule risks", "issues and risks"),
    "blockers": ("blockers", "blocker", "impediments"),
    "decisions": ("pending decisions", "decisions", "decision required"),
    "issues": ("open issues", "issues"),
    "actions": ("action items", "actions", "action item"),
    "forecast": ("delivery forecast", "status", "progress"),
}

FIELD_PATTERNS = {
    "project_name": [
        r"(?im)^(?:project\s*name|name)\s*[:\-]\s*(.+)$",
    ],
    "objective": [
        r"(?im)^(?:project\s*)?(?:objective|objectives|goals?)\s*[:\-]\s*(.+)$",
    ],
    "scope": [
        r"(?im)^(?:project\s*)?scope\s*[:\-]\s*(.+)$",
    ],
    "start_date": [
        r"(?im)^(?:start\s*date|project\s*start)\s*[:\-]\s*(.+)$",
    ],
    "end_date": [
        r"(?im)^(?:deadline|end\s*date|due\s*date|finish\s*date|project\s*end)\s*[:\-]\s*(.+)$",
    ],
}

COLUMN_ALIASES = {
    "deliverable": {"deliverable", "deliverables", "item", "name"},
    "milestone": {"milestone", "milestones"},
    "task": {"task", "tasks", "related task", "related_task", "work item"},
    "owner": {
        "owner",
        "owners",
        "responsible",
        "responsible person",
        "assignee",
        "assigned to",
        "responsibility",
        "team member",
    },
    "deadline": {"deadline", "due date", "due", "end date", "date", "target date"},
    "status": {"status", "state"},
    "dependency": {"dependency", "dependencies", "depends on", "blocked by"},
    "blocker": {"blocker", "blockers", "impediment"},
    "decision": {"decision required", "decision", "pending decision"},
    "issue": {"issue", "open issue"},
    "action": {"action item", "action", "next step"},
    "priority": {"priority", "severity"},
    "evidence": {"evidence", "notes", "comment", "description"},
    "category": {"category", "type"},
}

HEADER_RE = re.compile(r"^[A-Z][A-Z0-9 /&-]{2,}$")
DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b",
    re.I,
)


def extract_field(text: str, key: str) -> str:
    for pattern in FIELD_PATTERNS.get(key, []):
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    block = section_block(text, key)
    if block:
        first = next((line for line in block.splitlines() if line.strip()), "")
        if first and not _looks_like_header(first):
            return first.strip()
    return NOT_SPECIFIED


def section_block(text: str, key: str) -> str:
    titles = SECTION_TITLES.get(key, ())
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip().strip(":").lower()
        if stripped in titles:
            start = index + 1
            break
    if start is None:
        return ""
    collected: list[str] = []
    all_titles = {title for group in SECTION_TITLES.values() for title in group}
    for line in lines[start:]:
        stripped = line.strip().strip(":").lower()
        if stripped in all_titles:
            break
        collected.append(line)
    return "\n".join(collected).strip()


def parse_pipe_tables(text: str) -> list[dict]:
    rows: list[dict] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    index = 0
    while index < len(lines):
        line = lines[index]
        if "|" not in line:
            index += 1
            continue
        cells = _split_row(line)
        if len(cells) < 2 or not _looks_like_header_row(cells):
            index += 1
            continue
        headers = [_canonical_column(cell) for cell in cells]
        index += 1
        if index < len(lines) and re.fullmatch(r"[:\-| ]+", lines[index]):
            index += 1
        while index < len(lines) and "|" in lines[index]:
            values = _split_row(lines[index])
            index += 1
            if len(values) == 1:
                continue
            record = {}
            for header, value in zip(headers, values):
                if header:
                    record[header] = value or NOT_SPECIFIED
            if any(v and v != NOT_SPECIFIED for v in record.values()):
                rows.append(record)
        continue
    return rows


def parse_labeled_records(text: str) -> list[dict]:
    records: list[dict] = []
    current: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        match = re.match(r"^([A-Za-z][A-Za-z0-9 /_]{1,40})\s*[:\-]\s*(.+)$", line)
        if not match:
            if current:
                records.append(current)
                current = {}
            continue
        column = _canonical_column(match.group(1))
        if not column:
            continue
        current[column] = match.group(2).strip()
    if current:
        records.append(current)
    return [record for record in records if len(record) >= 2]


def parse_bullet_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def records_for(text: str, name_keys: Iterable[str]) -> list[dict]:
    keys = list(name_keys)
    combined = parse_pipe_tables(text) + parse_labeled_records(text)
    matched = []
    for record in combined:
        if any(key in record for key in keys):
            matched.append(record)
    if matched:
        return matched
    return []


def map_record(record: dict, mapping: dict[str, str]) -> dict:
    mapped = {}
    for target, source in mapping.items():
        mapped[target] = record.get(source, NOT_SPECIFIED) or NOT_SPECIFIED
    return mapped


def ground_record(record: dict, document_text: str, required_name_key: str) -> dict | None:
    name = ground_value(record.get(required_name_key), document_text)
    if name == NOT_SPECIFIED:
        return None
    grounded = {}
    for key, value in record.items():
        if key == required_name_key:
            grounded[key] = name
        elif key == "evidence":
            from agents.grounding import ground_evidence

            grounded[key] = ground_evidence(value, document_text, name)
        elif key in {"severity", "category"}:
            grounded[key] = str(value).strip() if value else NOT_SPECIFIED
        else:
            grounded[key] = ground_value(value, document_text)
    return grounded


def in_or_allowed_enum(value: str, document_text: str, key: str) -> bool:
    from agents.grounding import in_document

    if not value or value == NOT_SPECIFIED:
        return True
    if in_document(value, document_text):
        return True
    allowed = {
        "status": {
            "not started",
            "in progress",
            "completed",
            "done",
            "delayed",
            "overdue",
            "blocked",
            "at risk",
            "open",
            "closed",
            "pending",
            "missing",
            "requested",
        },
        "priority": {"low", "medium", "high", "critical"},
        "severity": {"low", "medium", "high", "critical"},
        "category": {
            "schedule",
            "schedule risk",
            "delayed task",
            "dependency gap",
            "missing resource",
            "unrealistic deadline",
            "overdue milestone",
            "conflicting timeline",
            "delivery challenge",
        },
    }
    return normalize(value) in allowed.get(key, set())


def _split_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _looks_like_header_row(cells: list[str]) -> bool:
    joined = " ".join(cells).lower()
    header_tokens = {
        "deliverable",
        "owner",
        "deadline",
        "status",
        "milestone",
        "date",
        "dependency",
        "task",
        "blocker",
        "decision",
        "issue",
        "action",
        "priority",
        "due",
        "responsible",
    }
    return sum(1 for token in header_tokens if token in joined) >= 2


def _canonical_column(label: str) -> str | None:
    norm = normalize(label)
    for canonical, aliases in COLUMN_ALIASES.items():
        if norm in aliases:
            return canonical
    return None


def _looks_like_header(line: str) -> bool:
    stripped = line.strip().strip(":")
    return bool(HEADER_RE.match(stripped)) or normalize(stripped) in {
        title for group in SECTION_TITLES.values() for title in group
    }


def find_dates(text: str) -> list[str]:
    return DATE_RE.findall(text or "")
