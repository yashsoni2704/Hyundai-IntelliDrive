"""Admin routes for booking oversight and management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth_utils import get_current_admin, hash_password
from booking_service import (
    create_booking,
    delete_booking,
    get_admin_slots_for_date,
    get_all_bookings,
    get_available_dates,
    update_booking,
)
from chat_log_service import get_chat_logs
from database import get_db
from models import User

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


class BookingUpdateRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    time_slot: str = Field(..., description="HH:MM")
    vehicle_model: str = Field(default="General", max_length=80)
    status: str = Field(default="confirmed", max_length=20)


class AdminBookingCreateRequest(BaseModel):
    customer_email: EmailStr
    customer_name: str = Field(default="", max_length=120)
    date: str = Field(..., description="YYYY-MM-DD")
    time_slot: str = Field(..., description="HH:MM")
    vehicle_model: str = Field(default="General", max_length=80)


@router.get("/bookings")
def list_bookings(db: Session = Depends(get_db)):
    return {"bookings": get_all_bookings(db)}


@router.post("/bookings")
def add_booking(body: AdminBookingCreateRequest, db: Session = Depends(get_db)):
    email = body.customer_email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=body.customer_name.strip(),
            password_hash=hash_password("admin-created-user"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif body.customer_name.strip() and not user.full_name:
        user.full_name = body.customer_name.strip()
        db.commit()
        db.refresh(user)

    return create_booking(db, user.id, body.date, body.time_slot, body.vehicle_model)


@router.get("/dates")
def list_dates():
    return {"dates": get_available_dates()}


@router.get("/slots")
def list_slots(date: str, db: Session = Depends(get_db)):
    return get_admin_slots_for_date(db, date)


@router.put("/bookings/{booking_id}")
def edit_booking(booking_id: str, body: BookingUpdateRequest, db: Session = Depends(get_db)):
    return update_booking(
        db,
        booking_id,
        body.date,
        body.time_slot,
        body.vehicle_model,
        body.status,
    )


@router.delete("/bookings/{booking_id}")
def remove_booking(booking_id: str, db: Session = Depends(get_db)):
    return delete_booking(db, booking_id)


@router.get("/chat-logs")
def list_chat_logs(
    page: int = 1,
    per_page: int = 10,
    email: str | None = None,
    db: Session = Depends(get_db),
):
    """Monitor user queries with pagination and optional email search."""
    return get_chat_logs(db, page=page, per_page=per_page, email=email)
