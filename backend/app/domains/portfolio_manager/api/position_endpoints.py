from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from ..schemas.position import PositionResponse
from ..services.position_service import PositionService
from ..services.portfolio_service import PortfolioService
from .user_endpoints import get_current_user

router = APIRouter()

@router.get("/portfolio/{portfolio_id}", response_model=List[PositionResponse])
async def get_portfolio_positions(portfolio_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    positions = await PositionService.get_portfolio_positions(db, portfolio_id)
    return positions