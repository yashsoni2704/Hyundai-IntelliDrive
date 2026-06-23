"""SQLAlchemy models for users, bookings, OTP codes, and chat logs."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="user")
    chat_logs: Mapped[list["ChatLog"]] = relationship("ChatLog", back_populates="user")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("booking_date", "time_slot", name="uq_date_slot"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    booking_date: Mapped[Date] = mapped_column(Date, nullable=False)
    time_slot: Mapped[str] = mapped_column(String(5), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(80), default="General")
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="bookings")


class OtpRecord(Base):
    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code: Mapped[str] = mapped_column(String(6))
    purpose: Mapped[str] = mapped_column(String(30))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
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
    found: Mapped[bool] = mapped_column(Boolean, default=False)
    response_type: Mapped[str] = mapped_column(String(20), default="faq")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User | None"] = relationship("User", back_populates="chat_logs")
    session: Mapped["ChatSession | None"] = relationship("ChatSession", back_populates="chat_logs")
