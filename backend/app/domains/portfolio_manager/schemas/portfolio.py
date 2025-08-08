from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    cash_balance: Optional[Decimal] = Decimal("0")
    portfolio_type: Optional[str] = "taxable"

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cash_balance: Optional[Decimal] = None
    portfolio_type: Optional[str] = None

class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    cash_balance: Decimal
    portfolio_type: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True