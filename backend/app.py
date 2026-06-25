"""
FastAPI application entry point for Hyundai Knowledge Assistant.

This file wires together:
  - Startup: SQLite init + ChromaDB FAQ ingestion (lifespan)
  - POST /chat: main chatbot pipeline (clarification → context → search → log)
  - GET /health, GET /stats: monitoring endpoints
  - Routers: auth, bookings, admin, session

Read this file after context_service.py and chroma_db.py to see the full request flow.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth_utils import get_optional_user
from booking_service import get_next_available_slots
from chat_log_service import log_chat_interaction
from email_service import email_configured
from chroma_db import vector_store
from config import CORS_ORIGINS, FRONTEND_DIST
from database import get_db, init_db
from models import User
from routers.auth_router import router as auth_router
from routers.bookings_router import router as bookings_router
from routers.admin_router import router as admin_router
from context_service import (
    clarification_message,
    coerce_context,
    default_context,
    enrich_search_query,
    is_low_signal_query,
    mentions_unknown_vehicle,
    needs_clarification,
    normalize_message,
    prepare_clarification_context,
    resolve_query,
    unknown_vehicle_message,
    update_context,
)
from routers.session_router import router as session_router
from session_service import (
    apply_exchange_to_session,
    get_session,
    get_session_context,
    save_session_context,
)
from slot_intent import is_slot_availability_query
from suggestions import get_follow_up_suggestions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Do NOT block before yield — Render detects an open port only after startup.
    All heavy work (SQLite + ChromaDB + embeddings) runs in a background task.
    """
    logger.info("Lifespan start — PORT=%s", os.getenv("PORT", "not set"))

    async def _background_boot() -> None:
        try:
            logger.info("Background boot: initializing database...")
            await asyncio.to_thread(init_db)
            logger.info("Background boot: initializing knowledge base...")
            if os.getenv("LIGHTWEIGHT_MODE", "false").lower() == "true":
                logger.info("LIGHTWEIGHT_MODE enabled — keyword search only (no PyTorch)")
            await asyncio.to_thread(vector_store.initialize_safe)
            if vector_store.is_initialized:
                logger.info("Knowledge base ready.")
            elif vector_store.init_error:
                logger.error("Knowledge base failed: %s", vector_store.init_error)
        except Exception:
            logger.exception("Background boot failed")

    boot_task = asyncio.create_task(_background_boot())
    yield  # uvicorn binds to PORT here — Render deploy succeeds
    boot_task.cancel()
    logger.info("Shutting down backend.")


# FastAPI app instance — title/description appear in auto-generated docs at /docs
app = FastAPI(
    title="Hyundai Knowledge Assistant",
    description="Semantic FAQ retrieval, auth, and test drive bookings.",
    version="2.2.0",
    lifespan=lifespan,
)
logger.info("FastAPI app created — uvicorn will bind to PORT next")

# CORS: local dev + Vercel frontend (direct calls if not using /api proxy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS if origin.strip()],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules — each router defines its own prefix (/auth, /bookings, etc.)
app.include_router(auth_router)
app.include_router(bookings_router)
app.include_router(admin_router)
app.include_router(session_router)


# --- Pydantic models: define JSON request/response shapes (auto-validated by FastAPI) ---

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question")
    used_suggestion_ids: list[str] = Field(default_factory=list)
    session_id: str | None = Field(default=None, description="Active chat session for context")
    client_context: dict | None = Field(
        default=None,
        description="Guest chat context round-trip (last_vehicle, last_topic)",
    )


class SuggestionItem(BaseModel):
    label: str
    action: str
    query: str | None = None
    vehicle: str | None = None
    id: str | None = None


class AvailableSlotItem(BaseModel):
    slot_number: int
    date: str
    time: str
    time_label: str
    day_label: str


class ChatResponse(BaseModel):
    answer: str
    found: bool
    response_type: str = "faq"  # faq | slots | clarification
    suggestions: list[SuggestionItem] = []
    available_slots: list[AvailableSlotItem] = []
    resolved_query: str | None = None  # expanded query after context resolution
    context: dict | None = None  # updated session context returned to frontend


class StatsResponse(BaseModel):
    total_faqs_loaded: int
    chroma_document_count: int
    embedding_model: str
    chroma_status: str
    similarity_threshold: float
    excel_path: str


@app.get("/health")
async def health_check():
    """Lightweight health check — responds immediately while KB loads in background."""
    if vector_store.init_error:
        kb_status = "error"
    elif vector_store.is_initialized:
        kb_status = "ready"
    elif vector_store.is_initializing:
        kb_status = "initializing"
    else:
        kb_status = "pending"

    return {
        "status": "ok",
        "version": "2.2.0",
        "knowledge_base": kb_status,
        "knowledge_base_error": vector_store.init_error,
        "auth": True,
        "bookings": True,
        "email_configured": email_configured(),
    }


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """FAQ count, ChromaDB status — shown in Knowledge Panel on frontend."""
    try:
        return vector_store.get_stats()
    except Exception as exc:
        logger.exception("Failed to fetch stats")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),  # Injected DB session — closed automatically after request
    current_user: User | None = Depends(get_optional_user),  # None if guest (no JWT)
):
    """
    Main chat endpoint. Pipeline:
      1. Normalize typos
      2. Load session context (if logged in)
      3. Clarification check (vague query without car model)
      4. Resolve query with context (e.g. 'its mileage' → 'Creta mileage')
      5. Slot intent OR semantic FAQ search
      6. Log interaction + update session context
    """
    try:
        if not vector_store.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Knowledge base is initializing. Please try again in a moment.",
            )

        original = normalize_message(request.message.strip())
        used_ids = request.used_suggestion_ids
        session_id = request.session_id
        message = original

        # Load context: logged-in users from DB; guests from client_context round-trip
        session_ctx: dict = {}
        session = None
        if current_user and session_id:
            session = get_session(db, current_user, session_id)
            session_ctx = get_session_context(session)
        else:
            session_ctx = coerce_context(request.client_context)

        # Reject non-Hyundai cars BEFORE context expansion (prevents "tata" -> Creta bug)
        if mentions_unknown_vehicle(original):
            answer = unknown_vehicle_message(original)
            session_ctx = default_context()
            response = ChatResponse(
                answer=answer,
                found=False,
                response_type="faq",
                suggestions=get_follow_up_suggestions(
                    original, answer, False, used_ids, session_ctx
                ),
                context=session_ctx,
            )
            log_chat_interaction(
                db,
                query=original,
                answer=answer,
                found=False,
                response_type="faq",
                user=current_user,
                session_id=session_id,
            )
            return response

        # Ignore stale context for meaningless input (e.g. "a", "no data found")
        if is_low_signal_query(original):
            answer = clarification_message(original, default_context())
            response = ChatResponse(
                answer=answer,
                found=False,
                response_type="clarification",
                suggestions=get_follow_up_suggestions(
                    original, answer, False, used_ids, {}
                ),
                context=session_ctx,
            )
            log_chat_interaction(
                db,
                query=original,
                answer=answer,
                found=False,
                response_type="clarification",
                user=current_user,
                session_id=session_id,
            )
            return response

        # Step A: Ask user for car model when query is too vague (e.g. 'its price' on fresh login)
        if needs_clarification(original, session_ctx):
            answer = clarification_message(original, session_ctx)
            suggestions = get_follow_up_suggestions(
                original, answer, False, used_ids, session_ctx
            )
            session_ctx = prepare_clarification_context(dict(session_ctx), original)
            if current_user and session_id and session:
                save_session_context(db, session, session_ctx)
            response = ChatResponse(
                answer=answer,
                found=False,
                response_type="clarification",
                suggestions=suggestions,
                context=session_ctx,
            )
            log_chat_interaction(
                db,
                query=original,
                answer=answer,
                found=False,
                response_type="clarification",
                user=current_user,
                session_id=session_id,
            )
            return response

        # Step B: Expand vague follow-ups using session context
        message = resolve_query(original, session_ctx)

        if mentions_unknown_vehicle(original) or mentions_unknown_vehicle(message):
            answer = unknown_vehicle_message(original)
            session_ctx = default_context()
            response = ChatResponse(
                answer=answer,
                found=False,
                response_type="faq",
                suggestions=get_follow_up_suggestions(
                    original, answer, False, used_ids, session_ctx
                ),
                context=session_ctx,
            )
            log_chat_interaction(
                db,
                query=original,
                answer=answer,
                found=False,
                response_type="faq",
                user=current_user,
                session_id=session_id,
            )
            return response

        # Step C: Booking slot queries — check ORIGINAL text only (avoid false positives)
        if is_slot_availability_query(original):
            slots_data = get_next_available_slots(db)
            suggestions = get_follow_up_suggestions(
                original,
                slots_data["message"],
                slots_data["total_found"] > 0,
                used_ids,
                session_ctx,
            )
            answer = slots_data["message"]
            response = ChatResponse(
                answer=answer,
                found=slots_data["total_found"] > 0,
                response_type="slots",
                available_slots=slots_data["slots"],
                suggestions=suggestions,
                resolved_query=message if message != original else None,
            )
            log_chat_interaction(
                db,
                query=original,
                answer=answer,
                found=response.found,
                response_type="slots",
                user=current_user,
                session_id=session_id,
            )
            if current_user and session_id and session:
                session_ctx = apply_exchange_to_session(db, session, original, answer)
            else:
                session_ctx = update_context(session_ctx, original, answer)
            response.context = session_ctx
            return response

        # Step D: Semantic FAQ search in ChromaDB
        result = vector_store.search(message)
        if not result["found"]:
            alt = resolve_query(original, session_ctx)
            if alt != message:
                result = vector_store.search(alt)
                if result["found"]:
                    message = alt

        suggestions = get_follow_up_suggestions(
            original, result["answer"], result["found"], used_ids, session_ctx
        )

        response = ChatResponse(
            answer=result["answer"],
            found=result["found"],
            response_type="faq",
            suggestions=suggestions,
            resolved_query=message if message != original else None,
        )
        log_chat_interaction(
            db,
            query=original,
            answer=result["answer"],
            found=result["found"],
            response_type="faq",
            user=current_user,
            session_id=session_id,
        )
        # Persist updated context (last_vehicle, last_topic) for next message
        if current_user and session_id and session:
            session_ctx = apply_exchange_to_session(
                db, session, original, result["answer"]
            )
        else:
            session_ctx = update_context(session_ctx, original, result["answer"])
        response.context = session_ctx
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat search failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


def _frontend_index() -> Path:
    return FRONTEND_DIST / "index.html"


def _frontend_available() -> bool:
    return _frontend_index().is_file()


if _frontend_available():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")
    logger.info("Serving React frontend from %s", FRONTEND_DIST)


@app.get("/", include_in_schema=False)
async def serve_root():
    """Serve chat UI when built; otherwise return health JSON for API-only deploys."""
    if _frontend_available():
        return FileResponse(_frontend_index())
    return await health_check()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """SPA fallback — static files from Vite build, else index.html."""
    if not _frontend_available():
        raise HTTPException(status_code=404, detail="Not found")

    if full_path:
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)

    return FileResponse(_frontend_index())


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
