from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

class PositionResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    quantity: Decimal
    average_cost_basis: Decimal
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True