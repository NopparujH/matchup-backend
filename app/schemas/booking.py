from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.models.models import BookingStatus

class HoldSlotsRequest(BaseModel):
    slot_ids: List[UUID]

class BookingOut(BaseModel):
    booking_id: UUID
    user_id: UUID
    total_amount: Decimal
    discount_amount: Decimal
    status: BookingStatus
    created_at: datetime
    hold_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True