from __future__ import annotations

import html
import re
import tempfile
from pathlib import Path

import streamlit as st

from frontend.api import (
    ApiError,
    check_services,
    get_collection_stats,
    get_document_status,
    queue_query,
    upload_ingestion,
    wait_for_query,
)
from frontend.styles import inject_styles


st.set_page_config(page_title="Nexa — Knowledge Workspace", page_icon="✦", layout="wide", initial_sidebar_state="expanded")
inject_styles()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "active_document_id" not in st.session_state:
    st.session_state.active_document_id = None
if "pending_document_id" not in st.session_state:
    st.session_state.pending_document_id = None
if "services" not in st.session_state:
    st.session_state.services = check_services()
if "response_style" not in st.session_state:
    st.session_state.response_style = "Grounded and concise"
if "retrieval_top_k" not in st.session_state:
    st.session_state.retrieval_top_k = 5
if "show_sources" not in st.session_state:
    st.session_state.show_sources = True
if "chat_history_enabled" not in st.session_state:
    st.session_state.chat_history_enabled = True
if "strict_document_mode" not in st.session_state:
    st.session_state.strict_document_mode = True


def icon(name: str) -> str:
    icons = {"home":"⌂", "docs":"▣", "chat":"✦", "layers":"◈", "settings":"⚙", "plus":"＋", "search":"⌕"}
    return icons.get(name, "•")


def safe_markdown(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = text.replace("\n", "<br>")
    return text


def sidebar() -> str:
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark"></div><div><div class="brand-name">NEXA</div><div class="brand-sub">knowledge workspace</div></div></div>', unsafe_allow_html=True)
        if st.button(f"{icon('plus')}  New chat", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)
        options = {
            "Overview": f"{icon('home')}  Overview",
            "Documents": f"{icon('docs')}  Documents",
            "AI Chat": f"{icon('chat')}  AI Chat",
            "Collections": f"{icon('layers')}  Collections",
            "Settings": f"{icon('settings')}  Settings",
        }
        selected = st.radio("Workspace", list(options), format_func=lambda x: options[x], label_visibility="collapsed")
        st.markdown("<div style='height:2rem'></div><div class='eyebrow'>Recent chats</div>", unsafe_allow_html=True)
        for title in ["WHO health system building blocks", "Service delivery notes", "Untitled exploration"]:
            st.markdown(f"<div style='color:#9ba8c1;padding:.55rem 0;border-bottom:1px solid #151d30;font-size:.78rem'>◌ &nbsp; {title}</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        statuses = "".join(f"<div style='color:{'#6fe3ad' if ok else '#ff8f9b'};font-size:.68rem;margin-top:.45rem'>● {name}</div>" for name, ok in st.session_state.services.items())
        st.markdown(f"<div style='margin-top:1.5rem'><div class='eyebrow'>System status</div>{statuses}</div>", unsafe_allow_html=True)
    return selected


def render_graph() -> None:
    st.markdown(
        '<div class="card"><div class="eyebrow">Knowledge graph</div><div class="graph">'
        '<div class="node">DOCUMENTS</div><div class="arrow">↓</div><div class="node">CHUNKS</div><div class="arrow">↓</div>'
        '<div class="node">EMBEDDINGS</div><div class="arrow">↓</div><div class="node">KNOWLEDGE</div><div class="arrow">↓</div><div class="node">AI</div>'
        '</div></div>', unsafe_allow_html=True,
    )


def upload_panel() -> None:
    st.markdown('<div class="eyebrow">Ingest a source</div><h2 style="margin:.25rem 0 .6rem">Turn a PDF into a living answer layer.</h2>', unsafe_allow_html=True)
    st.markdown('<div class="dropzone"><div style="font-size:2rem;color:#75baff">↥</div><div class="dropzone-title">Drop a PDF into the workspace</div><div class="dropzone-copy">Files stay on your local RAG stack. No keys leave your machine.</div></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
    if uploaded:
        if st.button("Start ingestion  →", type="primary", use_container_width=True):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="nexa-") as handle:
                    handle.write(uploaded.getbuffer())
                    saved = Path(handle.name)
                with st.status("Building your knowledge layer…", expanded=True) as status:
                    for stage in ["PDF", "EXTRACT", "CHUNK", "EMBED", "QDRANT", "READY"]:
                        st.write(f"◉ {stage}")
                    ingestion = upload_ingestion(saved, uploaded.name)
                    status.update(label="Ingestion queued in Inngest", state="complete")
                document = {
                    "name": ingestion.filename,
                    "size": uploaded.size,
                    "status": ingestion.status,
                    "event": ingestion.event_ids[0] if ingestion.event_ids else "—",
                    "document_id": ingestion.document_id,
                }
                st.session_state.documents.insert(0, document)
                st.session_state.active_document_id = None
                st.session_state.pending_document_id = ingestion.document_id
                st.success("Your PDF is queued. Watch the pipeline in Inngest or continue exploring.")
            except ApiError as exc:
                st.error(str(exc))
                st.button("Retry", key="retry_upload")


def documents_panel() -> None:
    st.markdown('<div class="eyebrow">Document library</div><h2 style="margin:.25rem 0 1rem">Your sources</h2>', unsafe_allow_html=True)
    query = st.text_input("Search documents", placeholder="Filter your knowledge base…", label_visibility="collapsed")
    docs = [doc for doc in st.session_state.documents if not query or query.lower() in doc["name"].lower()]
    if not docs:
        st.markdown('<div class="card" style="text-align:center;padding:2.2rem"><div style="font-size:2rem">⌁</div><h3>Your library is quiet.</h3><div style="color:#8b97ad">Upload your first document to start asking questions.</div></div>', unsafe_allow_html=True)
        return
    for doc in docs:
        try:
            current_status = get_document_status(doc["document_id"])["status"]
            doc["status"] = current_status
        except ApiError:
            current_status = doc["status"]
        if current_status == "ready" and st.session_state.active_document_id is None:
            st.session_state.active_document_id = doc["document_id"]
            if st.session_state.pending_document_id == doc["document_id"]:
                st.session_state.pending_document_id = None
        active = st.session_state.active_document_id == doc["document_id"]
        if st.button(
            f"{'● ' if active else ''}{doc['name']} · {current_status}",
            key=f"select-{doc['document_id']}",
            use_container_width=True,
        ):
            if current_status != "ready":
                st.warning("This PDF is still being processed. Please wait until ingestion is complete.")
            else:
                st.session_state.active_document_id = doc["document_id"]
                st.rerun()


def chat_panel() -> None:
    pending_id = st.session_state.pending_document_id
    if st.session_state.active_document_id is None and pending_id:
        try:
            pending_status = get_document_status(pending_id)
            pending_doc = next(
                (doc for doc in st.session_state.documents if doc["document_id"] == pending_id),
                None,
            )
            if pending_doc:
                pending_doc["status"] = pending_status["status"]
            if pending_status["status"] == "ready":
                st.session_state.active_document_id = pending_id
                st.session_state.pending_document_id = None
            elif pending_status["status"] not in {"queued", "processing"}:
                st.session_state.pending_document_id = None
        except ApiError:
            pass

    active_id = st.session_state.active_document_id
    active_document = next(
        (doc for doc in st.session_state.documents if doc["document_id"] == active_id),
        None,
    )
    if active_document:
        st.caption(f"Chatting with: {active_document['name']} · {active_document['status']}")
    elif pending_id:
        st.warning("This PDF is still being processed. Please wait until ingestion is complete.")
    else:
        st.info("Please upload a PDF first.")
    st.markdown('<div class="eyebrow">AI chat · grounded mode</div><h2 style="margin:.25rem 0 .4rem">Ask your knowledge.</h2><div style="color:#8e9ab2;margin-bottom:1rem">Answers are retrieved from your indexed sources, then traced back to evidence.</div>', unsafe_allow_html=True)
    for message in st.session_state.messages:
        cls = "chat-user" if message["role"] == "user" else "chat-assistant"
        st.markdown(f'<div class="{cls}">{safe_markdown(message["content"])}</div>', unsafe_allow_html=True)
        if message.get("sources") and st.session_state.show_sources:
            with st.expander(f"Evidence · {len(message['sources'])} source(s)"):
                for source in message["sources"]:
                    st.markdown(f'<div class="source"><div class="source-title">📄 {html.escape(Path(source).name)}</div><div class="source-meta">Retrieved context · local Qdrant</div></div>', unsafe_allow_html=True)
    question = st.chat_input("Ask about your documents…")
    if question:
        if not active_document:
            st.warning("Please upload a PDF first.")
            return
        try:
            active_status = get_document_status(active_id)["status"]
        except ApiError:
            st.error("Document not found. Please upload the PDF again.")
            return
        if active_status != "ready":
            st.warning("This PDF is still being processed. Please wait until ingestion is complete.")
            return
        st.session_state.messages.append({"role": "user", "content": question})
        try:
            with st.spinner("Tracing evidence through your knowledge graph…"):
                result = wait_for_query(
                    queue_query(
                        question,
                        active_id,
                        st.session_state.retrieval_top_k,
                        st.session_state.response_style,
                    )
                )
            st.session_state.messages.append({"role": "assistant", "content": result.answer, "sources": result.sources})
            if not st.session_state.chat_history_enabled:
                st.session_state.messages = st.session_state.messages[-2:]
        except ApiError as exc:
            st.session_state.messages.append({"role": "assistant", "content": f"Could not complete the query: {exc}"})
        st.rerun()


def settings_panel() -> None:
    st.markdown(
        '<div class="eyebrow">Workspace settings</div>'
        '<h1 class="hero-title"><span>Shape your workspace.</span></h1>'
        '<p class="hero-copy">These preferences are local to this Streamlit session. '
        'Authentication and multi-user persistence are not configured.</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("### Account")
        st.markdown("**Local workspace**")
        st.caption("No authentication provider is configured. Documents and preferences belong to this browser session.")
        if st.button("Clear local session", type="secondary"):
            for key in ("messages", "documents", "active_document_id", "pending_document_id"):
                st.session_state[key] = [] if key in {"messages", "documents"} else None
            st.success("The local workspace session was cleared.")
            st.rerun()

    with st.container(border=True):
        st.markdown("### Appearance")
        st.selectbox(
            "Theme",
            ["Dark mode", "System mode", "Light mode"],
            index=0,
            disabled=True,
            help="NEXA currently ships with its dark obsidian theme.",
        )

    with st.container(border=True):
        st.markdown("### Chat settings")
        st.selectbox(
            "Response style",
            ["Grounded and concise", "Detailed", "Bullet points"],
            key="response_style",
        )
        st.slider("Retrieved chunks", 1, 10, key="retrieval_top_k")
        st.toggle("Show sources and evidence", key="show_sources")
        st.toggle("Keep chat history", key="chat_history_enabled")

    with st.container(border=True):
        st.markdown("### Knowledge and RAG")
        st.toggle(
            "Strict document-only mode",
            key="strict_document_mode",
            disabled=True,
            help="Always enforced by the backend document_id filter.",
        )
        st.toggle(
            "Show page and source references",
            value=st.session_state.show_sources,
            key="show_page_references",
        )
        st.caption("Similarity threshold is not supported by the current Qdrant search implementation.")

    with st.container(border=True):
        st.markdown("### Application status")
        for name, healthy in st.session_state.services.items():
            st.write(f"{'●' if healthy else '○'} {name}: {'Connected' if healthy else 'Unavailable'}")
        st.caption("NEXA 0.1.0 · local session mode")

    with st.container(border=True):
        st.markdown("### Danger zone")
        st.warning("Document deletion is unavailable because the backend has no document-delete endpoint.")
        if st.button("Clear current conversation", type="secondary"):
            st.session_state.messages = []
            st.success("Conversation cleared.")
            st.rerun()


section = sidebar()
if section == "AI Chat":
    chat_panel()
elif section == "Documents":
    upload_panel()
    st.divider()
    documents_panel()
elif section == "Collections":
    st.markdown('<div class="eyebrow">Collections</div><h1 class="hero-title"><span>One source of truth.</span></h1><p class="hero-copy">Your local collection is connected to Qdrant and ready for grounded retrieval.</p>', unsafe_allow_html=True)
    render_graph()
elif section == "Settings":
    settings_panel()
else:
    st.markdown('<div class="eyebrow">Good afternoon · local workspace</div><h1 class="hero-title">Your knowledge<br><span>is waiting.</span></h1><p class="hero-copy">Nexa turns your documents into a private, searchable answer layer. Upload a source, let the pipeline do the quiet work, then ask better questions.</p>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([1.45, .8], gap="large")
    with left:
        upload_panel()
    with right:
        render_graph()
        point_count = get_collection_stats()
        count_label = str(point_count) if point_count is not None else "—"
        st.markdown(f'<div style="height:.8rem"></div><div class="card"><div class="metric">{count_label}</div><div class="metric-label">indexed knowledge points</div><div style="color:#6fe3ad;font-size:.75rem;margin-top:.8rem">● Qdrant connected · 384d local embeddings</div></div>', unsafe_allow_html=True)
    st.divider()
    documents_panel()
