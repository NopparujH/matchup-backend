from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.models import User, Booking, BookingStatus, Equipment
from app.schemas.equipment import EquipmentOut, AddEquipmentRequest
from app.api.deps import get_current_user

router = APIRouter(prefix="/equipments", tags=["Equipment Rental"])

@router.get("", response_model=list[EquipmentOut])
async def list_equipments(db: AsyncSession = Depends(get_db)):
    """ดึงรายการอุปกรณ์เสริมทั้งหมดที่เปิดให้เช่า"""
    result = await db.execute(select(Equipment))
    return result.scalars().all()

@router.post("/bookings/{booking_id}/add-equipment")
async def add_equipment_to_booking(
    booking_id: str,
    payload: AddEquipmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """เพิ่มรายการเช่าอุปกรณ์เข้ากับใบจอง (ขณะอยู่ในสถานะ HOLDING)"""
    result = await db.execute(
        select(Booking).where(
            Booking.booking_id == booking_id,
            Booking.user_id == current_user.user_id
        )
    )
    booking = result.scalars().first()

    if not booking or booking.status != BookingStatus.HOLDING:
        raise HTTPException(status_code=400, detail="ไม่พบรายการจอง หรือรายการไม่อยู่ในสถานะ HOLDING")

    eq_res = await db.execute(select(Equipment).where(Equipment.equipment_id == payload.equipment_id))
    equipment = eq_res.scalars().first()

    if not equipment or equipment.stock < payload.quantity:
        raise HTTPException(status_code=400, detail="อุปกรณ์ไม่เพียงพอ หรือไม่พบรายการในระบบ")

    rental_fee = equipment.rental_price * payload.quantity
    booking.total_amount += rental_fee
    equipment.stock -= payload.quantity

    await db.commit()
    await db.refresh(booking)

    return {
        "message": f"เพิ่มการเช่า {equipment.name} จำนวน {payload.quantity} ชิ้นเรียบร้อยแล้ว",
        "rental_fee": rental_fee,
        "new_total_amount": booking.total_amount
    }