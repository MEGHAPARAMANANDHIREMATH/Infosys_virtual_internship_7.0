import re

from agents.constants import NOT_SPECIFIED
from agents.exceptions import LLMError
from agents.extraction import parse_bullet_items, records_for, section_block
from agents.grounding import ground_evidence, ground_value, normalize
from agents.llm import complete_json, llm_enabled

BLOCKER_PROMPT = """Return JSON:
{
  "blockers": [{"blocker": string, "evidence": string, "owner": string, "priority": string, "status": string}],
  "pending_decisions": [{"decision": string, "evidence": string, "responsible_person": string, "due_date": string, "status": string}],
  "open_issues": [{"issue": string, "evidence": string, "owner": string, "priority": string, "status": string}],
  "action_items": [{"action_item": string, "owner": string, "due_date": string, "priority": string, "status": string}]
}
Do not invent owners or due dates. Use "Not specified" when missing.
"""

PRIORITY_WORDS = {"low", "medium", "high", "critical"}


class BlockerActionAgent:
    name = "blockers"

    def analyze(self, document_text: str, metadata: dict | None = None) -> dict:
        grounded = extract_blockers(document_text)
        if llm_enabled():
            prompt = (
                f"{BLOCKER_PROMPT}\nFile: {(metadata or {}).get('file_name', '')}\n\n"
                f"DOCUMENT TEXT:\n{document_text[:14000]}"
            )
            try:
                llm_data = complete_json(prompt) or {}
                grounded = merge_blockers(grounded, llm_data, document_text)
            except LLMError:
                pass
        return grounded


def extract_blockers(document_text: str) -> dict:
    blockers = _rows_from_records(
        document_text,
        records_for(document_text, ["blocker"]),
        {
            "blocker": "blocker",
            "evidence": "evidence",
            "owner": "owner",
            "priority": "priority",
            "status": "status",
        },
        "blocker",
    )
    if not blockers:
        blockers = _rows_from_bullets(document_text, "blockers", "blocker")

    decisions = _rows_from_records(
        document_text,
        records_for(document_text, ["decision"]),
        {
            "decision": "decision",
            "evidence": "evidence",
            "responsible_person": "owner",
            "due_date": "deadline",
            "status": "status",
        },
        "decision",
    )
    if not decisions:
        decisions = _rows_from_bullets(document_text, "decisions", "decision", extra_keys=("responsible_person", "due_date"))

    issues = _rows_from_records(
        document_text,
        records_for(document_text, ["issue"]),
        {
            "issue": "issue",
            "evidence": "evidence",
            "owner": "owner",
            "priority": "priority",
            "status": "status",
        },
        "issue",
    )
    if not issues:
        issues = _rows_from_bullets(document_text, "issues", "issue")

    actions = _rows_from_records(
        document_text,
        records_for(document_text, ["action"]),
        {
            "action_item": "action",
            "owner": "owner",
            "due_date": "deadline",
            "priority": "priority",
            "status": "status",
        },
        "action_item",
    )
    if not actions:
        actions = _rows_from_bullets(document_text, "actions", "action_item", extra_keys=("owner", "due_date"))

    blockers += _labeled_lines(document_text, r"(?i)^blocker\s*[:\-]\s*(.+)$", "blocker")
    decisions += _labeled_lines(
        document_text,
        r"(?i)^(?:pending decision|decision required|decision)\s*[:\-]\s*(.+)$",
        "decision",
        person_key="responsible_person",
    )
    issues += _labeled_lines(document_text, r"(?i)^(?:open issue|issue)\s*[:\-]\s*(.+)$", "issue")
    actions += _labeled_lines(
        document_text,
        r"(?i)^(?:action item|action)\s*[:\-]\s*(.+)$",
        "action_item",
        date_key="due_date",
    )

    return {
        "blockers": _dedupe(blockers, "blocker"),
        "pending_decisions": _dedupe(decisions, "decision"),
        "open_issues": _dedupe(issues, "issue"),
        "action_items": _dedupe(actions, "action_item"),
    }


def _rows_from_records(document_text, records, mapping, name_key):
    rows = []
    for record in records:
        row = {target: record.get(source, NOT_SPECIFIED) for target, source in mapping.items()}
        name = ground_value(row.get(name_key), document_text)
        if name == NOT_SPECIFIED:
            continue
        row[name_key] = name
        for key, value in list(row.items()):
            if key == name_key:
                continue
            if key == "evidence":
                row[key] = ground_evidence(value, document_text, name)
            elif key in {"owner", "responsible_person", "due_date", "deadline"}:
                row[key] = ground_value(value, document_text)
            elif key in {"priority", "status"}:
                row[key] = _priority_or_status(value, document_text)
            else:
                row[key] = ground_value(value, document_text)
        if row.get("evidence") in (None, "", NOT_SPECIFIED):
            row["evidence"] = ground_evidence("", document_text, name)
        rows.append(row)
    return rows


def _rows_from_bullets(document_text, section_key, name_key, extra_keys=()):
    rows = []
    for item in parse_bullet_items(section_block(document_text, section_key)):
        parsed = _split_owner_date(item)
        name = ground_value(parsed["text"], document_text)
        if name == NOT_SPECIFIED:
            continue
        row = {
            name_key: name,
            "evidence": ground_evidence(item, document_text, name),
            "owner": ground_value(parsed["owner"], document_text),
            "priority": parsed["priority"],
            "status": parsed["status"],
        }
        if "responsible_person" in extra_keys:
            row["responsible_person"] = row.pop("owner")
        if "due_date" in extra_keys:
            row["due_date"] = ground_value(parsed["due_date"], document_text)
        if name_key == "action_item":
            row["due_date"] = ground_value(parsed["due_date"], document_text)
            row.pop("evidence", None)
        rows.append(row)
    return rows


def _labeled_lines(document_text, pattern, name_key, person_key="owner", date_key=None):
    rows = []
    for match in re.finditer(pattern, document_text, re.M):
        parsed = _split_owner_date(match.group(1).strip())
        name = ground_value(parsed["text"], document_text)
        if name == NOT_SPECIFIED:
            continue
        row = {
            name_key: name,
            "evidence": ground_evidence(match.group(0), document_text, name),
            person_key: ground_value(parsed["owner"], document_text),
            "priority": parsed["priority"],
            "status": parsed["status"],
        }
        if date_key:
            row[date_key] = ground_value(parsed["due_date"], document_text)
        if name_key == "action_item":
            row.setdefault("due_date", ground_value(parsed["due_date"], document_text))
            row.pop("evidence", None)
        rows.append(row)
    return rows


def _split_owner_date(text: str) -> dict:
    owner = NOT_SPECIFIED
    due_date = NOT_SPECIFIED
    priority = NOT_SPECIFIED
    status = NOT_SPECIFIED
    remainder = text
    owner_match = re.search(
        r"(?i)\b(?:owner|responsible(?:\s*person)?|assigned to)\s*[:\-]\s*([^;,|]+)",
        text,
    )
    if owner_match:
        owner = owner_match.group(1).strip()
        remainder = remainder.replace(owner_match.group(0), " ")
    date_match = re.search(
        r"(?i)\b(?:due(?:\s*date)?|deadline|by)\s*[:\-]?\s*"
        r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4})",
        text,
    )
    if date_match:
        due_date = date_match.group(1).strip()
        remainder = remainder.replace(date_match.group(0), " ")
    for word in PRIORITY_WORDS:
        if re.search(rf"\b{word}\b", text, re.I):
            priority = word.title()
            break
    status_match = re.search(r"(?i)\bstatus\s*[:\-]\s*([^;,|]+)", text)
    if status_match:
        status = status_match.group(1).strip()
    remainder = re.sub(r"\s+", " ", remainder).strip(" -;:")
    return {
        "text": remainder or text,
        "owner": owner,
        "due_date": due_date,
        "priority": priority,
        "status": status,
    }


def _priority_or_status(value, document_text: str) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "null"}:
        return NOT_SPECIFIED
    if normalize(text) in PRIORITY_WORDS:
        return text.title()
    return ground_value(text, document_text)


def _dedupe(rows: list[dict], name_key: str) -> list[dict]:
    unique = []
    seen = set()
    for row in rows:
        key = normalize(str(row.get(name_key, "")))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def merge_blockers(grounded: dict, llm_data: dict, document_text: str) -> dict:
    mapping = {
        "blockers": ("blocker", {"blocker": "blocker", "evidence": "evidence", "owner": "owner", "priority": "priority", "status": "status"}),
        "pending_decisions": (
            "decision",
            {
                "decision": "decision",
                "evidence": "evidence",
                "responsible_person": "responsible_person",
                "due_date": "due_date",
                "status": "status",
            },
        ),
        "open_issues": ("issue", {"issue": "issue", "evidence": "evidence", "owner": "owner", "priority": "priority", "status": "status"}),
        "action_items": (
            "action_item",
            {
                "action_item": "action_item",
                "owner": "owner",
                "due_date": "due_date",
                "priority": "priority",
                "status": "status",
            },
        ),
    }
    merged = {}
    for collection, (name_key, fields) in mapping.items():
        extra = []
        for row in llm_data.get(collection) or []:
            if not isinstance(row, dict):
                continue
            item = {target: row.get(source, NOT_SPECIFIED) for target, source in fields.items()}
            if "responsible_person" in item and item["responsible_person"] == NOT_SPECIFIED:
                item["responsible_person"] = row.get("owner", NOT_SPECIFIED)
            name = ground_value(item.get(name_key), document_text)
            if name == NOT_SPECIFIED:
                continue
            item[name_key] = name
            for key in item:
                if key == name_key:
                    continue
                if key == "evidence":
                    item[key] = ground_evidence(item[key], document_text, name)
                elif key in {"owner", "responsible_person", "due_date"}:
                    item[key] = ground_value(item[key], document_text)
                elif key in {"priority", "status"}:
                    item[key] = _priority_or_status(item[key], document_text)
            extra.append(item)
        merged[collection] = _dedupe((grounded.get(collection) or []) + extra, name_key)
    return merged
