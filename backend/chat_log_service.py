"""Persist and query chat interaction logs for admin monitoring."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import ChatLog, User

IST = ZoneInfo("Asia/Kolkata")


def _to_ist_iso(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d/%m/%Y, %I:%M:%S %p")


def log_chat_interaction(
    db: Session,
    *,
    query: str,
    answer: str,
    found: bool,
    response_type: str,
    user: User | None = None,
    session_id: str | None = None,
) -> ChatLog:
    record = ChatLog(
        user_id=user.id if user else None,
        session_id=session_id,
        user_email=user.email if user else "guest",
        user_name=user.full_name if user else "",
        query=query,
        answer=answer,
        found=found,
        response_type=response_type,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_user_recent_exchanges(
    db: Session,
    user_id: str,
    limit: int = 5,
    session_id: str | None = None,
) -> list[dict]:
    """Last N Q&A pairs for sidebar (latest first). Optionally scoped to one session."""
    q = db.query(ChatLog).filter(ChatLog.user_id == user_id)
    if session_id:
        q = q.filter(ChatLog.session_id == session_id)
    rows = q.order_by(ChatLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "query": row.query,
            "answer": row.answer,
            "found": row.found,
            "response_type": row.response_type,
            "created_at": _to_ist_iso(row.created_at),
        }
        for row in rows
    ]


def get_chat_logs(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 10,
    email: str | None = None,
) -> dict:
    q = db.query(ChatLog)
    if email:
        q = q.filter(ChatLog.user_email.ilike(f"%{email.strip().lower()}%"))

    total = q.with_entities(func.count(ChatLog.id)).scalar() or 0
    page = max(1, page)
    per_page = min(max(1, per_page), 50)
    offset = (page - 1) * per_page

    rows = (
        q.order_by(ChatLog.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    logs = [
        {
            "id": row.id,
            "user_id": row.user_id,
            "user_email": row.user_email,
            "user_name": row.user_name,
            "query": row.query,
            "answer": row.answer,
            "found": row.found,
            "response_type": row.response_type,
            "created_at": _to_ist_iso(row.created_at),
        }
        for row in rows
    ]

    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }
