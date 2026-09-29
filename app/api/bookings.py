from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from decimal import Decimal

from app.db.session import get_db
from app.models.models import User, Booking, BookingSlot, SlotStatus, BookingStatus, SportsCourt
from app.schemas.booking import HoldSlotsRequest, BookingOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/bookings", tags=["Bookings & Slot Lock"])

async def release_expired_slots(db: AsyncSession):
    """ฟังก์ชันเคลียร์สล็อตที่หมดเวลา 8 นาที คืนกลับเป็น available"""
    now = datetime.utcnow()
    expired_slots_query = select(BookingSlot).where(
        BookingSlot.status == SlotStatus.HELD,
        BookingSlot.hold_expires_at < now
    )
    result = await db.execute(expired_slots_query)
    expired_slots = result.scalars().all()

    for slot in expired_slots:
        slot.status = SlotStatus.AVAILABLE
        slot.hold_expires_at = None
        slot.booking_id = None

    if expired_slots:
        await db.commit()


@router.post("/hold", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def hold_booking_slots(
    payload: HoldSlotsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """กักสล็อตเวลาไว้ 8 นาที (Hold Timer) & ป้องกัน Double-Booking"""
    await release_expired_slots(db)

    if not payload.slot_ids:
        raise HTTPException(status_code=400, detail="No slots provided")

    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=8)

    slots_query = select(BookingSlot).where(BookingSlot.slot_id.in_(payload.slot_ids))
    result = await db.execute(slots_query)
    slots = result.scalars().all()

    if len(slots) != len(payload.slot_ids):
        raise HTTPException(status_code=404, detail="One or more slots not found")

    for slot in slots:
        if slot.status != SlotStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot at {slot.start_time} is already held or booked."
            )

    total_amount = Decimal("0.00")
    for slot in slots:
        court_res = await db.execute(select(SportsCourt).where(SportsCourt.court_id == slot.court_id))
        court = court_res.scalars().first()
        if court:
            total_amount += court.hourly_rate

    new_booking = Booking(
        user_id=current_user.user_id,
        total_amount=total_amount,
        discount_amount=Decimal("0.00"),
        status=BookingStatus.HOLDING
    )
    db.add(new_booking)
    await db.flush()

    for slot in slots:
        slot.status = SlotStatus.HELD
        slot.hold_expires_at = expires_at
        slot.booking_id = new_booking.booking_id

    await db.commit()
    await db.refresh(new_booking)

    response_data = BookingOut.model_validate(new_booking)
    response_data.hold_expires_at = expires_at
    return response_data


@router.post("/{booking_id}/redeem-credit", response_model=BookingOut)
async def redeem_free_slot_credit(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ใช้ Free Slot Credit สะสมมาหักเป็นส่วนลดการจองฟรี 1 สล็อต"""
    if current_user.free_slot_credits < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="คุณไม่มี Free Slot Credit เหลือสำหรับการใช้งาน"
        )

    result = await db.execute(
        select(Booking).where(
            Booking.booking_id == booking_id,
            Booking.user_id == current_user.user_id
        )
    )
    booking = result.scalars().first()

    if not booking or booking.status != BookingStatus.HOLDING:
        raise HTTPException(status_code=400, detail="ไม่พบรายการจอง หรือรายการไม่อยู่ในสถานะ HOLDING")

    slots_res = await db.execute(select(BookingSlot).where(BookingSlot.booking_id == booking.booking_id))
    slots = slots_res.scalars().all()
    if not slots:
        raise HTTPException(status_code=400, detail="ไม่พบสล็อตเวลานี้ในระบบ")

    court_res = await db.execute(select(SportsCourt).where(SportsCourt.court_id == slots[0].court_id))
    court = court_res.scalars().first()
    
    discount = court.hourly_rate if court else Decimal("0.00")
    if discount > booking.total_amount:
        discount = booking.total_amount

    booking.discount_amount = discount
    booking.total_amount -= discount
    current_user.free_slot_credits -= 1

    await db.commit()
    await db.refresh(booking)
    return booking


@router.post("/{booking_id}/confirm", response_model=BookingOut)
async def confirm_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """ยืนยันการชำระเงิน + สะสมสล็อต + คำนวณแจก Free Slot Credit อัตโนมัติทุกๆ 10 สล็อต"""
    await release_expired_slots(db)

    result = await db.execute(
        select(Booking).where(
            Booking.booking_id == booking_id,
            Booking.user_id == current_user.user_id
        )
    )
    booking = result.scalars().first()

    if not booking or booking.status != BookingStatus.HOLDING:
        raise HTTPException(status_code=400, detail="Booking is not in holding state or already processed")

    slots_res = await db.execute(select(BookingSlot).where(BookingSlot.booking_id == booking.booking_id))
    slots = slots_res.scalars().all()

    booking.status = BookingStatus.CONFIRMED
    for slot in slots:
        slot.status = SlotStatus.BOOKED
        slot.hold_expires_at = None

    # สะสมจำนวนสล็อตของผู้ใช้งาน
    current_user.accumulated_slots_count += len(slots)

    # คำนวณแจก Free Slot Credit อัตโนมัติเมื่อสะสมครบทุกๆ 10 สล็อต
    if current_user.accumulated_slots_count >= 10:
        earned_credits = current_user.accumulated_slots_count // 10
        current_user.free_slot_credits += earned_credits
        current_user.accumulated_slots_count %= 10

    await db.commit()
    await db.refresh(booking)
    return booking