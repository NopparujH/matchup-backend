from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.models import User
from app.schemas.user import UserCreate, Token, UserOut
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. ตรวจสอบว่า Email ถูกใช้งานไปแล้วหรือยัง
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email this user is already registered."
        )

    # 2. บันทึกผู้ใช้ใหม่พร้อม Hash รหัสผ่าน
    new_user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        user_role=user_in.user_role
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """
    รองรับ Form Data จากปุ่ม Authorize ของ Swagger UI 
    โดย field 'username' ในแบบฟอร์มจะรับค่า Email ของผู้ใช้งาน
    """
    # 1. ค้นหาผู้ใช้ด้วย Email (รับมาจาก form_data.username)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    # 2. ตรวจสอบว่ามีผู้ใช้และรหัสผ่านถูกต้องหรือไม่
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect email or password."
        )

    # 3. สร้าง JWT Token ส่งกลับไป
    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user.user_role, "tier": user.tier_status}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """ดึงข้อมูลโปรไฟล์ของผู้ใช้ที่เข้าสู่ระบบด้วย JWT Token"""
    return current_user

from datetime import datetime, timedelta
from app.models.models import TierStatus

@router.post("/upgrade-pro", response_model=UserOut)
async def upgrade_to_pro(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """อัปเกรดสถานะผู้ใช้งานเป็น Pro Tier (ระยะเวลา 30 วัน)"""
    current_user.tier_status = TierStatus.PRO
    current_user.pro_expiry_date = datetime.utcnow() + timedelta(days=30)
    await db.commit()
    await db.refresh(current_user)
    return current_user