import importlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from auth import AuthenticatedUser, get_current_user


app_module = importlib.import_module("reg.app")


class IngestionEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        app_module.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            user_id="00000000-0000-0000-0000-000000000001",
            email="test@example.com",
            name="Test User",
            provider="test",
        )
        self.client = TestClient(app_module.app)

    def tearDown(self) -> None:
        app_module.app.dependency_overrides.clear()

    def test_rejects_an_empty_filename(self) -> None:
        response = self.client.post("/ingest-pdf?filename=")

        self.assertEqual(response.status_code, 422)

    def test_root_redirects_to_api_docs(self) -> None:
        response = self.client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/docs")

    def test_returns_service_unavailable_when_event_service_fails(self) -> None:
        with patch.object(app_module, "ensure_user"), patch.object(
            app_module, "create_document"
        ), patch.object(
            app_module.inngest_client, "send", AsyncMock(side_effect=ConnectionError("offline"))
        ):
            response = self.client.post("/ingest-pdf?filename=test.pdf")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "The ingestion event service is unavailable."},
        )

    def test_upload_returns_document_identity(self) -> None:
        with patch.object(app_module, "ensure_user"), patch.object(
            app_module, "create_document"
        ), patch.object(
            app_module.inngest_client, "send", AsyncMock(return_value=["event-1"])
        ):
            response = self.client.post(
                "/upload-pdf",
                files={"file": ("notes.pdf", b"%PDF-1.4 test", "application/pdf")},
            )

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertTrue(body["document_id"])
        self.assertEqual(body["filename"], "notes.pdf")
        self.assertEqual(body["status"], "queued")
