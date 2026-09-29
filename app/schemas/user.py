from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from app.models.models import UserRole, TierStatus

# Schema สำหรับรับข้อมูลสมัครสมาชิก
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    user_role: Optional[UserRole] = UserRole.CUSTOMER

# Schema สำหรับรับข้อมูลเข้าสู่ระบบ
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Schema สำหรับส่งกลับ JWT Token
class Token(BaseModel):
    access_token: str
    token_type: str

# Schema สำหรับแสดงข้อมูลผู้ใช้ส่งกลับไปให้ Frontend
class UserOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    user_role: UserRole
    tier_status: TierStatus
    accumulated_slots_count: int
    free_slot_credits: int

    class Config:
        from_attributes = True