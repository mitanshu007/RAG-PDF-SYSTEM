from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


API_URL = os.getenv("RAG_API_URL", "http://localhost:8000").rstrip("/")
INNGEST_URL = os.getenv("INNGEST_URL", "http://localhost:8288").rstrip("/")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
EVENT_KEY = os.getenv("INNGEST_EVENT_KEY", "NO_EVENT_KEY_SET")


def set_access_token(token: str | None) -> None:
    global ACCESS_TOKEN
    ACCESS_TOKEN = token


ACCESS_TOKEN: str | None = None


class ApiError(RuntimeError):
    """Raised when a local service returns an unusable response."""


@dataclass
class QueryResult:
    answer: str
    sources: list[str]
    num_contexts: int


@dataclass
class IngestionResult:
    event_ids: list[str]
    document_id: str
    filename: str
    status: str


def _request(url: str, *, method: str = "GET", payload: object | None = None, parse_json: bool = True) -> dict:
    body = None
    headers = {"Accept": "application/json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = "Bearer " + ACCESS_TOKEN
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ApiError(f"Unable to reach local service: {exc}") from exc
    if not parse_json:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError("The local service returned an invalid response.") from exc


def queue_ingestion(path: Path) -> list[str]:
    response = _request(
        f"{API_URL}/ingest-pdf?filename={quote(str(path), safe='')}",
        method="POST",
    )
    return [str(event_id) for event_id in response.get("event_ids", [])]


def upload_ingestion(path: Path, filename: str) -> IngestionResult:
    boundary = "----NexaUploadBoundary"
    content = path.read_bytes()
    multipart = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = Request(
        f"{API_URL}/upload-pdf",
        data=multipart,
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    if ACCESS_TOKEN:
        request.add_header("Authorization", "Bearer " + ACCESS_TOKEN)
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError(f"Unable to upload PDF: {exc}") from exc
    return IngestionResult(
        event_ids=[str(event_id) for event_id in result.get("event_ids", [])],
        document_id=str(result["document_id"]),
        filename=str(result.get("filename", filename)),
        status=str(result.get("status", "queued")),
    )


def get_document_status(document_id: str) -> dict[str, str]:
    return {
        key: str(value)
        for key, value in _request(f"{API_URL}/documents/{document_id}").items()
    }


def get_settings() -> dict[str, object]:
    return _request(f"{API_URL}/settings").get("settings", {})


def save_settings(settings: dict[str, object]) -> None:
    _request(f"{API_URL}/settings", method="PUT", payload=settings)


def queue_query(
    question: str,
    document_id: str,
    top_k: int = 5,
    response_style: str = "Grounded and concise",
) -> str:
    response = _request(
        f"{API_URL}/query",
        method="POST",
        payload={
            "question": question,
            "document_id": document_id,
            "top_k": top_k,
            "response_style": response_style,
        },
    )
    ids = response.get("event_ids", [])
    if not ids:
        raise ApiError("Inngest did not return a query event ID.")
    return str(ids[0])


def get_query_result(event_id: str) -> QueryResult | None:
    query = """
    query GetEvent($id: ID!) {
      event(query: {eventId: $id}) {
        status
        functionRuns {
          status
          output
          function { name }
        }
      }
    }
    """
    response = _request(
        f"{INNGEST_URL}/v0/gql",
        method="POST",
        payload={"query": query, "variables": {"id": event_id}},
    )
    event = (response.get("data") or {}).get("event") or {}
    if event.get("status") == "FAILED":
        raise ApiError("The RAG query failed in Inngest.")
    for run in event.get("functionRuns", []):
        if run.get("function", {}).get("name") != "RAG: Query":
            continue
        if run.get("status") == "FAILED":
            raise ApiError("The RAG query function failed in Inngest.")
        if run.get("status") != "COMPLETED" or not run.get("output"):
            continue
        try:
            output = json.loads(run["output"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ApiError("The RAG query returned malformed output.") from exc
        return QueryResult(
            answer=str(output.get("answer", "")),
            sources=[str(source) for source in output.get("sources", [])],
            num_contexts=int(output.get("num_contexts", 0)),
        )
    return None


def wait_for_query(event_id: str, timeout: float = 90) -> QueryResult:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = get_query_result(event_id)
        if result is not None:
            return result
        time.sleep(1.5)
    raise ApiError("The query is still processing. Check Inngest and retry shortly.")


def check_services() -> dict[str, bool]:
    services = {}
    for name, url in {
        "FastAPI": f"{API_URL}/api/inngest",
        "Inngest": INNGEST_URL,
    }.items():
        try:
            _request(url, parse_json=False)
            services[name] = True
        except ApiError:
            services[name] = False
    try:
        _request(f"{QDRANT_URL}/collections")
        services["Qdrant"] = True
    except ApiError:
        services["Qdrant"] = False
    return services


def get_collection_stats() -> int | None:
    try:
        response = _request(f"{QDRANT_URL}/collections/docs")
    except ApiError:
        return None
    result = response.get("result") or {}
    points_count = result.get("points_count")
    return int(points_count) if points_count is not None else None
