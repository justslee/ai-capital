from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

# Using relative import from backend.app
from app.config import settings # Point to config.py

# Create an async engine
async_engine = create_async_engine(settings.database_url, echo=False)

# Create a session factory
AsyncSessionFactory = sessionmaker(
    bind=async_engine,
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