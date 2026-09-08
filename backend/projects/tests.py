from documents.test_helpers import PipelineTestCase


class ProjectApiTests(PipelineTestCase):
    def test_create_project(self):
        data = self.create_project("Campus Portal")
        self.assertEqual(data["name"], "Campus Portal")
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["created_by"], "anonymous")
        self.assertIn("id", data)
        self.assertIn("created_at", data)

    def test_retrieve_project(self):
        created = self.create_project("Retrieve Me")
        response = self.client.get(f"/api/projects/{created['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Retrieve Me")

    def test_update_project(self):
        created = self.create_project("Old Name")
        response = self.client.put(
            f"/api/projects/{created['id']}/",
            {
                "name": "New Name",
                "description": "Updated",
                "start_date": "2026-02-01",
                "end_date": "2026-11-01",
                "status": "ON_HOLD",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "New Name")
        self.assertEqual(response.data["status"], "ON_HOLD")

    def test_invalid_project_returns_404(self):
        response = self.client.get("/api/projects/99999/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)

    def test_unauthorized_project_access(self):
        created = self.create_project("Private")
        with self.settings(ENFORCE_PROJECT_ACCESS=True):
            response = self.client.get(
                f"/api/projects/{created['id']}/",
                HTTP_X_USER_ID="someone-else",
            )
        self.assertEqual(response.status_code, 403)
