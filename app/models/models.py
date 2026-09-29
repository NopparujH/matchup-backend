import enum
import uuid
from datetime import datetime, date, time
from sqlalchemy import (
    Column, String, Integer, Numeric, DateTime, Date, Time, 
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base

# --- Enum Definitions ---
class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    COACH = "coach"
    ADMIN = "admin"

class TierStatus(str, enum.Enum):
    FREE = "free"
    PRO = "pro"

class SportType(str, enum.Enum):
    BADMINTON = "badminton"
    FOOTBALL = "football"
    BASKETBALL = "basketball"

class BookingStatus(str, enum.Enum):
    HOLDING = "holding"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"


# --- ORM Models ---

class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_role = Column(
        SQLEnum(UserRole, name="user_role_enum", values_callable=lambda x: [e.value for e in x]),
        default=UserRole.CUSTOMER,
        nullable=False
    )
    tier_status = Column(
        SQLEnum(TierStatus, name="tier_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=TierStatus.FREE,
        nullable=False
    )
    pro_expiry_date = Column(DateTime, nullable=True)
    accumulated_slots_count = Column(Integer, default=0, nullable=False)
    free_slot_credits = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")


class SportsCourt(Base):
    __tablename__ = "sports_courts"

    court_id = Column(Integer, primary_key=True, autoincrement=True)
    sport_type = Column(
        SQLEnum(SportType, name="sport_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    court_name = Column(String(100), nullable=False)
    hourly_rate = Column(Numeric(10, 2), nullable=False)

    slots = relationship("BookingSlot", back_populates="court", cascade="all, delete-orphan")


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    status = Column(
        SQLEnum(BookingStatus, name="booking_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=BookingStatus.HOLDING,
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    slots = relationship("BookingSlot", back_populates="booking")
    rentals = relationship("EquipmentRental", back_populates="booking", cascade="all, delete-orphan")


class BookingSlot(Base):
    __tablename__ = "booking_slots"

    slot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.booking_id", ondelete="SET NULL"), nullable=True)
    court_id = Column(Integer, ForeignKey("sports_courts.court_id", ondelete="CASCADE"), nullable=False)
    booking_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    hold_expires_at = Column(DateTime, nullable=True)
    status = Column(
        SQLEnum(SlotStatus, name="slot_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=SlotStatus.AVAILABLE,
        nullable=False
    )

    court = relationship("SportsCourt", back_populates="slots")
    booking = relationship("Booking", back_populates="slots")


class EquipmentRental(Base):
    __tablename__ = "equipment_rentals"

    rental_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.booking_id", ondelete="CASCADE"), nullable=False)
    equipment_type = Column(String(100), nullable=False)
    rental_fee = Column(Numeric(10, 2), nullable=False)

    booking = relationship("Booking", back_populates="rentals")

class Equipment(Base):
    __tablename__ = "equipments"

    equipment_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rental_price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)