"""
Tiingo API Client

Client for interacting with the Tiingo API to fetch financial data.
Supports stock prices, index data, and metadata.
"""

# Standard library imports
import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union, Any

# Third-party imports
import aiohttp
import pandas as pd
from decimal import Decimal
from pydantic import ValidationError

# Domain imports (relative)
from ..config import get_data_collection_config
from ..models.market_data import PriceDataPoint, TickerInfo, TiingoDataResponse

logger = logging.getLogger(__name__)


class TiingoClient:
    """Client for Tiingo API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.config = get_data_collection_config()
        self.api_key = api_key or self.config.tiingo_api_key
        self.base_url = self.config.tiingo_base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
        if not self.api_key:
            raise ValueError("Tiingo API key is required. Set TIINGO_API_KEY environment variable.")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Token {self.api_key}"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def __aenter__(self):
        self.session = await self._get_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_ticker_metadata(self, ticker: str) -> Optional[TickerInfo]:
        """
        Get metadata for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            TickerInfo object or None if error
        """
        try:
            url = f"{self.base_url}/daily/{ticker}"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return TickerInfo(
                        ticker=data.get("ticker", ticker),
                        name=data.get("name", ""),
                        exchange=data.get("exchangeCode"),
                        description=data.get("description"),
                        currency=data.get("currency", "USD"),
                        country=data.get("country", "US"),
                        asset_type="stock"  # Tiingo primarily handles stocks
                    )
                else:
                    logger.error(f"Error fetching metadata for {ticker}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Exception getting metadata for {ticker}: {e}")
            return None
    
    async def get_historical_prices(
        self,
        ticker: str,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        frequency: str = "daily"
    ) -> Optional[List[PriceDataPoint]]:
        """
        Get historical price data for a ticker.
        
        Args:
            ticker: Stock symbol
            start_date: Start date (YYYY-MM-DD format or date object)
            end_date: End date (YYYY-MM-DD format or date object)
            frequency: Data frequency (daily, weekly, monthly)
            
        Returns:
            List of PriceDataPoint objects or None if error
        """
        try:
            # Format dates
            if end_date is None:
                end_date = date.today().isoformat()
            elif isinstance(end_date, date):
                end_date = end_date.isoformat()
            
            # Build URL and params
            url = f"{self.base_url}/daily/{ticker}/prices"
            params = {
                "endDate": end_date,
                "format": "json",
                "resampleFreq": frequency
            }
            
            # Only add startDate if specified - omitting it gets ALL available data
            if start_date is not None:
                if isinstance(start_date, date):
                    start_date = start_date.isoformat()
                params["startDate"] = start_date
            
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data:
                        return []
                    
                    price_points = []
                    for point in data:
                        if not point:  # Add a check for None here
                            continue
                        try:
                            price_point = PriceDataPoint(
                                ticker=ticker,
                                date=datetime.fromisoformat(point["date"].replace("Z", "+00:00")).date(),
                                open=Decimal(str(point.get("open", 0))) if point.get("open") else None,
                                high=Decimal(str(point.get("high", 0))) if point.get("high") else None,
                                low=Decimal(str(point.get("low", 0))) if point.get("low") else None,
                                close=Decimal(str(point.get("close", 0))) if point.get("close") else None,
                                volume=int(point.get("volume", 0)) if point.get("volume") else None,
                                adj_close=Decimal(str(point.get("adjClose", 0))) if point.get("adjClose") else None,
                                adj_open=Decimal(str(point.get("adjOpen", 0))) if point.get("adjOpen") else None,
                                adj_high=Decimal(str(point.get("adjHigh", 0))) if point.get("adjHigh") else None,
                                adj_low=Decimal(str(point.get("adjLow", 0))) if point.get("adjLow") else None,
                                adj_volume=int(point.get("adjVolume", 0)) if point.get("adjVolume") else None,
                                dividend_cash=Decimal(str(point.get("divCash", 0))) if point.get("divCash") else None,
                                split_factor=Decimal(str(point.get("splitFactor", 1))) if point.get("splitFactor") else None
                            )
                            price_points.append(price_point)
                        except Exception as point_error:
                            continue
                    
                    return price_points
                    
                elif response.status == 404:
                    return None
                elif response.status == 429:
                    return None
                else:
                    logger.error(f"Error fetching data for {ticker}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Exception getting historical data for {ticker}: {e}")
            return None
    
    async def get_latest_price(self, ticker: str) -> Optional[PriceDataPoint]:
        """
        Get the latest price for a ticker.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Latest PriceDataPoint or None if error
        """
        try:
            # Get last 2 days of data to ensure we have the latest
            end_date = date.today()
            start_date = end_date - timedelta(days=7)  # Get last week to be safe
            
            prices = await self.get_historical_prices(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
            
            if prices:
                return max(prices, key=lambda x: x.date)  # Return most recent
            return None
            
        except Exception as e:
            logger.error(f"Exception getting latest price for {ticker}: {e}")
            return None

    async def test_connection(self) -> bool:
        try:
            # Import ticker config for consistent testing
            from ..config.ticker_config import get_dow_tickers
            
            # Try to get metadata for the first DOW ticker (reliable test case)
            test_ticker = get_dow_tickers()[0]  # AAPL
            metadata = await self.get_ticker_metadata(test_ticker)
            if metadata and metadata.ticker == test_ticker:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Tiingo API connection failed: {e}")
            return False

    async def get_supported_tickers(self) -> List[str]:
        """
        Get list of supported tickers from Tiingo.
        Note: This might be a large list, use carefully.
        
        Returns:
            List of supported ticker symbols
        """
        try:
            url = f"{self.base_url}/daily"
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return [item["ticker"] for item in data if "ticker" in item]
                else:
                    logger.error(f"Error fetching supported tickers: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Exception getting supported tickers: {e}")
            return []
    
    async def bulk_fetch_historical_data(
        self,
        tickers: List[str],
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        max_concurrent: Optional[int] = None
    ) -> Dict[str, List[PriceDataPoint]]:
        """
        Bulk fetch historical data for multiple tickers concurrently.
        
        Args:
            tickers: List of stock symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            max_concurrent: Max concurrent requests
            
        Returns:
            Dictionary mapping ticker to list of price data points
        """
        if max_concurrent is None:
            max_concurrent = self.config.max_concurrent_requests
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def fetch_single_ticker(ticker: str):
            async with semaphore:
                try:
                    await asyncio.sleep(self.config.request_delay_seconds)  # Rate limiting
                    data = await self.get_historical_prices(ticker, start_date, end_date)
                    return ticker, data
                except Exception as e:
                    logger.error(f"Error fetching data for {ticker}: {e}")
                    return ticker, None
        
        # Create tasks for all tickers
        tasks = [fetch_single_ticker(ticker) for ticker in tickers]
        
        # Execute with progress logging
        completed = 0
        for task in asyncio.as_completed(tasks):
            ticker, data = await task
            results[ticker] = data
            completed += 1
            
        
        
        return results

_tiingo_client = None

def get_tiingo_client() -> "TiingoClient":
    """Provides a singleton instance of the TiingoClient."""
    global _tiingo_client
    if _tiingo_client is None:
        _tiingo_client = TiingoClient()
    return _tiingo_client 