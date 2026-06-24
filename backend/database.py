"""
SQLite database setup and session management.

SQLite stores all relational data in backend/app.db (single file, no separate server).
SQLAlchemy engine + SessionLocal provide database connections.
get_db() is a FastAPI dependency — yields a session per request, auto-closes after.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATABASE_URL

# check_same_thread=False required for SQLite with FastAPI multi-threaded requests
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models in models.py."""
    pass


def get_db():
    """
    FastAPI dependency: yields a DB session for one request.
    Usage in routes: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_schema() -> None:
    """Lightweight migrations for existing databases (add columns if missing)."""
    insp = inspect(engine)
    if insp.has_table("chat_logs"):
        cols = {c["name"] for c in insp.get_columns("chat_logs")}
        if "session_id" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE chat_logs ADD COLUMN session_id VARCHAR(36)")
                )


def init_db() -> None:
    """Create all tables from models.py if they do not exist. Called on server startup."""
    from models import Booking, ChatLog, ChatSession, OtpRecord, User  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_schema()
