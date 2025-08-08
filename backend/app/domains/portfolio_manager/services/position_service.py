from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from ..models.position import Position

class PositionService:
    
    @staticmethod
    async def get_position_by_id(db: AsyncSession, position_id: int) -> Optional[Position]:
        result = await db.execute(select(Position).where(Position.id == position_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_portfolio_positions(db: AsyncSession, portfolio_id: int) -> List[Position]:
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio_id)
            .order_by(Position.ticker)
        )
        return result.scalars().all()