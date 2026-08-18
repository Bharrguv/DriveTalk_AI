"""
Mock appointment / service scheduler API for DriveTalk AI.

In production this would talk to a real DMS (CDK, Xtime, Dealertrack, etc.).
Here we keep everything in memory so the project runs 100% locally.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field


class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: f"APT-{uuid.uuid4().hex[:5].upper()}")
    customer_name: str
    phone: str
    vehicle: str
    service: str
    datetime: str  
    status: str = "confirmed"  
    notes: str = ""


class Slot(BaseModel):
    datetime: str
    bay: str
    available: bool = True



_APPOINTMENTS: dict[str, Appointment] = {}
_SLOTS: list[Slot] = []


def _seed_slots() -> None:
    """Generate realistic open slots for the next 7 days (service hours 8–17)."""
    global _SLOTS
    if _SLOTS:
        return

    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    services_hours = list(range(8, 17)) 

    for day_offset in range(1, 8):  
        day = base + timedelta(days=day_offset)
        if day.weekday() >= 5:  
            continue
        for hour in services_hours:
            for bay in ("Bay 1", "Bay 2", "Bay 3"):
                
                taken = (hour + day_offset) % 4 == 0
                _SLOTS.append(
                    Slot(
                        datetime=day.replace(hour=hour, minute=0).strftime("%Y-%m-%d %H:%M"),
                        bay=bay,
                        available=not taken,
                    )
                )


def reset_store() -> None:
    """Clear everything (useful for tests / demos)."""
    global _APPOINTMENTS, _SLOTS
    _APPOINTMENTS = {}
    _SLOTS = []
    _seed_slots()


_seed_slots()



def get_available_slots(
    service: str | None = None,
    preferred_date: str | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """
    Return open slots. Optional filters:
    - preferred_date: "YYYY-MM-DD" or "tomorrow" / "next monday" style (agent handles parsing)
    """
    _seed_slots()
    open_slots = [s for s in _SLOTS if s.available]

    if preferred_date:
        open_slots = [s for s in open_slots if s.datetime.startswith(preferred_date[:10])]

    result = []
    for s in open_slots[:limit]:
        result.append(
            {
                "datetime": s.datetime,
                "bay": s.bay,
                "service_hint": service or "general service",
            }
        )
    return result


def book_appointment(
    customer_name: str,
    phone: str,
    vehicle: str,
    service: str,
    datetime_str: str,
    notes: str = "",
) -> dict[str, Any]:
    """Book a slot. Returns confirmation or error."""
    target = None
    for s in _SLOTS:
        if s.datetime == datetime_str and s.available:
            target = s
            break

    if not target:
        return {
            "success": False,
            "error": f"No available slot at {datetime_str}. Please check available slots again.",
        }

    target.available = False
    appt = Appointment(
        customer_name=customer_name,
        phone=phone,
        vehicle=vehicle,
        service=service,
        datetime=datetime_str,
        notes=notes,
    )
    _APPOINTMENTS[appt.id] = appt

    return {
        "success": True,
        "confirmation_code": appt.id,
        "customer_name": appt.customer_name,
        "datetime": appt.datetime,
        "bay": target.bay,
        "service": appt.service,
        "vehicle": appt.vehicle,
        "message": f"Booked {service} for {customer_name} on {datetime_str} ({target.bay}).",
    }


def reschedule_appointment(
    confirmation_code: str,
    new_datetime: str,
) -> dict[str, Any]:
    """Move an existing appointment to a new open slot."""
    appt = _APPOINTMENTS.get(confirmation_code)
    if not appt:
        return {"success": False, "error": f"Appointment {confirmation_code} not found."}

    for s in _SLOTS:
        if s.datetime == appt.datetime:
            s.available = True
            break

    new_slot = None
    for s in _SLOTS:
        if s.datetime == new_datetime and s.available:
            new_slot = s
            break

    if not new_slot:
        return {
            "success": False,
            "error": f"No available slot at {new_datetime}.",
        }

    new_slot.available = False
    old_dt = appt.datetime
    appt.datetime = new_datetime

    return {
        "success": True,
        "confirmation_code": appt.id,
        "old_datetime": old_dt,
        "new_datetime": new_datetime,
        "bay": new_slot.bay,
        "message": f"Rescheduled {appt.service} from {old_dt} to {new_datetime}.",
    }


def get_appointment(confirmation_code: str) -> dict[str, Any] | None:
    appt = _APPOINTMENTS.get(confirmation_code)
    if not appt:
        return None
    return appt.model_dump()


def list_appointments() -> list[dict[str, Any]]:
    return [a.model_dump() for a in _APPOINTMENTS.values()]
