from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

class TransactionCreate(BaseModel):
    portfolio_id: int
    ticker: str
    transaction_type: str
    quantity: Decimal
    price_per_share: Decimal
    total_value: Decimal
    fees: Optional[Decimal] = Decimal("0")
    transaction_date: datetime
    notes: Optional[str] = None

class TransactionUpdate(BaseModel):
    ticker: Optional[str] = None
    transaction_type: Optional[str] = None
    quantity: Optional[Decimal] = None
    price_per_share: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    transaction_date: Optional[datetime] = None
    notes: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    transaction_type: str
    quantity: Decimal
    price_per_share: Decimal
    total_value: Decimal
    fees: Decimal
    transaction_date: datetime
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True