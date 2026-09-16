from agents.base import BaseAgent, missing_overview
from agents.constants import NOT_SPECIFIED
from agents.exceptions import LLMError
from agents.extraction import (
    extract_field,
    ground_record,
    map_record,
    parse_bullet_items,
    records_for,
    section_block,
)
from agents.grounding import ground_value
from agents.llm import complete_json, llm_enabled

SCOPE_PROMPT = """Return JSON with this shape:
{
  "project_name": string,
  "objective": string,
  "scope": string,
  "start_date": string,
  "end_date": string,
  "responsibilities": [{"name": string, "role": string}],
  "tasks": [{"task": string, "owner": string, "deadline": string, "status": string, "depends_on": string}],
  "deliverables": [{"deliverable": string, "owner": string, "deadline": string, "status": string}],
  "milestones": [{"milestone": string, "date": string, "owner": string, "status": string}],
  "dependencies": [{"dependency": string, "related_task": string, "status": string}]
}
Use "Not specified" for missing values. Do not invent data.
"""


class ScopeDeliverableAgent(BaseAgent):
    name = "scope"
    prompt_schema = SCOPE_PROMPT

    def analyze(self, document_text: str, metadata: dict | None = None) -> dict:
        grounded = extract_scope(document_text)
        if llm_enabled():
            prompt = (
                f"{SCOPE_PROMPT}\nFile: {(metadata or {}).get('file_name', '')}\n\n"
                f"DOCUMENT TEXT:\n{document_text[:14000]}"
            )
            try:
                llm_data = complete_json(prompt) or {}
                grounded = merge_scope(grounded, llm_data, document_text)
            except LLMError:
                pass
        return grounded


def extract_scope(document_text: str) -> dict:
    result = missing_overview()
    result["project_name"] = ground_value(extract_field(document_text, "project_name"), document_text)
    result["objective"] = _multiline_field(document_text, "objective")
    result["scope"] = _multiline_field(document_text, "scope")
    result["start_date"] = ground_value(extract_field(document_text, "start_date"), document_text)
    result["end_date"] = ground_value(extract_field(document_text, "end_date"), document_text)

    deliverable_records = records_for(document_text, ["deliverable"])
    if not deliverable_records:
        deliverable_records = [
            {"deliverable": item} for item in parse_bullet_items(section_block(document_text, "deliverables"))
        ]
    result["deliverables"] = _ground_rows(
        [
            map_record(
                record,
                {
                    "deliverable": "deliverable",
                    "owner": "owner",
                    "deadline": "deadline",
                    "status": "status",
                },
            )
            for record in deliverable_records
        ],
        document_text,
        "deliverable",
    )

    milestone_records = records_for(document_text, ["milestone"])
    if not milestone_records:
        milestone_records = [
            {"milestone": item} for item in parse_bullet_items(section_block(document_text, "milestones"))
        ]
    result["milestones"] = _ground_rows(
        [
            map_record(
                record,
                {
                    "milestone": "milestone",
                    "date": "deadline",
                    "owner": "owner",
                    "status": "status",
                },
            )
            for record in milestone_records
        ],
        document_text,
        "milestone",
    )
    for row in result["milestones"]:
        if row.get("date") in (None, NOT_SPECIFIED) and row.get("deadline"):
            row["date"] = row["deadline"]
        row.setdefault("date", NOT_SPECIFIED)
        row.pop("deadline", None)

    task_records = records_for(document_text, ["task"])
    result["tasks"] = _ground_rows(
        [
            {
                "task": record.get("task", NOT_SPECIFIED),
                "owner": record.get("owner", NOT_SPECIFIED),
                "deadline": record.get("deadline", NOT_SPECIFIED),
                "status": record.get("status", NOT_SPECIFIED),
                "depends_on": record.get("dependency", NOT_SPECIFIED),
            }
            for record in task_records
        ],
        document_text,
        "task",
    )

    dependency_records = [
        record for record in records_for(document_text, ["dependency"]) if "task" not in record or "dependency" in record
    ]
    # labeled "Depends On" on tasks already captured; keep dedicated dependency rows
    dedicated = []
    for record in parse_pipe_tables_safe(document_text):
        if "dependency" in record and "deliverable" not in record and "milestone" not in record:
            dedicated.append(
                {
                    "dependency": record.get("dependency", NOT_SPECIFIED),
                    "related_task": record.get("task", NOT_SPECIFIED),
                    "status": record.get("status", NOT_SPECIFIED),
                }
            )
    if not dedicated:
        dedicated = [
            {
                "dependency": record.get("dependency", NOT_SPECIFIED),
                "related_task": record.get("task", NOT_SPECIFIED),
                "status": record.get("status", NOT_SPECIFIED),
            }
            for record in dependency_records
            if record.get("dependency")
        ]
    result["dependencies"] = _ground_rows(dedicated, document_text, "dependency")

    result["responsibilities"] = _responsibilities(document_text, result)
    return result


def parse_pipe_tables_safe(document_text: str):
    from agents.extraction import parse_pipe_tables

    return parse_pipe_tables(document_text)


def _multiline_field(document_text: str, key: str) -> str:
    labeled = extract_field(document_text, key)
    block = section_block(document_text, key)
    candidate = block if block and (labeled == NOT_SPECIFIED or len(block) > len(labeled)) else labeled
    return ground_value(candidate.replace("\n", " "), document_text) if candidate else NOT_SPECIFIED


def _responsibilities(document_text: str, result: dict) -> list[dict]:
    seen = []
    rows = []
    for collection in (result["deliverables"], result["milestones"], result["tasks"]):
        for item in collection:
            owner = item.get("owner") or NOT_SPECIFIED
            if owner == NOT_SPECIFIED or owner in seen:
                continue
            seen.append(owner)
            role = NOT_SPECIFIED
            rows.append({"name": owner, "role": role})
    block = section_block(document_text, "responsibilities")
    for line in block.splitlines():
        if ":" in line:
            name, role = [part.strip() for part in line.split(":", 1)]
            name = ground_value(name, document_text)
            if name != NOT_SPECIFIED and name not in seen:
                seen.append(name)
                rows.append({"name": name, "role": ground_value(role, document_text)})
    return rows


def _ground_rows(rows: list[dict], document_text: str, name_key: str) -> list[dict]:
    grounded = []
    seen = set()
    for row in rows:
        item = ground_record(row, document_text, name_key)
        if not item:
            continue
        key = item[name_key].lower()
        if key in seen:
            continue
        seen.add(key)
        grounded.append(item)
    return grounded


def merge_scope(grounded: dict, llm_data: dict, document_text: str) -> dict:
    merged = dict(grounded)
    for key in ("project_name", "objective", "scope", "start_date", "end_date"):
        llm_value = ground_value(llm_data.get(key), document_text)
        if merged.get(key) == NOT_SPECIFIED and llm_value != NOT_SPECIFIED:
            merged[key] = llm_value
    list_keys = {
        "deliverables": "deliverable",
        "milestones": "milestone",
        "tasks": "task",
        "dependencies": "dependency",
        "responsibilities": "name",
    }
    for collection, name_key in list_keys.items():
        extra = []
        for row in llm_data.get(collection) or []:
            if not isinstance(row, dict):
                continue
            if collection == "milestones" and "date" not in row and "deadline" in row:
                row = {**row, "date": row.get("deadline")}
            item = ground_record(row, document_text, name_key)
            if item:
                extra.append(item)
        merged[collection] = _ground_rows((merged.get(collection) or []) + extra, document_text, name_key)
    return merged
