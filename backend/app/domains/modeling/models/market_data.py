"""
Market Data Models

Data models for storing and managing market data from various sources.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Date, JSON, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# Enums
class IngestionStatus(Enum):
    """Status of data ingestion."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


# Pydantic Models for API responses
class TickerInfo(BaseModel):
    """Information about a stock ticker."""
    ticker: str
    name: str
    exchange: Optional[str] = None
    asset_type: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = "USD"
    country: Optional[str] = "US"
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    is_active: bool = True


class PriceDataPoint(BaseModel):
    """Single price data point."""
    ticker: str
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    volume: Optional[int] = None
    adj_close: Optional[Decimal] = None
    adj_open: Optional[Decimal] = None
    adj_high: Optional[Decimal] = None
    adj_low: Optional[Decimal] = None
    adj_volume: Optional[int] = None
    dividend_cash: Optional[Decimal] = None
    split_factor: Optional[Decimal] = None


class IndexData(BaseModel):
    """Index data point."""
    index_name: str
    date: date
    value: Decimal
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None


class TiingoDataResponse(BaseModel):
    """Response from Tiingo API."""
    ticker: str
    start_date: date
    end_date: date
    frequency: str
    data: List[PriceDataPoint]


class IngestionLog(BaseModel):
    """Log entry for data ingestion."""
    ticker: str
    start_date: date
    end_date: date
    records_processed: int
    records_stored: int
    status: IngestionStatus
    duration_seconds: float
    error_message: Optional[str] = None
    ingestion_date: datetime


# SQLAlchemy Models for database storage
class Ticker(Base):
    """Ticker information table."""
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    exchange = Column(String(50))
    asset_type = Column(String(50))
    description = Column(String(1000))
    currency = Column(String(10), default="USD")
    country = Column(String(10), default="US")
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Numeric(20, 2))
    is_active = Column(String(10), default="true")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyPrice(Base):
    """Daily price data table."""
    __tablename__ = "daily_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Numeric(20, 6))
    high = Column(Numeric(20, 6))
    low = Column(Numeric(20, 6))
    close = Column(Numeric(20, 6))
    volume = Column(Integer)
    adj_close = Column(Numeric(20, 6))
    adj_open = Column(Numeric(20, 6))
    adj_high = Column(Numeric(20, 6))
    adj_low = Column(Numeric(20, 6))
    adj_volume = Column(Integer)
    dividend_cash = Column(Numeric(10, 6))
    split_factor = Column(Numeric(10, 6))
    data_source = Column(String(50), default="tiingo")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_daily_prices_ticker_date', 'ticker', 'date', unique=True),
    )


class IndexPrice(Base):
    """Index price data table."""
    __tablename__ = "index_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    index_name = Column(String(50), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    value = Column(Numeric(20, 6), nullable=False)
    change = Column(Numeric(20, 6))
    change_percent = Column(Numeric(10, 6))
    data_source = Column(String(50), default="tiingo")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_index_prices_name_date', 'index_name', 'date', unique=True),
    )


class DataIngestionLog(Base):
    """Log of data ingestion activities."""
    __tablename__ = "data_ingestion_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True)
    data_type = Column(String(50), nullable=False)  # 'daily_prices', 'index_prices', etc.
    source = Column(String(50), nullable=False)     # 'tiingo', 'alphavantage', etc.
    start_date = Column(Date)
    end_date = Column(Date)
    records_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    error_message = Column(String(1000))
    ingestion_metadata = Column(JSON)  # Additional metadata about the ingestion
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# Market lists and constants
SP500_INDEX_SYMBOLS = ["SPY", "^GSPC"]
NASDAQ_INDEX_SYMBOLS = ["QQQ", "^IXIC", "^NDX"]
DOW_INDEX_SYMBOLS = ["DIA", "^DJI"]

ALL_MAJOR_INDEXES = SP500_INDEX_SYMBOLS + NASDAQ_INDEX_SYMBOLS + DOW_INDEX_SYMBOLS 