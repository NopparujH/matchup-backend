from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import date, time, timedelta, datetime
from app.db.session import get_db
from app.models.models import SportsCourt, BookingSlot, SlotStatus
from app.schemas.court import (
    SportsCourtCreate, SportsCourtOut, 
    BookingSlotOut, GenerateSlotsRequest
)

router = APIRouter(prefix="/courts", tags=["Sports Courts & Slots"])

@router.post("/", response_model=SportsCourtOut, status_code=status.HTTP_201_CREATED)
async def create_court(court_in: SportsCourtCreate, db: AsyncSession = Depends(get_db)):
    """สร้างสนามใหม่ (เช่น สนามแบดมินตัน Court 1)"""
    court = SportsCourt(**court_in.model_dump())
    db.add(court)
    await db.commit()
    await db.refresh(court)
    return court

@router.get("/", response_model=List[SportsCourtOut])
async def list_courts(db: AsyncSession = Depends(get_db)):
    """ดึงรายชื่อสนามทั้งหมด"""
    result = await db.execute(select(SportsCourt))
    return result.scalars().all()

@router.post("/generate-slots", status_code=status.HTTP_201_CREATED)
async def generate_daily_slots(payload: GenerateSlotsRequest, db: AsyncSession = Depends(get_db)):
    """สร้างสล็อตเวลาประจำวันสำหรับสนามที่ระบุ (เช่น 09:00-10:00, 10:00-11:00)"""
    court_result = await db.execute(select(SportsCourt).where(SportsCourt.court_id == payload.court_id))
    court = court_result.scalars().first()
    if not court:
        raise HTTPException(status_code=404, detail="Court not found")

    created_slots = []
    for hour in range(payload.start_hour, payload.end_hour):
        start_t = time(hour, 0)
        end_t = time(hour + 1, 0)

        # เช็กว่าสล็อตช่วงเวลานี้มีอยู่แล้วหรือยัง
        existing = await db.execute(
            select(BookingSlot).where(
                BookingSlot.court_id == payload.court_id,
                BookingSlot.booking_date == payload.target_date,
                BookingSlot.start_time == start_t
            )
        )
        if existing.scalars().first():
            continue

        slot = BookingSlot(
            court_id=payload.court_id,
            booking_date=payload.target_date,
            start_time=start_t,
            end_time=end_t,
            status=SlotStatus.AVAILABLE
        )
        db.add(slot)
        created_slots.append(slot)

    await db.commit()
    return {"message": f"Successfully created {len(created_slots)} slots for {payload.target_date}"}

@router.get("/{court_id}/slots", response_model=List[BookingSlotOut])
async def get_court_slots(court_id: int, target_date: date, db: AsyncSession = Depends(get_db)):
    """ดึงตารางสล็อตเวลาของสนามตามวันที่กำหนด"""
    result = await db.execute(
        select(BookingSlot)
        .where(
            BookingSlot.court_id == court_id,
            BookingSlot.booking_date == target_date
        )
        .order_by(BookingSlot.start_time)
    )
    return result.scalars().all()