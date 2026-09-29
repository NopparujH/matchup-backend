from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.api.auth import router as auth_router
from app.api.courts import router as courts_router
from app.api.bookings import router as bookings_router
from app.api.equipment import router as equipment_router

app = FastAPI(
    title="Match Up Backend API",
    description="Smart Multi-Sport Booking & Membership Platform API Gateway",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(courts_router)
app.include_router(bookings_router)
app.include_router(equipment_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Match Up API Gateway"}

@app.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        return {"status": "success", "database": "connected", "result": result.scalar()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Connection Failed: {str(e)}")