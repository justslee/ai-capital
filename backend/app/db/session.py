from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

# Using absolute import from backend.app
from backend.app.config import settings # Point to config.py

# Create the async engine
engine = create_async_engine(settings.database_url, pool_pre_ping=True, echo=False)

# Create a session factory using async_sessionmaker (preferred)
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Basic dependency getter (might not be used if service layer doesn't need it yet)
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close() 