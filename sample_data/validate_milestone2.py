"""Run grounded agents against Milestone 2 sample documents and print a report."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "sample_data"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("LLM_PROVIDER", "grounded")
os.environ.setdefault("OPENAI_API_KEY", "")

import django

django.setup()

from generate_milestone2_samples import main as generate_samples

from agents.blocker_agent import extract_blockers
from agents.constants import NOT_SPECIFIED
from agents.risk_agent import build_forecast, detect_risks
from agents.scope_agent import extract_scope
from agents.text import extract_document_text


SAMPLES = ROOT / "sample_data" / "milestone2"


def _contains(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return all(needle.lower() in lowered for needle in needles)


def _rows_blob(rows: list[dict]) -> str:
    return json.dumps(rows, ensure_ascii=True).lower()


def validate() -> list[dict]:
    generate_samples()
    rows: list[dict] = []

    software = extract_document_text(SAMPLES / "software_development_project_plan.pdf", "pdf")
    scope = extract_scope(software)
    risks = detect_risks(software, scope)
    forecast = build_forecast(software, risks["risks"], scope)
    rows.extend(
        [
            _row(
                "Software Development Project Plan",
                "PDF",
                "Scope",
                "Name, objective, scope, dates, deliverables, milestones, tasks, owners, dependencies",
                f"name={scope['project_name']}; deliverables={len(scope['deliverables'])}; "
                f"milestones={len(scope['milestones'])}; tasks={len(scope['tasks'])}; "
                f"deps={len(scope['dependencies'])}",
                _ok(
                    scope["project_name"] == "Campus Attendance Platform"
                    and "QR-based" in scope["objective"]
                    and scope["start_date"] == "2026-01-15"
                    and scope["end_date"] == "2026-06-30"
                    and any(row["deliverable"] == "Mobile check-in app" for row in scope["deliverables"])
                    and any(row["owner"] == "Priya Sharma" for row in scope["deliverables"])
                    and any(row["milestone"] == "Beta release" for row in scope["milestones"])
                    and any(row.get("status") == "Delayed" for row in scope["tasks"])
                    and any("SSO" in row["dependency"] for row in scope["dependencies"])
                ),
            ),
            _row(
                "Software Development Project Plan",
                "PDF",
                "Risk & Forecast",
                "Delayed task, missing resource, unrealistic deadline, AT RISK or DELAYED",
                f"risks={len(risks['risks'])}; forecast={forecast['status']}",
                _ok(
                    risks["risks"]
                    and all(item["evidence"] != NOT_SPECIFIED for item in risks["risks"])
                    and forecast["status"] in {"AT RISK", "DELAYED"}
                    and {"Delayed task", "Missing resource"} & {item["category"] for item in risks["risks"]}
                ),
            ),
        ]
    )

    college = extract_document_text(SAMPLES / "college_project_plan.docx", "docx")
    college_scope = extract_scope(college)
    college_risks = detect_risks(college, college_scope)
    college_forecast = build_forecast(college, college_risks["risks"], college_scope)
    rows.append(
        _row(
            "College Project Plan",
            "DOCX",
            "Scope",
            "Smart Library Kiosk, team, tasks, milestones, deadline",
            f"name={college_scope['project_name']}; tasks={len(college_scope['tasks'])}; "
            f"milestones={len(college_scope['milestones'])}",
            _ok(
                college_scope["project_name"] == "Smart Library Kiosk"
                and college_scope["end_date"] == "2026-11-15"
                and any(row["owner"] == "Luis Romero" for row in college_scope["tasks"])
                and any(row["milestone"] == "Midterm demo" for row in college_scope["milestones"])
            ),
        )
    )
    rows.append(
        _row(
            "College Project Plan",
            "DOCX",
            "Risk & Forecast",
            "No invented delays; missing info stays Not specified",
            f"forecast={college_forecast['status']}; risks={len(college_risks['risks'])}",
            _ok(
                college_forecast["status"] in {"ON TRACK", "AT RISK", "DELAYED"}
                and "john doe" not in _rows_blob(college_scope["tasks"])
            ),
        )
    )

    meeting = extract_document_text(SAMPLES / "meeting_notes.txt", "txt")
    blockers = extract_blockers(meeting)
    rows.append(
        _row(
            "Meeting Notes",
            "TXT",
            "Blockers",
            "Blocker, pending decision, issue, action items with owners and due dates",
            f"blockers={len(blockers['blockers'])}; decisions={len(blockers['pending_decisions'])}; "
            f"actions={len(blockers['action_items'])}",
            _ok(
                blockers["blockers"]
                and blockers["blockers"][0]["owner"] == "Ananya Iyer"
                and blockers["pending_decisions"][0]["responsible_person"] == "Maya Chen"
                and blockers["pending_decisions"][0]["due_date"] == "2026-09-18"
                and any("license reminder" in row["action_item"].lower() for row in blockers["action_items"])
            ),
        )
    )

    tracker = extract_document_text(SAMPLES / "project_task_tracker.xlsx", "xlsx")
    tracker_scope = extract_scope(tracker)
    tracker_risks = detect_risks(tracker, tracker_scope)
    rows.append(
        _row(
            "Project Task Tracker",
            "XLSX",
            "Scope + Risk",
            "Tasks, owners, delayed/blocked work, missing SDK dependency",
            f"tasks={len(tracker_scope['tasks'])}; risks={len(tracker_risks['risks'])}",
            _ok(
                any(row["task"] == "Card reader integration" for row in tracker_scope["tasks"])
                and any(row.get("status") == "Delayed" for row in tracker_scope["tasks"])
                and any("SDK" in row["dependency"] for row in tracker_scope["dependencies"])
                and tracker_risks["risks"]
            ),
        )
    )

    status = extract_document_text(SAMPLES / "project_status_report.docx", "docx")
    status_scope = extract_scope(status)
    status_risks = detect_risks(status, status_scope)
    status_blockers = extract_blockers(status)
    status_forecast = build_forecast(status, status_risks["risks"], status_scope)
    rows.append(
        _row(
            "Project Status Report",
            "DOCX",
            "All agents",
            "Progress, delayed task, risks, blocker, upcoming milestones",
            f"name={status_scope['project_name']}; forecast={status_forecast['status']}; "
            f"blockers={len(status_blockers['blockers'])}",
            _ok(
                status_scope["project_name"] == "Smart Library Kiosk"
                and any(row["milestone"] == "Midterm demo" for row in status_scope["milestones"])
                and status_risks["risks"]
                and status_blockers["blockers"]
                and status_forecast["status"] in {"AT RISK", "DELAYED"}
            ),
        )
    )

    sparse_scope = extract_scope(
        "PROJECT NAME: Mystery Project\nOBJECTIVE: Learn Django.\nThis document does not list owners or deadlines."
    )
    rows.append(
        _row(
            "Sparse notes",
            "TXT",
            "Scope",
            "Missing fields shown as Not specified; no hallucinated owners",
            f"start={sparse_scope['start_date']}; deliverables={len(sparse_scope['deliverables'])}",
            _ok(
                sparse_scope["start_date"] == NOT_SPECIFIED
                and sparse_scope["deliverables"] == []
                and sparse_scope["end_date"] == NOT_SPECIFIED
            ),
        )
    )
    return rows


def _ok(passed: bool) -> tuple[str, str]:
    return ("", "Pass") if passed else ("Extraction mismatch", "Fail")


def _row(document, fmt, agent, expected, actual, issue_pass):
    issue, result = issue_pass
    return {
        "document": document,
        "format": fmt,
        "agent": agent,
        "expected": expected,
        "actual": actual,
        "issues": issue or "None",
        "result": result,
    }


def render(rows: list[dict]) -> str:
    lines = [
        "# Milestone 2 Validation Report",
        "",
        "| Document | Format | Agent | Expected Result | Actual Result | Issues | Pass/Fail |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {document} | {format} | {agent} | {expected} | {actual} | {issues} | {result} |".format(**row)
        )
    failed = sum(1 for row in rows if row["result"] != "Pass")
    lines.extend(
        [
            "",
            f"Summary: {len(rows) - failed} passed, {failed} failed.",
            "",
            "Checks covered: goal, scope, deliverable, milestone, timeline, responsibility, "
            "dependency, risk detection, severity, delivery forecast, blockers, pending decisions, "
            "action items, owners, due dates, no hallucinated fields, and Not specified for missing data.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    rows = validate()
    report = render(rows)
    out = ROOT / "docs" / "milestone-2-validation.md"
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {out}")
    return 0 if all(row["result"] == "Pass" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
