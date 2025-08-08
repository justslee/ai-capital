from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from ..models.portfolio import Portfolio
from ..schemas.portfolio import PortfolioCreate, PortfolioUpdate

class PortfolioService:
    
    @staticmethod
    async def create_portfolio(db: AsyncSession, user_id: int, portfolio_data: PortfolioCreate) -> Portfolio:
        db_portfolio = Portfolio(
            user_id=user_id,
            name=portfolio_data.name,
            description=portfolio_data.description,
            cash_balance=portfolio_data.cash_balance,
            portfolio_type=portfolio_data.portfolio_type
        )
        db.add(db_portfolio)
        await db.commit()
        await db.refresh(db_portfolio)
        return db_portfolio
    
    @staticmethod
    async def get_portfolio_by_id(db: AsyncSession, portfolio_id: int) -> Optional[Portfolio]:
        result = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_portfolios(db: AsyncSession, user_id: int) -> List[Portfolio]:
        result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
        return result.scalars().all()
    
    @staticmethod
    async def update_portfolio(db: AsyncSession, portfolio_id: int, portfolio_data: PortfolioUpdate) -> Optional[Portfolio]:
        portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
        if not portfolio:
            return None
        
        for field, value in portfolio_data.dict(exclude_unset=True).items():
            setattr(portfolio, field, value)
        
        await db.commit()
        await db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    async def delete_portfolio(db: AsyncSession, portfolio_id: int) -> bool:
        portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
        if not portfolio:
            return False
        
        await db.delete(portfolio)
        await db.commit()
        return True