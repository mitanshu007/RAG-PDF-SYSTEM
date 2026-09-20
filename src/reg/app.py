"""FastAPI application and Inngest workflow definitions."""

import logging
import os
import re
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5
from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStore
from custom_types import RAQQueryResult, RAGSearchResult, RAGUpsertResult, RAGChunkAndSrc

import inngest
import inngest.fast_api
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from inngest.experimental import ai

load_dotenv()

logger = logging.getLogger(__name__)

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logger,
    is_production=os.getenv("INNGEST_ENV", "development").strip().lower() == "production",
    # Send local-development events to the Inngest dev server by default.
    event_api_base_url=os.getenv("INNGEST_EVENT_API_BASE_URL", "http://localhost:8288"),
    serializer=inngest.PydanticSerializer(),
)


@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
)
async def ingest_pdf(ctx: inngest.Context) -> dict[str, object]:
    """Load, embed, and store the chunks from a queued PDF ingestion event."""
    def _load() -> RAGChunkAndSrc:
        pdf_path = ctx.event.data["pdf_path"]
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        source_id = ctx.event.data.get("source_id", pdf_path)
        chunks = load_and_chunk_pdf(pdf_path)
        return RAGChunkAndSrc(chunks=chunks, source_id=source_id)

    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id
        vecs = embed_texts(chunks)
        ids = [str(uuid5(NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        payloads = [{"source": source_id, "text": chunks[i]} for i in range(len(chunks))]
        QdrantStore().upsert(ids, vecs, payloads)
        return RAGUpsertResult(ingested=len(chunks))

    chunk_and_src = await ctx.step.run(
        "load-and-chunk", _load, output_type=RAGChunkAndSrc
    )
    ingested = await ctx.step.run(
        "embed-and-upsert",
        _upsert,
        chunk_and_src,
        output_type=RAGUpsertResult,
    )
    return ingested.model_dump()

@inngest_client.create_function(
    fn_id="RAG: Query",
    trigger=inngest.TriggerEvent(event="rag/query"),
)
async def rag_query(ctx: inngest.Context) -> dict[str, object]:
    """Search indexed chunks and generate an answer grounded in that context."""
    question = str(ctx.event.data.get("question", "")).strip()
    if not question:
        raise ValueError("The query event requires a non-empty 'question'.")

    top_k = int(ctx.event.data.get("top_k", 5))

    def _search() -> RAGSearchResult:
        query_vector = embed_texts([question])[0]
        return RAGSearchResult(**QdrantStore().search(query_vector, top_k))

    found = await ctx.step.run(
        "embed-and-search", _search, output_type=RAGSearchResult
    )
    context_block = "\n\n".join(found.content)
    user_context = f"Question: {question}\n\nContext:\n{context_block}"
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    llm_model = os.getenv("LLM_MODEL", "").strip()
    enable_openai = os.getenv("ENABLE_OPENAI", "false").strip().lower() in ("true", "1", "yes")

    # Determine adapter: Groq (free), custom base_url, or standard OpenAI if explicitly enabled
    adapter = None
    if groq_api_key:
        adapter = ai.openai.Adapter(
            auth_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model=llm_model or "openai/gpt-oss-120b",
        )
    elif openai_base_url and openai_api_key:
        adapter = ai.openai.Adapter(
            auth_key=openai_api_key,
            base_url=openai_base_url,
            model=llm_model or "gpt-4o-mini",
        )
    elif enable_openai and openai_api_key:
        adapter = ai.openai.Adapter(
            auth_key=openai_api_key,
            model=llm_model or "gpt-4o-mini",
        )

    if adapter is not None:
        response = await ctx.step.ai.infer(
            "llm-response",
            adapter=adapter,
            body={
                "max_tokens": 1024,
                "temperature": 0.2,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer questions using only the provided context. "
                            "If the answer is not in the context, say 'I don't know'."
                        ),
                    },
                    {"role": "user", "content": user_context},
                ],
            },
        )
        answer = str(response["choices"][0]["message"]["content"]).strip()
    else:
        # Free local synthesis from retrieved context without external paid API
        def _synthesize() -> str:
            if not found.content:
                return "I don't know. No relevant context found in indexed documents."
            summary = "\n\n".join(f"- {c.strip()}" for c in found.content)
            return f"Answer grounded in retrieved context:\n\n{summary}"

        answer = await ctx.step.run("local-synthesis", _synthesize)

    return RAQQueryResult(
        answer=answer,
        sources=found.source,
        num_contexts=len(found.content),
    ).model_dump()



app = FastAPI(title="RAG Ingestion API")
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Send browser visits to the interactive API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest-pdf", status_code=status.HTTP_202_ACCEPTED)
async def start_pdf_ingestion(
    filename: str = Query(default="example.pdf", min_length=1),
) -> dict[str, object]:
    """Queue a PDF ingestion workflow and return its Inngest event IDs."""
    cleaned_filename = filename.strip()
    if not cleaned_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename must be a non-empty string.",
        )

    event = inngest.Event(
        name="rag/ingest_pdf",
        data={"pdf_path": cleaned_filename, "request_id": str(uuid4())},
    )

    try:
        event_ids = await inngest_client.send(event)
    except Exception as exc:
        logger.exception("Unable to queue PDF ingestion for %s", cleaned_filename)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The ingestion event service is unavailable.",
        ) from exc

    return {"event_ids": event_ids, "message": "PDF ingestion started"}


@app.post("/upload-pdf", status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(file: UploadFile = File(...)) -> dict[str, object]:
    """Persist an uploaded PDF locally and queue the existing ingestion workflow."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are supported.",
        )

    upload_dir = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(file.filename).name)
    saved_path = upload_dir / f"{uuid4()}-{safe_name}"
    try:
        saved_path.write_bytes(await file.read())
        event_ids = await inngest_client.send(
            inngest.Event(
                name="rag/ingest_pdf",
                data={"pdf_path": str(saved_path), "source_id": file.filename},
            )
        )
    except Exception as exc:
        saved_path.unlink(missing_ok=True)
        logger.exception("Unable to queue uploaded PDF %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The ingestion event service is unavailable.",
        ) from exc

    return {"event_ids": event_ids, "message": "PDF ingestion started"}


inngest.fast_api.serve(app, inngest_client, [ingest_pdf, rag_query])


def main() -> None:
    """Run the service for the installed ``reg`` command."""
    uvicorn.run(
        "reg.app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
