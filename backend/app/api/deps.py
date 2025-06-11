from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionFactory

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async database session."""
    async with AsyncSessionFactory() as session:
        # Add basic try/except/finally for safety,
        # although detailed transaction logic might be in the service layer.
        try:
            yield session
        except Exception:
            # Consider logging the exception here
            await session.rollback()
            raise
        finally:
            await session.close() 