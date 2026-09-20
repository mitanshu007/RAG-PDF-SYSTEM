from __future__ import annotations

import os
from typing import Any

from supabase import Client, create_client


def database() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Supabase persistence is not configured.")
    return create_client(url, key)


def ensure_user(user_id: str, email: str | None, name: str | None, provider: str | None) -> None:
    database().table("profiles").upsert(
        {
            "id": user_id,
            "email": email,
            "full_name": name,
            "provider": provider,
        }
    ).execute()


def create_document(user_id: str, document_id: str, filename: str, status: str) -> None:
    database().table("documents").insert(
        {
            "id": document_id,
            "user_id": user_id,
            "filename": filename,
            "status": status,
        }
    ).execute()


def update_document(document_id: str, user_id: str, status: str) -> None:
    database().table("documents").update({"status": status}).eq(
        "id", document_id
    ).eq("user_id", user_id).execute()


def get_document(document_id: str, user_id: str) -> dict[str, Any] | None:
    response = database().table("documents").select("*").eq(
        "id", document_id
    ).eq("user_id", user_id).maybe_single().execute()
    return response.data


def get_settings(user_id: str) -> dict[str, Any]:
    return load_settings(user_id)


def save_settings(user_id: str, settings: dict[str, Any]) -> None:
    database().table("user_settings").upsert(
        {"user_id": user_id, "settings": settings}
    ).execute()


def load_settings(user_id: str) -> dict[str, Any]:
    response = database().table("user_settings").select("settings").eq(
        "user_id", user_id
    ).maybe_single().execute()
    return (response.data or {}).get("settings", {})
