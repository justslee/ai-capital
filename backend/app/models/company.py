from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, func
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .financials import IncomeStatementDB, BalanceSheetDB, CashFlowDB

class Company(Base):
    """Model for company information."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    exchange = Column(String)
    sector = Column(String)
    industry = Column(String)
    description = Column(String)
    website = Column(String)
    ceo = Column(String)
    employees = Column(Integer)
    headquarters = Column(String)
    
    # Audit fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Metrics
    market_cap = Column(Float)
    pe_ratio = Column(Float)
    dividend_yield = Column(Float)
    beta = Column(Float)
    
    # Status fields
    is_active = Column(Boolean, default=True)
    has_financials = Column(Boolean, default=False) 