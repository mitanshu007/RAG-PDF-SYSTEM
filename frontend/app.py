from __future__ import annotations

import html
import re
import tempfile
from pathlib import Path

import streamlit as st

from frontend.api import ApiError, check_services, get_collection_stats, queue_query, upload_ingestion, wait_for_query
from frontend.styles import inject_styles


st.set_page_config(page_title="Nexa — Knowledge Workspace", page_icon="✦", layout="wide", initial_sidebar_state="expanded")
inject_styles()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "services" not in st.session_state:
    st.session_state.services = check_services()


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
        }
        selected = st.radio("Workspace", list(options), format_func=lambda x: options[x], label_visibility="collapsed")
        st.markdown("<div style='height:2rem'></div><div class='eyebrow'>Recent chats</div>", unsafe_allow_html=True)
        for title in ["WHO health system building blocks", "Service delivery notes", "Untitled exploration"]:
            st.markdown(f"<div style='color:#9ba8c1;padding:.55rem 0;border-bottom:1px solid #151d30;font-size:.78rem'>◌ &nbsp; {title}</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#9ba8c1;font-size:.8rem'>{icon('settings')} &nbsp; Settings</div>", unsafe_allow_html=True)
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
                    event_ids = upload_ingestion(saved, uploaded.name)
                    status.update(label="Ingestion queued in Inngest", state="complete")
                st.session_state.documents.insert(0, {"name": uploaded.name, "size": uploaded.size, "status": "Queued", "event": event_ids[0] if event_ids else "—"})
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
        st.markdown(f'<div class="card" style="margin:.6rem 0;display:flex;justify-content:space-between;align-items:center"><div><div style="font-size:1.4rem;color:#ff7b86">▤</div><strong>{html.escape(doc["name"])}</strong><div class="source-meta">{doc["size"] / 1024:.1f} KB · {doc["status"]} · event {doc["event"]}</div></div><div style="color:#67b3ff">Indexed</div></div>', unsafe_allow_html=True)


def chat_panel() -> None:
    st.markdown('<div class="eyebrow">AI chat · grounded mode</div><h2 style="margin:.25rem 0 .4rem">Ask your knowledge.</h2><div style="color:#8e9ab2;margin-bottom:1rem">Answers are retrieved from your indexed sources, then traced back to evidence.</div>', unsafe_allow_html=True)
    for message in st.session_state.messages:
        cls = "chat-user" if message["role"] == "user" else "chat-assistant"
        st.markdown(f'<div class="{cls}">{safe_markdown(message["content"])}</div>', unsafe_allow_html=True)
        if message.get("sources"):
            with st.expander(f"Evidence · {len(message['sources'])} source(s)"):
                for source in message["sources"]:
                    st.markdown(f'<div class="source"><div class="source-title">📄 {html.escape(Path(source).name)}</div><div class="source-meta">Retrieved context · local Qdrant</div></div>', unsafe_allow_html=True)
    question = st.chat_input("Ask about your documents…")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        try:
            with st.spinner("Tracing evidence through your knowledge graph…"):
                result = wait_for_query(queue_query(question))
            st.session_state.messages.append({"role": "assistant", "content": result.answer, "sources": result.sources})
        except ApiError as exc:
            st.session_state.messages.append({"role": "assistant", "content": f"Could not complete the query: {exc}"})
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
