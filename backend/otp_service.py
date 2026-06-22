"""OTP generation, storage, and verification."""

import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from email_service import EmailDeliveryError, send_otp_email
from models import OtpRecord


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def create_and_send_otp(db: Session, email: str, purpose: str) -> dict:
    """Invalidate old OTPs, create a new one, and send via email."""
    db.query(OtpRecord).filter(
        OtpRecord.email == email,
        OtpRecord.purpose == purpose,
        OtpRecord.used.is_(False),
    ).update({"used": True})

    code = generate_otp()
    record = OtpRecord(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(record)
    db.commit()

    try:
        send_otp_email(email, code, purpose)
    except EmailDeliveryError as exc:
        record.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return {"message": "OTP sent to your email.", "email": email}


def verify_otp(db: Session, email: str, otp: str, purpose: str) -> bool:
    """Verify OTP matches a valid, unused, non-expired record."""
    record = (
        db.query(OtpRecord)
        .filter(
            OtpRecord.email == email,
            OtpRecord.purpose == purpose,
            OtpRecord.used.is_(False),
        )
        .order_by(OtpRecord.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not found")
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
    if record.code != otp.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    record.used = True
    db.commit()
    return True
