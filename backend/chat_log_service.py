"""Persist and query chat interaction logs for admin monitoring."""

from sqlalchemy.orm import Session

from models import ChatLog, User


def log_chat_interaction(
    db: Session,
    *,
    query: str,
    answer: str,
    found: bool,
    response_type: str,
    user: User | None = None,
) -> None:
    record = ChatLog(
        user_id=user.id if user else None,
        user_email=user.email if user else "guest",
        user_name=user.full_name if user else "",
        query=query,
        answer=answer,
        found=found,
        response_type=response_type,
    )
    db.add(record)
    db.commit()


def get_chat_logs(db: Session, limit: int = 200) -> list[dict]:
    rows = (
        db.query(ChatLog)
        .order_by(ChatLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "user_email": row.user_email,
            "user_name": row.user_name,
            "query": row.query,
            "answer": row.answer,
            "found": row.found,
            "response_type": row.response_type,
            "created_at": row.created_at.isoformat() if row.created_at else "",
        }
        for row in rows
    ]
