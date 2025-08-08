from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from typing import List, Optional
from decimal import Decimal

from ..models.transaction import Transaction
from ..models.position import Position
from ..schemas.transaction import TransactionCreate, TransactionUpdate

class TransactionService:
    
    @staticmethod
    async def create_transaction(db: AsyncSession, transaction_data: TransactionCreate) -> Transaction:
        db_transaction = Transaction(**transaction_data.dict())
        db.add(db_transaction)
        
        await TransactionService._update_position(db, transaction_data)
        
        await db.commit()
        await db.refresh(db_transaction)
        return db_transaction
    
    @staticmethod
    async def _update_position(db: AsyncSession, transaction_data: TransactionCreate):
        result = await db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == transaction_data.portfolio_id,
                    Position.ticker == transaction_data.ticker
                )
            )
        )
        position = result.scalar_one_or_none()
        
        if transaction_data.transaction_type.upper() == "BUY":
            if position:
                new_quantity = position.quantity + transaction_data.quantity
                new_cost_basis = (
                    (position.quantity * position.average_cost_basis) + 
                    (transaction_data.quantity * transaction_data.price_per_share)
                ) / new_quantity
                position.quantity = new_quantity
                position.average_cost_basis = new_cost_basis
            else:
                position = Position(
                    portfolio_id=transaction_data.portfolio_id,
                    ticker=transaction_data.ticker,
                    quantity=transaction_data.quantity,
                    average_cost_basis=transaction_data.price_per_share
                )
                db.add(position)
        
        elif transaction_data.transaction_type.upper() == "SELL" and position:
            position.quantity -= transaction_data.quantity
            if position.quantity <= 0:
                await db.delete(position)
    
    @staticmethod
    async def get_transaction_by_id(db: AsyncSession, transaction_id: int) -> Optional[Transaction]:
        result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_portfolio_transactions(db: AsyncSession, portfolio_id: int) -> List[Transaction]:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.transaction_date.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def update_transaction(db: AsyncSession, transaction_id: int, transaction_data: TransactionUpdate) -> Optional[Transaction]:
        transaction = await TransactionService.get_transaction_by_id(db, transaction_id)
        if not transaction:
            return None
        
        for field, value in transaction_data.dict(exclude_unset=True).items():
            setattr(transaction, field, value)
        
        await db.commit()
        await db.refresh(transaction)
        return transaction
    
    @staticmethod
    async def delete_transaction(db: AsyncSession, transaction_id: int) -> bool:
        transaction = await TransactionService.get_transaction_by_id(db, transaction_id)
        if not transaction:
            return False
        
        await db.delete(transaction)
        await db.commit()
        return True