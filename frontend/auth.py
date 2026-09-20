from __future__ import annotations

import os
import time
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def client() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Supabase authentication is not configured.")
    return create_client(url, key)


def restore_session() -> dict[str, Any] | None:
    if "auth_session" in st.session_state:
        session = st.session_state.auth_session
        expires_at = session.get("expires_at")
        refresh_token = session.get("refresh_token")
        if (
            expires_at
            and refresh_token
            and float(expires_at) <= time.time() + 60
        ):
            refreshed = client().auth.refresh_session(refresh_token)
            if refreshed.session is None:
                st.session_state.pop("auth_session", None)
                return None
            session = refreshed.session.model_dump()
            st.session_state.auth_session = session
        return session
    code = st.query_params.get("code")
    if code:
        session = client().auth.exchange_code_for_session(
            {
                "auth_code": code,
                "redirect_to": os.getenv(
                    "SUPABASE_REDIRECT_URL", "http://localhost:8501"
                ),
            }
        )
        st.session_state.auth_session = session.model_dump()
        st.query_params.clear()
        return st.session_state.auth_session
    return None


def sign_in(provider: str) -> None:
    response = client().auth.sign_in_with_oauth(
        {
            "provider": provider,
            "options": {"redirect_to": os.getenv("SUPABASE_REDIRECT_URL", "http://localhost:8501")},
        }
    )
    st.markdown(f'<meta http-equiv="refresh" content="0;url={response.url}">', unsafe_allow_html=True)


def sign_out() -> None:
    client().auth.sign_out()
    st.session_state.pop("auth_session", None)
