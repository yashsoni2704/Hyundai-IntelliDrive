"""
Chat session lifecycle and context persistence.

A ChatSession is created on each login (POST /chat/session/start).
It stores conversation context as JSON so follow-up questions work.

Flow:
  login → start_session() → blank context
  each /chat → apply_exchange_to_session() → update last_vehicle, last_topic
  logout → end_session() → mark session inactive
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from context_service import default_context, parse_context, serialize_context, update_context
from models import ChatLog, ChatSession, User


def start_session(db: Session, user: User) -> ChatSession:
    """End any active session and create a fresh one with empty context."""
    db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.is_active.is_(True),
    ).update({"is_active": False, "ended_at": datetime.now(timezone.utc)})

    session = ChatSession(
        user_id=user.id,
        context_json=serialize_context(default_context()),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(db: Session, user: User, session_id: str | None = None) -> None:
    """Mark session(s) inactive on logout — context is no longer used."""
    q = db.query(ChatSession).filter(ChatSession.user_id == user.id, ChatSession.is_active.is_(True))
    if session_id:
        q = q.filter(ChatSession.id == session_id)
    q.update({"is_active": False, "ended_at": datetime.now(timezone.utc)})
    db.commit()


def get_session(db: Session, user: User, session_id: str) -> ChatSession:
    """Fetch session by ID — 404 if not found or belongs to another user."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def get_active_session(db: Session, user: User) -> ChatSession | None:
    """Return the user's current active session, if any."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id, ChatSession.is_active.is_(True))
        .order_by(ChatSession.created_at.desc())
        .first()
    )


def get_session_context(session: ChatSession) -> dict:
    """Parse context_json string into a Python dict."""
    return parse_context(session.context_json)


def save_session_context(db: Session, session: ChatSession, ctx: dict) -> None:
    """Write updated context dict back to SQLite."""
    session.context_json = serialize_context(ctx)
    db.commit()


def apply_exchange_to_session(
    db: Session, session: ChatSession, query: str, answer: str
) -> dict:
    """
    After each chat exchange: update context (last_vehicle, last_topic) and save.
    Called at the end of app.py /chat handler.
    """
    ctx = update_context(get_session_context(session), query, answer)
    save_session_context(db, session, ctx)
    return ctx


def get_session_messages(db: Session, session_id: str) -> list[dict]:
    """
    Rebuild chat UI messages from chat_logs for the current session.
    Used when user refreshes the page while still logged in.
    """
    rows = (
        db.query(ChatLog)
        .filter(ChatLog.session_id == session_id)
        .order_by(ChatLog.created_at.asc())
        .all()
    )
    messages: list[dict] = []
    for row in rows:
        messages.append(
            {
                "id": f"{row.id}-q",
                "role": "user",
                "content": row.query,
                "timestamp": row.created_at.isoformat() if row.created_at else "",
            }
        )
        messages.append(
            {
                "id": row.id,
                "role": "assistant",
                "content": row.answer,
                "found": row.found,
                "response_type": row.response_type,
                "timestamp": row.created_at.isoformat() if row.created_at else "",
            }
        )
    return messages
