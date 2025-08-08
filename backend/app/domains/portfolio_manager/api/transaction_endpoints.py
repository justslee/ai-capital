from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from ..schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate
from ..services.transaction_service import TransactionService
from ..services.portfolio_service import PortfolioService
from .user_endpoints import get_current_user

router = APIRouter()

@router.post("/", response_model=TransactionResponse)
async def create_transaction(transaction_data: TransactionCreate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.get_portfolio_by_id(db, transaction_data.portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    transaction = await TransactionService.create_transaction(db, transaction_data)
    return transaction

@router.get("/portfolio/{portfolio_id}", response_model=List[TransactionResponse])
async def get_portfolio_transactions(portfolio_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    portfolio = await PortfolioService.get_portfolio_by_id(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    transactions = await TransactionService.get_portfolio_transactions(db, portfolio_id)
    return transactions

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    transaction = await TransactionService.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    
    portfolio = await PortfolioService.get_portfolio_by_id(db, transaction.portfolio_id)
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    return transaction

@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(transaction_id: int, transaction_data: TransactionUpdate, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    transaction = await TransactionService.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    
    portfolio = await PortfolioService.get_portfolio_by_id(db, transaction.portfolio_id)
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    updated_transaction = await TransactionService.update_transaction(db, transaction_id, transaction_data)
    return updated_transaction

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: int, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    transaction = await TransactionService.get_transaction_by_id(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    
    portfolio = await PortfolioService.get_portfolio_by_id(db, transaction.portfolio_id)
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    success = await TransactionService.delete_transaction(db, transaction_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete transaction")
    return {"message": "Transaction deleted successfully"}