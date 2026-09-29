from pydantic import BaseModel
from decimal import Decimal

class EquipmentOut(BaseModel):
    equipment_id: int
    name: str
    rental_price: Decimal
    stock: int

    class Config:
        from_attributes = True

class AddEquipmentRequest(BaseModel):
    equipment_id: int
    quantity: int