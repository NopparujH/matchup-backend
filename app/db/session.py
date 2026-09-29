from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# สร้าง Async Engine สำหรับเชื่อมต่อ PostgreSQL ผ่าน asyncpg
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# สร้าง Session Factory สำหรับใช้งานในแต่ละ API request
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency สำหรับสร้าง DB Session ให้ API
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session