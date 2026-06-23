"""Chat session lifecycle and context persistence."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from context_service import default_context, parse_context, serialize_context, update_context
from models import ChatLog, ChatSession, User


def start_session(db: Session, user: User) -> ChatSession:
    """End any active session and create a fresh one."""
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
    q = db.query(ChatSession).filter(ChatSession.user_id == user.id, ChatSession.is_active.is_(True))
    if session_id:
        q = q.filter(ChatSession.id == session_id)
    q.update({"is_active": False, "ended_at": datetime.now(timezone.utc)})
    db.commit()


def get_session(db: Session, user: User, session_id: str) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def get_active_session(db: Session, user: User) -> ChatSession | None:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id, ChatSession.is_active.is_(True))
        .order_by(ChatSession.created_at.desc())
        .first()
    )


def get_session_context(session: ChatSession) -> dict:
    return parse_context(session.context_json)


def save_session_context(db: Session, session: ChatSession, ctx: dict) -> None:
    session.context_json = serialize_context(ctx)
    db.commit()


def apply_exchange_to_session(
    db: Session, session: ChatSession, query: str, answer: str
) -> dict:
    ctx = update_context(get_session_context(session), query, answer)
    save_session_context(db, session, ctx)
    return ctx


def get_session_messages(db: Session, session_id: str) -> list[dict]:
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
