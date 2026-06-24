"""
SQLAlchemy ORM models — maps Python classes to SQLite tables.

ORM = Object-Relational Mapping: write Python instead of raw SQL.
Each class below becomes one database table when init_db() runs.

Relationships:
  User 1──* Booking
  User 1──* ChatSession
  User 1──* ChatLog
  ChatSession 1──* ChatLog
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _uuid() -> str:
    """Generate a random UUID string for primary keys."""
    return str(uuid.uuid4())


class User(Base):
    """Registered customer or admin account."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # bcrypt hash, never plain password
    full_name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="user")
    chat_logs: Mapped[list["ChatLog"]] = relationship("ChatLog", back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user")


class Booking(Base):
    """Test drive appointment — one slot per date+time (enforced by unique constraint)."""

    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("booking_date", "time_slot", name="uq_date_slot"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    booking_date: Mapped[Date] = mapped_column(Date, nullable=False)
    time_slot: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM" format
    vehicle_model: Mapped[str] = mapped_column(String(80), default="General")
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="bookings")


class OtpRecord(Base):
    """Temporary 6-digit OTP codes for register/login/password-reset."""

    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(6))
    purpose: Mapped[str] = mapped_column(String(30))  # register, login_2fa, password_reset
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
    """
    Per-login chat session. context_json stores conversation state:
    last_vehicle, last_topic, pending_topic, etc. (see context_service.py).
    """

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    chat_logs: Mapped[list["ChatLog"]] = relationship("ChatLog", back_populates="session")


class ChatLog(Base):
    """Every user question and bot answer — used by admin monitor and sidebar history."""

    __tablename__ = "chat_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("chat_sessions.id"), nullable=True, index=True
    )
    user_email: Mapped[str] = mapped_column(String(255), default="guest")
    user_name: Mapped[str] = mapped_column(String(120), default="")
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    found: Mapped[bool] = mapped_column(Boolean, default=False)  # True if FAQ/slot match found
    response_type: Mapped[str] = mapped_column(String(20), default="faq")  # faq|slots|clarification
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User | None"] = relationship("User", back_populates="chat_logs")
    session: Mapped["ChatSession | None"] = relationship("ChatSession", back_populates="chat_logs")
