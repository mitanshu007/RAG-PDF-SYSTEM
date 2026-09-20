from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    name: str | None
    provider: str | None


security = HTTPBearer(auto_error=False)


def _supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Supabase authentication is not configured.")
    return create_client(url, key)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
        )
    try:
        response = _supabase().auth.get_user(credentials.credentials)
        user = response.user
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired.",
        ) from exc
    if user is None:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")
    metadata = user.user_metadata or {}
    identities = user.identities or []
    provider = identities[0].provider if identities else None
    return AuthenticatedUser(
        user_id=str(user.id),
        email=user.email,
        name=metadata.get("full_name") or metadata.get("name"),
        provider=provider,
    )
