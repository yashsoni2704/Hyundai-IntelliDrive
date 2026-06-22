"""Test drive booking routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth_utils import get_current_user
from booking_service import (
    create_booking,
    get_available_dates,
    get_next_available_slots,
    get_slots_for_date,
    get_user_bookings,
)
from database import get_db
from models import User

router = APIRouter(prefix="/bookings", tags=["bookings"])


class BookSlotRequest(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    time_slot: str = Field(..., description="HH:MM e.g. 10:00")
    vehicle_model: str = Field(default="General", max_length=80)


@router.get("/dates")
def list_dates():
    return {"dates": get_available_dates()}


@router.get("/slots")
def list_slots(date: str, db: Session = Depends(get_db)):
    return get_slots_for_date(db, date)


@router.get("/next-available")
def next_available_slots(count: int = 5, db: Session = Depends(get_db)):
    """Return the next N available 1-hour booking slots from the database."""
    return get_next_available_slots(db, min(count, 10))


@router.get("/my")
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"bookings": get_user_bookings(db, user.id)}


@router.post("")
def book_slot(
    body: BookSlotRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return create_booking(db, user.id, body.date, body.time_slot, body.vehicle_model)
    except HTTPException:
        raise
