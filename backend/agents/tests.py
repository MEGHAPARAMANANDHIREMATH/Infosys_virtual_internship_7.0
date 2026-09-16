from django.core.files.uploadedfile import SimpleUploadedFile

from agents.blocker_agent import extract_blockers
from agents.constants import NOT_SPECIFIED
from agents.risk_agent import detect_risks
from agents.scope_agent import extract_scope
from documents.test_helpers import PipelineTestCase

SOFTWARE_TEXT = """
PROJECT NAME: Campus Attendance Platform
OBJECTIVE: Build a QR-based attendance system for the computer science department.
SCOPE: In scope: student mobile check-in, faculty dashboard, and attendance reports.
START DATE: 2026-01-15
DEADLINE: 2026-06-30

DELIVERABLES
Deliverable | Owner | Deadline | Status
Mobile check-in app | Priya Sharma | 2026-03-15 | In progress

MILESTONES
Milestone | Date | Owner | Status
Beta release | 2026-05-01 | Priya Sharma | At risk

TASKS
Task | Owner | Deadline | Status | Depends On
Design API | Daniel Okonkwo | 2026-02-20 | Delayed | Requirements freeze

DEPENDENCIES
Dependency | Related Task | Status
University SSO credentials | Design API | Missing

RISKS
Schedule risk: Design API is delayed, which threatens the 2026-03-15 mobile app deadline.
Resource gap: No dedicated QA engineer is assigned.
"""

MEETING_TEXT = """
BLOCKERS
Blocker: Card reader SDK license not approved | Owner: Ananya Iyer | Priority: High | Status: Open

PENDING DECISIONS
Decision Required: Whether to use campus SSO or a local PIN | Responsible Person: Maya Chen | Due Date: 2026-09-18 | Status: Open

OPEN ISSUES
Issue: Kiosk printer jams during due-date slip tests | Owner: Luis Romero | Priority: Medium | Status: Open

ACTION ITEMS
Action Item: Send license reminder to finance | Owner: Ananya Iyer | Due Date: 2026-09-14 | Priority: High | Status: Open
"""

SPARSE_TEXT = """
PROJECT NAME: Mystery Project
OBJECTIVE: Learn Django.
This document does not list owners, deadlines, or deliverables.
"""


class GroundedAgentTests(PipelineTestCase):
    def test_scope_extraction(self):
        result = extract_scope(SOFTWARE_TEXT)
        self.assertEqual(result["project_name"], "Campus Attendance Platform")
        self.assertIn("QR-based attendance", result["objective"])
        self.assertIn("student mobile check-in", result["scope"])
        self.assertEqual(result["start_date"], "2026-01-15")
        self.assertEqual(result["end_date"], "2026-06-30")
        self.assertTrue(result["deliverables"])
        self.assertEqual(result["deliverables"][0]["owner"], "Priya Sharma")
        self.assertTrue(result["milestones"])
        self.assertTrue(result["tasks"])
        self.assertEqual(result["tasks"][0]["status"], "Delayed")
        self.assertTrue(result["dependencies"])

    def test_missing_fields_are_not_specified(self):
        result = extract_scope(SPARSE_TEXT)
        self.assertEqual(result["project_name"], "Mystery Project")
        self.assertEqual(result["start_date"], NOT_SPECIFIED)
        self.assertEqual(result["deliverables"], [])
        self.assertEqual(result["milestones"], [])

    def test_no_hallucinated_owner(self):
        result = extract_scope(SPARSE_TEXT)
        for row in result["responsibilities"]:
            self.assertNotEqual(row["name"].lower(), "john doe")
        blockers = extract_blockers(SPARSE_TEXT)
        for row in blockers["action_items"]:
            self.assertEqual(row["owner"], NOT_SPECIFIED)

    def test_risk_and_forecast(self):
        scope = extract_scope(SOFTWARE_TEXT)
        bundle = detect_risks(SOFTWARE_TEXT, scope)
        self.assertTrue(bundle["risks"])
        categories = {risk["category"] for risk in bundle["risks"]}
        self.assertTrue({"Delayed task", "Missing resource"} & categories)
        from agents.risk_agent import build_forecast

        forecast = build_forecast(SOFTWARE_TEXT, bundle["risks"], scope)
        self.assertIn(forecast["status"], {"AT RISK", "DELAYED"})
        for risk in bundle["risks"]:
            self.assertNotEqual(risk["evidence"], NOT_SPECIFIED)

    def test_blocker_extraction(self):
        result = extract_blockers(MEETING_TEXT)
        self.assertEqual(result["blockers"][0]["owner"], "Ananya Iyer")
        self.assertEqual(result["pending_decisions"][0]["responsible_person"], "Maya Chen")
        self.assertEqual(result["pending_decisions"][0]["due_date"], "2026-09-18")
        self.assertEqual(result["action_items"][0]["action_item"], "Send license reminder to finance")


class IntelligenceApiTests(PipelineTestCase):
    def test_run_all_agents(self):
        project = self.create_project("Intel")
        uploaded = SimpleUploadedFile(
            "plan.txt", SOFTWARE_TEXT.encode("utf-8"), content_type="text/plain"
        )
        upload = self.client.post(
            f"/api/projects/{project['id']}/documents/",
            {"file": uploaded},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201, upload.data)
        response = self.client.post(
            f"/api/projects/{project['id']}/intelligence/",
            {"document_id": upload.data["id"], "agents": "all"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["file_name"], "plan.txt")
        self.assertIsNotNone(response.data["scope"])
        self.assertTrue(response.data["risks"])
        self.assertIn(response.data["forecast"]["status"], {"ON TRACK", "AT RISK", "DELAYED"})
        self.assertEqual(
            response.data["agents_run"],
            ["scope", "risk", "blockers"],
        )

    def test_invalid_file_on_intelligence(self):
        project = self.create_project("Bad")
        uploaded = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post(
            f"/api/projects/{project['id']}/intelligence/",
            {"file": uploaded, "agents": "scope"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file format", response.data["error"])

    def test_missing_document_returns_error(self):
        project = self.create_project("None")
        response = self.client.post(
            f"/api/projects/{project['id']}/intelligence/",
            {"agents": "scope"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("document_id", response.data["error"])

    def test_scope_agent_only(self):
        project = self.create_project("ScopeOnly")
        uploaded = SimpleUploadedFile(
            "sparse.txt", SPARSE_TEXT.encode("utf-8"), content_type="text/plain"
        )
        upload = self.client.post(
            f"/api/projects/{project['id']}/documents/",
            {"file": uploaded},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201, upload.data)
        response = self.client.post(
            f"/api/projects/{project['id']}/intelligence/",
            {"document_id": upload.data["id"], "agents": "scope"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["agents_run"], ["scope"])
        self.assertEqual(response.data["scope"]["project_name"], "Mystery Project")
        self.assertIsNone(response.data["risks"])
        self.assertEqual(response.data["scope"]["start_date"], NOT_SPECIFIED)
