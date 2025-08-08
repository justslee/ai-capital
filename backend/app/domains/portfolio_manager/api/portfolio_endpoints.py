from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from ..schemas.portfolio import PortfolioCreate, PortfolioResponse, PortfolioUpdate
from ..services.portfolio_service import PortfolioService
from .user_endpoints import get_current_user

router = APIRouter()

@router.post("/", response_model=PortfolioResponse)
async def create_portfolio(portfolio_data: PortfolioCreate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.create_portfolio(db, current_user.id, portfolio_data)
    return portfolio

@router.get("/", response_model=List[PortfolioResponse])
async def get_user_portfolios(current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolios = await PortfolioService.get_user_portfolios(db, current_user.id)
    return portfolios

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return portfolio

@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(portfolio_id: int, portfolio_data: PortfolioUpdate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    updated_portfolio = await PortfolioService.update_portfolio(db, portfolio_id, portfolio_data)
    return updated_portfolio

@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    success = await PortfolioService.delete_portfolio(db, portfolio_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete portfolio")
    return {"message": "Portfolio deleted successfully"}