"""
Fundamentals Data Models

SQLAlchemy models for storing company fundamental data and financial ratios.
"""

from datetime import date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Float, Date, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base_class import Base


class FundamentalsData(Base):
    """
    Company fundamentals data table.
    
    Stores quarterly and annual financial ratios and metrics.
    """
    __tablename__ = "fundamentals_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    # period removed - this is daily fundamentals data
    
    # Valuation Ratios
    pe_ratio = Column(Float, nullable=True)
    pb_ratio = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    ps_ratio = Column(Float, nullable=True)
    pcf_ratio = Column(Float, nullable=True)
    ev_to_ebitda = Column(Float, nullable=True)
    ev_to_revenue = Column(Float, nullable=True)
    
    # Profitability Ratios
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_margin = Column(Float, nullable=True)
    roa = Column(Float, nullable=True)  # Return on Assets
    roe = Column(Float, nullable=True)  # Return on Equity
    roic = Column(Float, nullable=True)  # Return on Invested Capital
    
    # Liquidity Ratios
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    cash_ratio = Column(Float, nullable=True)
    
    # Leverage Ratios
    debt_to_equity = Column(Float, nullable=True)
    debt_to_assets = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)
    
    # Activity Ratios
    asset_turnover = Column(Float, nullable=True)
    inventory_turnover = Column(Float, nullable=True)
    receivables_turnover = Column(Float, nullable=True)
    
    # Growth Ratios
    revenue_growth = Column(Float, nullable=True)
    earnings_growth = Column(Float, nullable=True)
    
    # Market Data
    market_cap = Column(Float, nullable=True)
    enterprise_value = Column(Float, nullable=True)
    shares_outstanding = Column(Float, nullable=True)
    
    # Raw data storage for additional fields
    raw_data = Column(JSONB, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)


class FundamentalsDataPoint(BaseModel):
    """
    Pydantic model for fundamentals data point.
    
    Used for API responses and data validation.
    """
    ticker: str
    date: date
    # period removed - this is daily fundamentals data
    
    # Valuation Ratios
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    pcf_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    ev_to_revenue: Optional[float] = None
    
    # Profitability Ratios
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roa: Optional[float] = None  # Return on Assets
    roe: Optional[float] = None  # Return on Equity
    roic: Optional[float] = None  # Return on Invested Capital
    
    # Liquidity Ratios
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    
    # Leverage Ratios
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    
    # Activity Ratios
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    
    # Growth Ratios
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    
    # Market Data
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    shares_outstanding: Optional[float] = None
    
    # Raw data storage for additional fields
    raw_data: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class FundamentalsResponse(BaseModel):
    """Response model for fundamentals API endpoints."""
    ticker: str
    data_points: int
    date_range: Dict[str, Optional[date]]
    fundamentals: List[FundamentalsDataPoint]
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class FundamentalsStats(BaseModel):
    """Statistics model for fundamentals data."""
    total_records: int
    unique_tickers: int
    # periods removed - this is daily fundamentals data
    date_range: Dict[str, Optional[date]]
    coverage_by_ticker: Dict[str, int]
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class FundamentalsIngestionRequest(BaseModel):
    """Request model for fundamentals ingestion."""
    ticker: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # period removed - this is daily fundamentals data
    force_refresh: bool = False


class BulkFundamentalsIngestionRequest(BaseModel):
    """Request model for bulk fundamentals ingestion."""
    tickers: List[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    # period removed - this is daily fundamentals data
    max_concurrent: int = 2
    force_refresh: bool = False 