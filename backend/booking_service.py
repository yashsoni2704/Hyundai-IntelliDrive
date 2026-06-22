"""Test drive slot management - 1-hour slots, conflict detection."""

from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import Booking, User

OPEN_HOUR = 10
CLOSE_HOUR = 20
TIME_SLOTS = [f"{h:02d}:00" for h in range(OPEN_HOUR, CLOSE_HOUR)]
MAX_BOOKING_DAYS = 14
NEXT_SLOTS_COUNT = 5


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD.",
        ) from exc


def _format_hour(hour: int) -> str:
    suffix = "am" if hour < 12 else "pm"
    display_hour = hour % 12 or 12
    return f"{display_hour}:00 {suffix}"


def _slot_label(slot: str) -> str:
    hour = int(slot.split(":")[0])
    return f"{_format_hour(hour)} - {_format_hour(hour + 1)}"


def _booked_slots(db: Session, booking_date: date) -> set[str]:
    rows = (
        db.query(Booking.time_slot)
        .filter(Booking.booking_date == booking_date, Booking.status == "confirmed")
        .all()
    )
    return {row[0] for row in rows}


def _slots_from_now(booking_date: date) -> list[str]:
    """Return time slots that have not yet started on the given date."""
    today = date.today()
    if booking_date < today:
        return []
    if booking_date > today:
        return TIME_SLOTS

    now = datetime.now()
    start_hour = now.hour if now.minute == 0 else now.hour + 1
    start_hour = max(start_hour, OPEN_HOUR)
    if start_hour >= CLOSE_HOUR:
        return []
    return [slot for slot in TIME_SLOTS if int(slot.split(":")[0]) >= start_hour]


def _day_label(booking_date: date) -> str:
    today = date.today()
    if booking_date == today:
        return "Today"
    if booking_date == today + timedelta(days=1):
        return "Tomorrow"
    return booking_date.strftime("%a, %d %b %Y")


def get_available_dates() -> list[str]:
    """Return today and upcoming days available for booking."""
    today = date.today()
    return [(today + timedelta(days=i)).isoformat() for i in range(MAX_BOOKING_DAYS)]


def get_next_available_slots(db: Session, count: int = NEXT_SLOTS_COUNT) -> dict:
    """
    Find the next N available 1-hour slots across today and future days.

    Today's slots start from the current hour when exactly on the hour, otherwise
    from the next hour, and never before showroom opening.
    """
    today = date.today()
    results: list[dict] = []

    for day_offset in range(MAX_BOOKING_DAYS):
        current_date = today + timedelta(days=day_offset)
        booked = _booked_slots(db, current_date)
        candidates = _slots_from_now(current_date)

        for slot in candidates:
            if slot in booked:
                continue
            results.append(
                {
                    "slot_number": len(results) + 1,
                    "date": current_date.isoformat(),
                    "time": slot,
                    "time_label": _slot_label(slot),
                    "day_label": _day_label(current_date),
                }
            )
            if len(results) >= count:
                break
        if len(results) >= count:
            break

    today_available = sum(
        1
        for slot in _slots_from_now(today)
        if slot not in _booked_slots(db, today)
    )

    if not results:
        message = "No test drive slots are available in the next 14 days. Please contact the showroom."
    elif today_available == 0 and results:
        message = (
            "All slots for today are fully booked. "
            f"Here are the next {len(results)} available slot(s) for booking:"
        )
    else:
        message = f"Here are the next {len(results)} available test drive slot(s):"

    return {
        "slots": results,
        "total_found": len(results),
        "today_available_count": today_available,
        "message": message,
    }


def get_slots_for_date(db: Session, date_str: str) -> dict:
    booking_date = _parse_date(date_str)
    booked = _booked_slots(db, booking_date)
    visible_slots = _slots_from_now(booking_date) if booking_date == date.today() else TIME_SLOTS
    slots = [
        {"time": slot, "available": slot not in booked, "label": _slot_label(slot)}
        for slot in visible_slots
    ]
    return {
        "date": date_str,
        "showroom_hours": f"{_format_hour(OPEN_HOUR)} - {_format_hour(CLOSE_HOUR)}",
        "current_time": datetime.now().strftime("%I:%M %p").lstrip("0").lower(),
        "slots": slots,
        "available_count": sum(1 for s in slots if s["available"]),
    }


def find_next_free_slot(
    db: Session,
    start_date: date,
    preferred_slot: str | None = None,
) -> tuple[str, str] | None:
    """Find the next available date and time slot."""
    for day_offset in range(MAX_BOOKING_DAYS):
        current_date = start_date + timedelta(days=day_offset)
        booked = _booked_slots(db, current_date)
        candidates = _slots_from_now(current_date)
        if day_offset == 0 and preferred_slot and preferred_slot in candidates:
            idx = candidates.index(preferred_slot)
            candidates = candidates[idx:] + candidates[:idx]
        for slot in candidates:
            if slot not in booked:
                return current_date.isoformat(), slot
    return None


def create_booking(
    db: Session,
    user_id: str,
    date_str: str,
    time_slot: str,
    vehicle_model: str,
) -> dict:
    booking_date = _parse_date(date_str)
    if time_slot not in TIME_SLOTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time slot")
    if time_slot not in _slots_from_now(booking_date):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This slot is no longer available")

    existing = (
        db.query(Booking)
        .filter(
            Booking.booking_date == booking_date,
            Booking.time_slot == time_slot,
            Booking.status == "confirmed",
        )
        .first()
    )
    if existing:
        next_free = find_next_free_slot(db, booking_date, time_slot)
        detail = {
            "message": "This slot has been taken.",
            "requested_date": date_str,
            "requested_slot": time_slot,
            "requested_label": _slot_label(time_slot),
        }
        if next_free:
            detail["next_available_date"] = next_free[0]
            detail["next_available_slot"] = next_free[1]
            detail["next_available_label"] = _slot_label(next_free[1])
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    booking = Booking(
        user_id=user_id,
        booking_date=booking_date,
        time_slot=time_slot,
        vehicle_model=vehicle_model or "General",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "id": booking.id,
        "date": date_str,
        "time_slot": time_slot,
        "slot_label": _slot_label(time_slot),
        "vehicle_model": booking.vehicle_model,
        "status": booking.status,
        "message": f"Test drive booked for {date_str} at {_slot_label(time_slot)}.",
    }


def get_user_bookings(db: Session, user_id: str) -> list[dict]:
    rows = (
        db.query(Booking)
        .filter(Booking.user_id == user_id, Booking.status == "confirmed")
        .order_by(Booking.booking_date, Booking.time_slot)
        .all()
    )
    return [
        {
            "id": b.id,
            "date": b.booking_date.isoformat(),
            "time_slot": b.time_slot,
            "slot_label": _slot_label(b.time_slot),
            "vehicle_model": b.vehicle_model,
            "status": b.status,
        }
        for b in rows
    ]


def get_all_bookings(db: Session) -> list[dict]:
    rows = (
        db.query(Booking, User)
        .join(User, Booking.user_id == User.id)
        .order_by(Booking.booking_date, Booking.time_slot)
        .all()
    )
    return [
        {
            "id": booking.id,
            "user_id": user.id,
            "customer_name": user.full_name,
            "customer_email": user.email,
            "date": booking.booking_date.isoformat(),
            "time_slot": booking.time_slot,
            "slot_label": _slot_label(booking.time_slot),
            "vehicle_model": booking.vehicle_model,
            "status": booking.status,
            "created_at": booking.created_at.isoformat() if booking.created_at else None,
        }
        for booking, user in rows
    ]


def get_admin_slots_for_date(db: Session, date_str: str) -> dict:
    booking_date = _parse_date(date_str)
    rows = (
        db.query(Booking, User)
        .join(User, Booking.user_id == User.id)
        .filter(Booking.booking_date == booking_date, Booking.status == "confirmed")
        .all()
    )
    booking_by_slot = {booking.time_slot: (booking, user) for booking, user in rows}
    visible_slots = _slots_from_now(booking_date) if booking_date == date.today() else TIME_SLOTS
    slots = []
    for slot in visible_slots:
        booking_pair = booking_by_slot.get(slot)
        slot_data = {
            "time": slot,
            "label": _slot_label(slot),
            "available": booking_pair is None,
            "booking": None,
        }
        if booking_pair:
            booking, user = booking_pair
            slot_data["booking"] = {
                "id": booking.id,
                "customer_name": user.full_name,
                "customer_email": user.email,
                "vehicle_model": booking.vehicle_model,
                "status": booking.status,
            }
        slots.append(slot_data)
    return {
        "date": date_str,
        "showroom_hours": f"{_format_hour(OPEN_HOUR)} - {_format_hour(CLOSE_HOUR)}",
        "current_time": datetime.now().strftime("%I:%M %p").lstrip("0").lower(),
        "slots": slots,
        "available_count": sum(1 for s in slots if s["available"]),
        "taken_count": sum(1 for s in slots if not s["available"]),
    }


def update_booking(
    db: Session,
    booking_id: str,
    date_str: str,
    time_slot: str,
    vehicle_model: str,
    status_value: str,
) -> dict:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    booking_date = _parse_date(date_str)
    if time_slot not in TIME_SLOTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time slot")

    conflict = (
        db.query(Booking)
        .filter(
            Booking.id != booking_id,
            Booking.booking_date == booking_date,
            Booking.time_slot == time_slot,
            Booking.status == "confirmed",
        )
        .first()
    )
    if status_value == "confirmed" and conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This slot is already taken")

    booking.booking_date = booking_date
    booking.time_slot = time_slot
    booking.vehicle_model = vehicle_model or "General"
    booking.status = status_value or "confirmed"
    db.commit()
    db.refresh(booking)
    return {
        "id": booking.id,
        "date": booking.booking_date.isoformat(),
        "time_slot": booking.time_slot,
        "slot_label": _slot_label(booking.time_slot),
        "vehicle_model": booking.vehicle_model,
        "status": booking.status,
        "message": "Booking updated.",
    }


def delete_booking(db: Session, booking_id: str) -> dict:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted."}
