"""
FastAPI application entry point for Hyundai Knowledge Assistant.

This file wires together:
  - Startup: SQLite init + ChromaDB FAQ ingestion (lifespan)
  - POST /chat: main chatbot pipeline (clarification → context → search → log)
  - GET /health, GET /stats: monitoring endpoints
  - Routers: auth, bookings, admin, session

Read this file after context_service.py and chroma_db.py to see the full request flow.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth_utils import get_optional_user
from booking_service import get_next_available_slots
from chat_log_service import log_chat_interaction
from chroma_db import vector_store
from config import CORS_ORIGINS
from database import get_db, init_db
from models import User
from routers.auth_router import router as auth_router
from routers.bookings_router import router as bookings_router
from routers.admin_router import router as admin_router
from context_service import (
    clarification_message,
    enrich_search_query,
    needs_clarification,
    normalize_message,
    prepare_clarification_context,
    resolve_query,
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
    Runs once when the server starts (before accepting requests).
    init_db() creates SQLite tables; vector_store.initialize() ingests FAQs into ChromaDB.
    """
    logger.info("Starting Hyundai Knowledge Assistant backend...")
    init_db()
    try:
        vector_store.initialize()
        logger.info("Knowledge base ready.")
    except Exception as exc:
        logger.error("Failed to initialize knowledge base: %s", exc)
        raise
    yield  # Server runs here until shutdown
    logger.info("Shutting down backend.")


# FastAPI app instance — title/description appear in auto-generated docs at /docs
app = FastAPI(
    title="Hyundai Knowledge Assistant",
    description="Semantic FAQ retrieval, auth, and test drive bookings.",
    version="2.2.0",
    lifespan=lifespan,
)

# CORS: allow browser frontend (port 5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS],
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
    """Lightweight health check for monitoring."""
    return {
        "status": "ok",
        "version": "2.2.0",
        "knowledge_base": "ready" if vector_store.is_initialized else "initializing",
        "auth": True,
        "bookings": True,
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
        session_ctx: dict = {}
        session_id = request.session_id
        message = original

        # Load persisted context (last_vehicle, pending_topic, etc.) from SQLite
        if current_user and session_id:
            session = get_session(db, current_user, session_id)
            session_ctx = get_session_context(session)

        # Step A: Ask user for car model when query is too vague (e.g. 'its price' on fresh login)
        if needs_clarification(original, session_ctx):
            answer = clarification_message(original, session_ctx)
            suggestions = get_follow_up_suggestions(
                original, answer, False, used_ids, session_ctx
            )
            if current_user and session_id:
                session_ctx = prepare_clarification_context(dict(session_ctx), original)
                save_session_context(db, session, session_ctx)
            response = ChatResponse(
                answer=answer,
                found=False,
                response_type="clarification",
                suggestions=suggestions,
                context=session_ctx if current_user and session_id else None,
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
        if current_user and session_id:
            message = resolve_query(original, session_ctx)
        else:
            message = enrich_search_query(original, session_ctx)

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
            if current_user and session_id:
                session = get_session(db, current_user, session_id)
                session_ctx = apply_exchange_to_session(db, session, original, answer)
                response.context = session_ctx
            return response

        # Step D: Semantic FAQ search in ChromaDB
        result = vector_store.search(message)
        if not result["found"]:
            # Retry with alternate enriched query if first search missed
            alt = enrich_search_query(original, session_ctx)
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
        if current_user and session_id:
            session = get_session(db, current_user, session_id)
            session_ctx = apply_exchange_to_session(
                db, session, original, result["answer"]
            )
            response.context = session_ctx
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chat search failed")
        raise HTTPException(status_code=500, detail="Internal server error") from exc
