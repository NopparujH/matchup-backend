from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time, datetime
from decimal import Decimal
from uuid import UUID
from app.models.models import SportType, SlotStatus

class SportsCourtCreate(BaseModel):
    sport_type: SportType
    court_name: str
    hourly_rate: Decimal

class SportsCourtOut(BaseModel):
    court_id: int
    sport_type: SportType
    court_name: str
    hourly_rate: Decimal

    class Config:
        from_attributes = True

class BookingSlotOut(BaseModel):
    slot_id: UUID
    court_id: int
    booking_date: date
    start_time: time
    end_time: time
    status: SlotStatus
    hold_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class GenerateSlotsRequest(BaseModel):
    court_id: int
    target_date: date
    start_hour: int = 9   # เริ่ม 09:00
    end_hour: int = 22    # สิ้นสุด 22:00