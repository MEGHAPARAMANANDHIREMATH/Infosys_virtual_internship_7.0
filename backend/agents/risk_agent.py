import re

from agents.constants import FORECAST_STATUSES, NOT_SPECIFIED, SEVERITIES
from agents.extraction import parse_bullet_items, section_block
from agents.exceptions import LLMError
from agents.grounding import find_snippet, ground_evidence, ground_value, in_document, normalize
from agents.llm import complete_json, llm_enabled
from agents.scope_agent import extract_scope

RISK_PROMPT = """Return JSON:
{
  "risks": [
    {
      "risk": string,
      "category": "Schedule" | "Delayed task" | "Dependency gap" | "Missing resource" | "Unrealistic deadline" | "Overdue milestone" | "Conflicting timeline" | "Delivery challenge",
      "severity": "Low" | "Medium" | "High" | "Critical",
      "evidence": string,
      "affected": string,
      "mitigation": string
    }
  ],
  "forecast": {
    "status": "ON TRACK" | "AT RISK" | "DELAYED",
    "reason": string,
    "key_risks": [string],
    "affected_milestones": [string],
    "recommended_actions": [string]
  }
}
Use only document evidence. If a mitigation is not stated, use "Not specified".
"""

DELAYED_STATUSES = {"delayed", "overdue", "blocked", "at risk", "late", "slipped"}
MISSING_STATUSES = {"missing", "not assigned", "unassigned", "requested"}
RESOURCE_HINTS = (
    "no dedicated",
    "missing resource",
    "resource gap",
    "not assigned",
    "staffing",
    "no qa",
    "shortage",
)
UNREALISTIC_HINTS = ("unrealistic", "too aggressive", "impossible deadline", "cannot meet")
CONFLICT_HINTS = ("conflicting", "conflict", "depends on a delayed", "scheduled after")


class RiskForecastAgent:
    name = "risk"

    def analyze(self, document_text: str, metadata: dict | None = None) -> dict:
        scope = (metadata or {}).get("scope_result") or extract_scope(document_text)
        grounded = detect_risks(document_text, scope)
        if llm_enabled():
            prompt = (
                f"{RISK_PROMPT}\nFile: {(metadata or {}).get('file_name', '')}\n\n"
                f"DOCUMENT TEXT:\n{document_text[:14000]}"
            )
            try:
                llm_data = complete_json(prompt) or {}
                grounded = merge_risks(grounded, llm_data, document_text)
            except LLMError:
                pass
        grounded["forecast"] = build_forecast(document_text, grounded["risks"], scope)
        return grounded


def detect_risks(document_text: str, scope: dict) -> dict:
    risks: list[dict] = []

    for task in scope.get("tasks") or []:
        status = normalize(task.get("status", ""))
        if status in DELAYED_STATUSES:
            risks.append(
                _risk(
                    document_text,
                    risk=f"Task '{task['task']}' is {task.get('status')}",
                    category="Delayed task",
                    severity="High" if status in {"delayed", "overdue", "blocked"} else "Medium",
                    query=task["task"],
                    affected=task["task"],
                    mitigation=_mitigation_from_doc(document_text, task["task"]),
                )
            )
        if task.get("owner") == NOT_SPECIFIED and task.get("task") != NOT_SPECIFIED:
            risks.append(
                _risk(
                    document_text,
                    risk=f"Task '{task['task']}' has no owner",
                    category="Missing resource",
                    severity="Medium",
                    query=task["task"],
                    affected=task["task"],
                )
            )

    for milestone in scope.get("milestones") or []:
        status = normalize(milestone.get("status", ""))
        if status in {"overdue", "delayed"}:
            risks.append(
                _risk(
                    document_text,
                    risk=f"Milestone '{milestone['milestone']}' is {milestone.get('status')}",
                    category="Overdue milestone",
                    severity="Critical" if status == "overdue" else "High",
                    query=milestone["milestone"],
                    affected=milestone["milestone"],
                )
            )
        elif status == "at risk":
            risks.append(
                _risk(
                    document_text,
                    risk=f"Milestone '{milestone['milestone']}' is at risk",
                    category="Schedule",
                    severity="High",
                    query=milestone["milestone"],
                    affected=milestone["milestone"],
                )
            )

    for dep in scope.get("dependencies") or []:
        status = normalize(dep.get("status", ""))
        if status in MISSING_STATUSES or status in {"requested"}:
            severity = "High" if status == "missing" else "Medium"
            category = "Missing resource" if status in MISSING_STATUSES else "Dependency gap"
            risks.append(
                _risk(
                    document_text,
                    risk=f"Dependency '{dep['dependency']}' status is {dep.get('status')}",
                    category=category,
                    severity=severity,
                    query=dep["dependency"],
                    affected=dep.get("related_task") or NOT_SPECIFIED,
                )
            )

    lowered = document_text.lower()
    if any(hint in lowered for hint in RESOURCE_HINTS):
        snippet = find_snippet(document_text, "resource missing dedicated QA")
        risks.append(
            _risk(
                document_text,
                risk="Document reports a resource gap",
                category="Missing resource",
                severity="High",
                query="resource",
                affected=_affected_from_scope(scope),
                evidence=snippet,
            )
        )
    if any(hint in lowered for hint in UNREALISTIC_HINTS):
        risks.append(
            _risk(
                document_text,
                risk="Document describes an unrealistic deadline",
                category="Unrealistic deadline",
                severity="High",
                query="unrealistic deadline",
                affected=_milestone_names(scope),
            )
        )
    if any(hint in lowered for hint in CONFLICT_HINTS):
        risks.append(
            _risk(
                document_text,
                risk="Document describes a conflicting timeline",
                category="Conflicting timeline",
                severity="High",
                query="conflicting",
                affected=_milestone_names(scope),
            )
        )
    if "schedule risk" in lowered or re.search(r"\brisks?\b", lowered):
        for bullet in parse_bullet_items(section_block(document_text, "risks")) + _prose_risk_lines(document_text):
            if normalize(bullet) in {normalize(r["risk"]) for r in risks}:
                continue
            category = _category_from_text(bullet)
            risks.append(
                _risk(
                    document_text,
                    risk=bullet[:180],
                    category=category,
                    severity=_severity_from_text(bullet, category),
                    query=bullet,
                    affected=_guess_affected(bullet, scope),
                )
            )

    unique = []
    seen = set()
    for risk in risks:
        if not risk or not risk.get("evidence") or risk["evidence"] == NOT_SPECIFIED:
            continue
        key = normalize(risk["risk"])[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(risk)
    return {"risks": unique, "forecast": {}}


def _prose_risk_lines(document_text: str) -> list[str]:
    lines = []
    for line in document_text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^(schedule risk|resource gap|unrealistic deadline|conflicting timeline|delivery)", stripped):
            lines.append(re.sub(r"(?i)^[a-z ]+:\s*", "", stripped))
    return lines


def _risk(document_text, risk, category, severity, query, affected, mitigation=None, evidence=None):
    evidence_text = evidence or ground_evidence("", document_text, query)
    if evidence_text == NOT_SPECIFIED:
        evidence_text = find_snippet(document_text, query) or NOT_SPECIFIED
    return {
        "risk": risk,
        "category": category,
        "severity": severity if severity in SEVERITIES else "Medium",
        "evidence": evidence_text,
        "affected": affected if affected and affected != NOT_SPECIFIED else NOT_SPECIFIED,
        "mitigation": mitigation or _mitigation_from_doc(document_text, query),
    }


def _mitigation_from_doc(document_text: str, query: str) -> str:
    block = section_block(document_text, "risks")
    for line in (block or document_text).splitlines():
        if "mitigation" in line.lower() and (not query or in_document(query.split()[0], line)):
            _, _, rest = line.partition(":")
            return ground_value(rest or line, document_text)
    return NOT_SPECIFIED


def _affected_from_scope(scope: dict) -> str:
    names = [row.get("task") for row in scope.get("tasks") or [] if row.get("task") and row["task"] != NOT_SPECIFIED]
    return names[0] if names else _milestone_names(scope)


def _milestone_names(scope: dict) -> str:
    names = [
        row.get("milestone")
        for row in scope.get("milestones") or []
        if row.get("milestone") and row["milestone"] != NOT_SPECIFIED
    ]
    return names[0] if names else NOT_SPECIFIED


def _guess_affected(text: str, scope: dict) -> str:
    blob = normalize(text)
    for collection, key in (
        (scope.get("milestones") or [], "milestone"),
        (scope.get("tasks") or [], "task"),
        (scope.get("deliverables") or [], "deliverable"),
    ):
        for row in collection:
            name = row.get(key) or ""
            if name != NOT_SPECIFIED and normalize(name) in blob:
                return name
    return NOT_SPECIFIED


def _category_from_text(text: str) -> str:
    lowered = text.lower()
    if "overdue" in lowered and "milestone" in lowered:
        return "Overdue milestone"
    if "delayed" in lowered:
        return "Delayed task"
    if "dependenc" in lowered:
        return "Dependency gap"
    if "resource" in lowered or "qa" in lowered:
        return "Missing resource"
    if "unrealistic" in lowered:
        return "Unrealistic deadline"
    if "conflict" in lowered:
        return "Conflicting timeline"
    if "schedule" in lowered:
        return "Schedule"
    return "Delivery challenge"


def _severity_from_text(text: str, category: str) -> str:
    lowered = text.lower()
    if "critical" in lowered or "overdue" in lowered:
        return "Critical"
    if category in {"Overdue milestone"}:
        return "Critical"
    if category in {"Delayed task", "Unrealistic deadline", "Conflicting timeline", "Missing resource"}:
        return "High"
    if "medium" in lowered:
        return "Medium"
    return "Medium"


def merge_risks(grounded: dict, llm_data: dict, document_text: str) -> dict:
    extra = []
    for row in llm_data.get("risks") or []:
        if not isinstance(row, dict):
            continue
        evidence = ground_evidence(row.get("evidence"), document_text, row.get("risk", ""))
        if evidence == NOT_SPECIFIED:
            continue
        extra.append(
            {
                "risk": str(row.get("risk") or NOT_SPECIFIED)[:240],
                "category": row.get("category") or "Delivery challenge",
                "severity": row.get("severity") if row.get("severity") in SEVERITIES else "Medium",
                "evidence": evidence,
                "affected": ground_value(row.get("affected") or row.get("affected_task") or row.get("affected_milestone"), document_text),
                "mitigation": ground_value(row.get("mitigation"), document_text),
            }
        )
    combined = grounded.get("risks", []) + extra
    unique = []
    seen = set()
    for risk in combined:
        key = normalize(risk.get("risk", ""))[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(risk)
    return {"risks": unique, "forecast": grounded.get("forecast") or {}}


def build_forecast(document_text: str, risks: list[dict], scope: dict) -> dict:
    delayed_items = [
        row
        for row in (scope.get("tasks") or []) + (scope.get("milestones") or [])
        if normalize(row.get("status", "")) in {"delayed", "overdue"}
    ]
    high = [risk for risk in risks if risk.get("severity") in {"High", "Critical"}]
    if delayed_items or any(risk.get("severity") == "Critical" for risk in risks):
        status = "DELAYED"
        reason = "The document reports delayed or overdue work."
    elif high or risks:
        status = "AT RISK"
        reason = "The document identifies delivery risks without confirming an on-track schedule."
    elif _has_schedule_signal(document_text, scope):
        on_track_mention = "on track" in document_text.lower()
        status = "ON TRACK"
        reason = (
            "The document describes planned work and does not report delays."
            if not on_track_mention
            else "The document states the project is on track."
        )
        if not on_track_mention and not risks:
            # No delay evidence and schedule exists.
            reason = "No delayed tasks, overdue milestones, or explicit risks were found in the document."
    else:
        status = "AT RISK"
        reason = "The document does not contain enough schedule evidence to confirm the project is on track."

    if status not in FORECAST_STATUSES:
        status = "AT RISK"

    affected_milestones = []
    for row in scope.get("milestones") or []:
        if normalize(row.get("status", "")) in DELAYED_STATUSES or row.get("milestone") in {
            risk.get("affected") for risk in risks
        }:
            if row.get("milestone") and row["milestone"] != NOT_SPECIFIED:
                affected_milestones.append(row["milestone"])
    if not affected_milestones:
        affected_milestones = [NOT_SPECIFIED]

    key_risks = [risk["risk"] for risk in risks[:5]] or [NOT_SPECIFIED]
    actions = []
    for risk in high[:3]:
        if risk.get("mitigation") and risk["mitigation"] != NOT_SPECIFIED:
            actions.append(risk["mitigation"])
        else:
            actions.append(f"Review and resolve: {risk['risk']}")
    if not actions:
        actions = [NOT_SPECIFIED] if status == "ON TRACK" else ["Review the risks and dates stated in the uploaded document."]

    return {
        "status": status,
        "reason": reason,
        "key_risks": key_risks,
        "affected_milestones": affected_milestones,
        "recommended_actions": actions,
    }


def _has_schedule_signal(document_text: str, scope: dict) -> bool:
    if scope.get("start_date") != NOT_SPECIFIED or scope.get("end_date") != NOT_SPECIFIED:
        return True
    if scope.get("milestones") or scope.get("tasks"):
        return True
    return bool(re.search(r"\b(deadline|milestone|schedule|start date)\b", document_text, re.I))
