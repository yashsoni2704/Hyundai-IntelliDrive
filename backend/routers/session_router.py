"""Chat session routes for logged-in users."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from chat_log_service import get_user_recent_exchanges
from database import get_db
from models import User
from session_service import (
    end_session,
    get_session,
    get_session_context,
    get_session_messages,
    start_session,
)

router = APIRouter(prefix="/chat", tags=["chat-session"])


class SessionStartResponse(BaseModel):
    session_id: str
    context: dict


class SessionEndRequest(BaseModel):
    session_id: str | None = None


@router.post("/session/start", response_model=SessionStartResponse)
def session_start(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start a fresh chat session (new context). Called on login."""
    session = start_session(db, user)
    return SessionStartResponse(
        session_id=session.id,
        context=get_session_context(session),
    )


@router.post("/session/end")
def session_end(
    body: SessionEndRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """End session on logout — context is discarded."""
    end_session(db, user, body.session_id)
    return {"message": "Session ended"}


@router.get("/session/{session_id}/messages")
def session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restore current session messages (e.g. page refresh while logged in)."""
    get_session(db, user, session_id)
    return {"messages": get_session_messages(db, session_id)}


@router.get("/recent")
def recent_exchanges(
    session_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Last 5 Q&A pairs for sidebar (latest first). User-wide history by default."""
    if session_id:
        get_session(db, user, session_id)
    return {
        "exchanges": get_user_recent_exchanges(
            db, user.id, limit=5, session_id=session_id
        )
    }
