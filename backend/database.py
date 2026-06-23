"""SQLite database setup and session management."""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Yield a database session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_schema() -> None:
    """Add new columns/tables on existing SQLite databases."""
    insp = inspect(engine)
    if insp.has_table("chat_logs"):
        cols = {c["name"] for c in insp.get_columns("chat_logs")}
        if "session_id" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE chat_logs ADD COLUMN session_id VARCHAR(36)")
                )


def init_db() -> None:
    """Create all tables if they do not exist."""
    from models import Booking, ChatLog, ChatSession, OtpRecord, User  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_schema()
