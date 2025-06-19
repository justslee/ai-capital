"""
Price Data Ingestion Service

Handles ingestion of historical price data for modeling purposes.
Supports Tiingo API and will support AlphaVantage in the future.
"""

import logging
import os
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import pandas as pd
import asyncio

from ..services.tiingo_client import TiingoClient
from ..models.market_data import DailyPrice, Ticker, DataIngestionLog, PriceDataPoint
from ..config.modeling_config import get_modeling_config, get_all_target_symbols, get_sp100_symbols

logger = logging.getLogger(__name__)

class PriceDataIngestionService:
    """Service for ingesting price data for modeling."""
    
    def __init__(self):
        self.config = get_modeling_config()
        self.tiingo_client: Optional[TiingoClient] = None
    
    async def ingest_historical_prices(
        self,
        ticker: str,
        start_date: Union[datetime, date, str],
        end_date: Optional[Union[datetime, date, str]] = None, 
        source: str = "tiingo",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Ingest historical price data for a ticker.
        
        Args:
            ticker: Stock symbol
            start_date: Start date for data ingestion
            end_date: End date for data ingestion (defaults to today)
            source: Data source to use ('tiingo' or 'alphavantage')
            db: Database session for storage
            
        Returns:
            Dictionary containing ingestion results
        """
        log_entry = None
        try:
            # Convert dates if needed
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date).date()
            elif isinstance(start_date, datetime):
                start_date = start_date.date()
                
            if end_date is None:
                end_date = date.today()
            elif isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date).date()
            elif isinstance(end_date, datetime):
                end_date = end_date.date()
            
            logger.info(f"Ingesting price data for {ticker} from {start_date} to {end_date} via {source}")
            
            # Create ingestion log entry
            if db:
                log_entry = DataIngestionLog(
                    ticker=ticker,
                    data_type="daily_prices",
                    source=source,
                    start_date=start_date,
                    end_date=end_date,
                    status="running"
                )
                db.add(log_entry)
                await db.flush()
            
            # 1. Fetch data from source
            price_data = await self._fetch_price_data(ticker, start_date, end_date, source)
            
            if not price_data:
                error_msg = f"No data retrieved for {ticker}"
                logger.warning(error_msg)
                if log_entry:
                    log_entry.status = "failed"
                    log_entry.error_message = error_msg
                    log_entry.completed_at = datetime.utcnow()
                    await db.commit()
                return {
                    "ticker": ticker,
                    "error": error_msg,
                    "ingestion_date": datetime.now().isoformat()
                }
            
            # 2. Validate and clean data  
            cleaned_data = await self._clean_price_data(price_data)
            
            # 3. Store in database
            records_inserted = 0
            records_updated = 0
            
            if db and cleaned_data:
                records_inserted, records_updated = await self._store_price_data(ticker, cleaned_data, db)
            
            # 4. Update log entry
            if log_entry:
                log_entry.records_processed = len(price_data)
                log_entry.records_inserted = records_inserted
                log_entry.records_updated = records_updated
                log_entry.status = "completed"
                log_entry.completed_at = datetime.utcnow()
                await db.commit()
            
            result = {
                "ticker": ticker,
                "records_processed": len(price_data),
                "records_inserted": records_inserted,
                "records_updated": records_updated,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "source": source,
                "ingestion_date": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully ingested {records_inserted + records_updated} records for {ticker}")
            return result
            
        except Exception as e:
            error_msg = f"Error ingesting price data for {ticker}: {e}"
            logger.error(error_msg)
            
            if log_entry and db:
                log_entry.status = "failed"
                log_entry.error_message = str(e)
                log_entry.completed_at = datetime.utcnow()
                await db.commit()
            
            return {
                "ticker": ticker,
                "error": str(e),
                "ingestion_date": datetime.now().isoformat()
            }
    
    async def _fetch_price_data(
        self, 
        ticker: str, 
        start_date: date, 
        end_date: date, 
        source: str
    ) -> Optional[List[PriceDataPoint]]:
        """Fetch price data from specified source."""
        logger.info(f"Fetching price data from {source} for {ticker}")
        
        if source == "tiingo":
            return await self._fetch_from_tiingo(ticker, start_date, end_date)
        elif source == "alphavantage":
            # TODO: Implement AlphaVantage fetching
            logger.warning("AlphaVantage source not yet implemented")
            return None
        else:
            logger.error(f"Unsupported data source: {source}")
            return None
    
    async def _fetch_from_tiingo(
        self, 
        ticker: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[List[PriceDataPoint]]:
        """Fetch data from Tiingo API."""
        try:
            async with TiingoClient() as client:
                return await client.get_historical_prices(ticker, start_date, end_date)
        except Exception as e:
            logger.error(f"Error fetching from Tiingo for {ticker}: {e}")
            return None
    
    async def _clean_price_data(self, data: List[PriceDataPoint]) -> List[PriceDataPoint]:
        """Clean and validate price data."""
        if not data:
            return []
            
        logger.info(f"Cleaning {len(data)} price data points")
        
        cleaned_data = []
        validation_rules = self.config.VALIDATION_RULES if hasattr(self.config, 'VALIDATION_RULES') else {
            "min_price": 0.01,
            "max_price": 100000.0,
            "min_volume": 0,
            "max_volume": 10_000_000_000,
        }
        
        for point in data:
            # Skip points with invalid data
            if not point.close or point.close <= 0:
                continue
                
            # Validate price ranges
            if point.close < validation_rules["min_price"] or point.close > validation_rules["max_price"]:
                logger.warning(f"Price {point.close} for {point.ticker} on {point.date} outside valid range")
                continue
                
            # Validate volume if present
            if point.volume and (point.volume < validation_rules["min_volume"] or point.volume > validation_rules["max_volume"]):
                logger.warning(f"Volume {point.volume} for {point.ticker} on {point.date} outside valid range")
                # Don't skip, just log - volume can be unusual
            
            cleaned_data.append(point)
        
        logger.info(f"Cleaned data: {len(cleaned_data)} valid records from {len(data)} original records")
        return cleaned_data
    
    async def _store_price_data(
        self, 
        ticker: str,
        data: List[PriceDataPoint], 
        db: AsyncSession
    ) -> tuple[int, int]:
        """
        Store price data in database using upsert (insert or update).
        
        Returns:
            Tuple of (records_inserted, records_updated)
        """
        if not data:
            return 0, 0
            
        logger.info(f"Storing {len(data)} price records for {ticker} in database")
        
        records_inserted = 0
        records_updated = 0
        
        try:
            # Prepare data for bulk upsert
            price_records = []
            for point in data:
                price_record = {
                    'ticker': point.ticker,
                    'date': point.date,
                    'open': point.open,
                    'high': point.high,
                    'low': point.low,
                    'close': point.close,
                    'volume': point.volume,
                    'adj_close': point.adj_close,
                    'adj_open': point.adj_open,
                    'adj_high': point.adj_high,
                    'adj_low': point.adj_low,
                    'adj_volume': point.adj_volume,
                    'dividend_cash': point.dividend_cash,
                    'split_factor': point.split_factor,
                    'data_source': 'tiingo',
                    'created_at': datetime.utcnow()
                }
                price_records.append(price_record)
            
            # Perform bulk upsert
            stmt = insert(DailyPrice).values(price_records)
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker', 'date'],
                set_={
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'close': stmt.excluded.close,
                    'volume': stmt.excluded.volume,
                    'adj_close': stmt.excluded.adj_close,
                    'adj_open': stmt.excluded.adj_open,
                    'adj_high': stmt.excluded.adj_high,
                    'adj_low': stmt.excluded.adj_low,
                    'adj_volume': stmt.excluded.adj_volume,
                    'dividend_cash': stmt.excluded.dividend_cash,
                    'split_factor': stmt.excluded.split_factor,
                    'data_source': stmt.excluded.data_source,
                }
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            # Note: PostgreSQL doesn't easily tell us insert vs update counts
            # For now, we'll assume all are inserts unless we implement more complex logic
            records_inserted = len(data)
            
            logger.info(f"Successfully stored {records_inserted} records for {ticker}")
            
        except Exception as e:
            logger.error(f"Error storing price data for {ticker}: {e}")
            await db.rollback()
            raise
            
        return records_inserted, records_updated


    async def bulk_ingest_sp100(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        db: Optional[AsyncSession] = None,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Bulk ingest historical data for S&P 100 companies.
        
        Args:
            start_date: Start date for ingestion
            end_date: End date for ingestion
            db: Database session
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Summary of ingestion results
        """
        tickers = get_sp100_symbols()
        return await self.bulk_ingest_tickers(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            db=db,
            max_concurrent=max_concurrent
        )
    
    async def bulk_ingest_all_targets(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        db: Optional[AsyncSession] = None,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Bulk ingest historical data for all target symbols (S&P 100 + indexes + ETFs).
        
        Args:
            start_date: Start date for ingestion
            end_date: End date for ingestion
            db: Database session
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Summary of ingestion results
        """
        tickers = get_all_target_symbols()
        return await self.bulk_ingest_tickers(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            db=db,
            max_concurrent=max_concurrent
        )
    
    async def bulk_ingest_tickers(
        self,
        tickers: List[str],
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        db: Optional[AsyncSession] = None,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Bulk ingest historical data for a list of tickers.
        
        Args:
            tickers: List of stock symbols
            start_date: Start date for ingestion
            end_date: End date for ingestion
            db: Database session
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Summary of ingestion results
        """
        if start_date is None:
            start_date = self.config.default_start_date
            
        logger.info(f"Starting bulk ingestion for {len(tickers)} tickers from {start_date}")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {
            "total_tickers": len(tickers),
            "successful": 0,
            "failed": 0,
            "total_records": 0,
            "ticker_results": {},
            "errors": []
        }
        
        async def ingest_single_ticker(ticker: str):
            async with semaphore:
                try:
                    # Add small delay between requests to respect rate limits
                    await asyncio.sleep(self.config.request_delay_seconds)
                    
                    result = await self.ingest_historical_prices(
                        ticker=ticker,
                        start_date=start_date,
                        end_date=end_date,
                        db=db
                    )
                    
                    return ticker, result
                except Exception as e:
                    logger.error(f"Error in bulk ingestion for {ticker}: {e}")
                    return ticker, {"error": str(e)}
        
        # Create tasks for all tickers
        tasks = [ingest_single_ticker(ticker) for ticker in tickers]
        
        # Execute with progress logging
        completed = 0
        for task in asyncio.as_completed(tasks):
            ticker, result = await task
            completed += 1
            
            results["ticker_results"][ticker] = result
            
            if "error" in result:
                results["failed"] += 1
                results["errors"].append(f"{ticker}: {result['error']}")
            else:
                results["successful"] += 1
                results["total_records"] += result.get("records_inserted", 0) + result.get("records_updated", 0)
            
            # Log progress every 10 completed tickers
            if completed % 10 == 0:
                logger.info(f"Bulk ingestion progress: {completed}/{len(tickers)} completed "
                           f"({results['successful']} successful, {results['failed']} failed)")
        
        logger.info(f"Bulk ingestion completed: {results['successful']}/{len(tickers)} successful, "
                   f"{results['total_records']} total records ingested")
        
        return results
    
    async def get_ingestion_status(
        self,
        ticker: Optional[str] = None,
        source: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get status of data ingestion activities.
        
        Args:
            ticker: Filter by ticker (optional)
            source: Filter by data source (optional)
            db: Database session
            
        Returns:
            List of ingestion log entries
        """
        if not db:
            return []
            
        query = db.query(DataIngestionLog)
        
        if ticker:
            query = query.filter(DataIngestionLog.ticker == ticker)
        if source:
            query = query.filter(DataIngestionLog.source == source)
            
        query = query.order_by(DataIngestionLog.created_at.desc()).limit(100)
        
        logs = await query.all()
        
        return [
            {
                "id": log.id,
                "ticker": log.ticker,
                "data_type": log.data_type,
                "source": log.source,
                "start_date": log.start_date.isoformat() if log.start_date else None,
                "end_date": log.end_date.isoformat() if log.end_date else None,
                "records_processed": log.records_processed,
                "records_inserted": log.records_inserted,
                "records_updated": log.records_updated,
                "status": log.status,
                "error_message": log.error_message,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            }
            for log in logs
        ]
    
    async def get_data_coverage(
        self,
        tickers: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get summary of data coverage for tickers.
        
        Args:
            tickers: List of tickers to check (defaults to all targets)
            db: Database session
            
        Returns:
            Data coverage summary
        """
        if not db:
            return {}
            
        if tickers is None:
            tickers = get_all_target_symbols()
        
        coverage = {}
        
        for ticker in tickers:
            query = db.query(DailyPrice).filter(DailyPrice.ticker == ticker)
            
            count = await query.count()
            if count > 0:
                earliest = await query.order_by(DailyPrice.date.asc()).first()
                latest = await query.order_by(DailyPrice.date.desc()).first()
                
                coverage[ticker] = {
                    "record_count": count,
                    "earliest_date": earliest.date.isoformat(),
                    "latest_date": latest.date.isoformat(),
                    "data_source": earliest.data_source
                }
            else:
                coverage[ticker] = {
                    "record_count": 0,
                    "earliest_date": None,
                    "latest_date": None,
                    "data_source": None
                }
        
        return coverage


# Service instance
price_data_ingestion_service = PriceDataIngestionService() 