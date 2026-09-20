import importlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


app_module = importlib.import_module("reg.app")


class IngestionEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app_module.app)

    def test_rejects_an_empty_filename(self) -> None:
        response = self.client.post("/ingest-pdf?filename=")

        self.assertEqual(response.status_code, 422)

    def test_root_redirects_to_api_docs(self) -> None:
        response = self.client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers["location"], "/docs")

    def test_returns_service_unavailable_when_event_service_fails(self) -> None:
        with patch.object(
            app_module.inngest_client,
            "send",
            AsyncMock(side_effect=ConnectionError("offline")),
        ):
            response = self.client.post("/ingest-pdf?filename=test.pdf")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"detail": "The ingestion event service is unavailable."},
        )
