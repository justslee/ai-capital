"""
Market Data Models for Data Collection

Data models used for handling data within the data_collection domain.
"""

from typing import Optional, List
from datetime import date
from decimal import Decimal
from pydantic import BaseModel

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

class TiingoDataResponse(BaseModel):
    """Response from Tiingo API."""
    ticker: str
    start_date: date
    end_date: date
    frequency: str
    data: List[PriceDataPoint] 