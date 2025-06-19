"""
DuckDB-based Data Ingestion Service

High-performance data ingestion using DuckDB + Parquet storage.
Replaces the PostgreSQL-based ingestion with columnar storage optimized for ML workloads.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Set
import pandas as pd

from .tiingo_client import TiingoClient
from ..models.market_data import PriceDataPoint, IngestionLog, IngestionStatus
from ..storage.duckdb_service import get_storage_service
from ..config.modeling_config import get_modeling_config

logger = logging.getLogger(__name__)


class DuckDBIngestionService:
    """High-performance data ingestion service using DuckDB + Parquet."""
    
    def __init__(self):
        self.config = get_modeling_config()
        self._storage_service = None
    
    async def _get_storage_service(self):
        """Get the DuckDB storage service."""
        if self._storage_service is None:
            self._storage_service = await get_storage_service()
        return self._storage_service
    
    async def ingest_single_ticker(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest historical data for a single ticker.
        
        Args:
            ticker: Stock symbol to ingest
            start_date: Start date for data (defaults to config)
            end_date: End date for data (defaults to today)
            force_refresh: Whether to re-fetch existing data
            
        Returns:
            Ingestion result summary
        """
        start_time = datetime.utcnow()
        
        try:
            # Set default date range
            if not start_date:
                start_date = date.today() - timedelta(days=self.config.default_lookback_days)
            if not end_date:
                end_date = date.today()
            
            logger.info(f"Starting ingestion for {ticker} from {start_date} to {end_date}")
            
            # Fetch data from Tiingo using async context manager
            async with TiingoClient() as tiingo_client:
                raw_data = await tiingo_client.get_historical_prices(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date
                )
            
            if not raw_data:
                logger.warning(f"No data returned for {ticker}")
                return {
                    "ticker": ticker,
                    "status": "no_data",
                    "records_processed": 0,
                    "records_stored": 0
                }
            
            # Convert to PriceDataPoint objects (data is already in correct format from Tiingo client)
            price_points = []
            for data_point in raw_data:
                try:
                    # Validate data point
                    if self._validate_price_point(data_point):
                        price_points.append(data_point)
                    else:
                        logger.warning(f"Invalid data point for {ticker} on {data_point.date}")
                        
                except Exception as e:
                    logger.error(f"Error processing data point for {ticker}: {e}")
                    continue
            
            if not price_points:
                logger.warning(f"No valid data points for {ticker}")
                return {
                    "ticker": ticker,
                    "status": "no_valid_data",
                    "records_processed": len(raw_data),
                    "records_stored": 0
                }
            
            # Store in DuckDB + Parquet
            storage_service = await self._get_storage_service()
            storage_result = await storage_service.store_price_data(price_points, ticker)
            
            logger.info(f"Successfully ingested {storage_result['records_stored']} records for {ticker}")
            
            return {
                "ticker": ticker,
                "status": "success",
                "records_processed": len(raw_data),
                "records_stored": storage_result['records_stored'],
                "files_created": storage_result['files_created'],
                "storage_format": storage_result['storage_format'],
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Error ingesting data for {ticker}: {e}")
            
            return {
                "ticker": ticker,
                "status": "error",
                "error": str(e),
                "records_processed": 0,
                "records_stored": 0
            }
    
    async def ingest_bulk_tickers(
        self,
        tickers: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_concurrent: int = 5,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest historical data for multiple tickers concurrently.
        
        Args:
            tickers: List of stock symbols to ingest
            start_date: Start date for data
            end_date: End date for data
            max_concurrent: Maximum concurrent requests
            force_refresh: Whether to re-fetch existing data
            
        Returns:
            Bulk ingestion result summary
        """
        start_time = datetime.utcnow()
        
        logger.info(f"Starting bulk ingestion for {len(tickers)} tickers")
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def ingest_with_semaphore(ticker: str):
            async with semaphore:
                return await self.ingest_single_ticker(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh
                )
        
        # Execute concurrent ingestion
        tasks = [ingest_with_semaphore(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        skipped = 0
        total_records = 0
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                errors.append(f"{tickers[i]}: {str(result)}")
            elif result['status'] == 'success':
                successful += 1
                total_records += result['records_stored']
            elif result['status'] == 'skipped':
                skipped += 1
            else:
                failed += 1
                if 'error' in result:
                    errors.append(f"{result['ticker']}: {result['error']}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(f"Bulk ingestion completed: {successful} successful, {failed} failed, {skipped} skipped")
        
        return {
            "total_tickers": len(tickers),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "total_records_stored": total_records,
            "duration_seconds": duration,
            "errors": errors[:10],  # Limit error list
            "storage_format": "parquet + duckdb"
        }
    
    async def ingest_sp100(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Ingest all S&P 100 tickers."""
        return await self.ingest_bulk_tickers(
            tickers=self.config.sp100_tickers,
            start_date=start_date,
            end_date=end_date,
            max_concurrent=3,  # Conservative for free tier
            force_refresh=force_refresh
        )
    
    async def ingest_all_targets(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Ingest all configured targets (S&P 100 + indexes + ETFs)."""
        all_tickers = (
            self.config.sp100_tickers + 
            self.config.major_indexes + 
            self.config.sector_etfs
        )
        
        return await self.ingest_bulk_tickers(
            tickers=all_tickers,
            start_date=start_date,
            end_date=end_date,
            max_concurrent=3,
            force_refresh=force_refresh
        )
    
    async def _check_existing_coverage(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> Optional[Dict[str, Any]]:
        """Check existing data coverage for a ticker."""
        try:
            storage_service = await self._get_storage_service()
            
            # Query existing data
            existing_data = await storage_service.query_price_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                columns=['date']
            )
            
            if existing_data.empty:
                return None
            
            # Calculate coverage
            expected_days = (end_date - start_date).days + 1
            actual_days = len(existing_data)
            coverage_ratio = actual_days / expected_days
            
            return {
                "record_count": actual_days,
                "expected_days": expected_days,
                "coverage_ratio": coverage_ratio,
                "complete": coverage_ratio > 0.95,  # 95% threshold for "complete"
                "earliest_date": existing_data['date'].min(),
                "latest_date": existing_data['date'].max()
            }
            
        except Exception as e:
            logger.warning(f"Error checking coverage for {ticker}: {e}")
            return None
    
    def _validate_price_point(self, point: PriceDataPoint) -> bool:
        """Validate a price data point."""
        try:
            # Basic validation rules
            if not point.ticker or not point.date:
                return False
            
            # Price validation
            if point.close is not None:
                if point.close <= 0 or point.close > self.config.max_price_threshold:
                    return False
            
            # Volume validation
            if point.volume is not None:
                if point.volume < 0 or point.volume > self.config.max_volume_threshold:
                    return False
            
            # OHLC consistency
            if all(x is not None for x in [point.open, point.high, point.low, point.close]):
                if not (point.low <= point.open <= point.high and 
                       point.low <= point.close <= point.high):
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error validating price point: {e}")
            return False
    
    async def _log_ingestion(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        records_processed: int,
        records_stored: int,
        status: IngestionStatus,
        duration_seconds: float,
        error_message: Optional[str] = None
    ):
        """Log ingestion attempt."""
        try:
            log_entry = IngestionLog(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                records_processed=records_processed,
                records_stored=records_stored,
                status=status,
                duration_seconds=duration_seconds,
                error_message=error_message,
                ingestion_date=datetime.utcnow()
            )
            
            # Store log in Parquet (could be separate from main data)
            storage_service = await self._get_storage_service()
            
            # Convert to DataFrame for storage
            log_df = pd.DataFrame([{
                'ticker': log_entry.ticker,
                'start_date': log_entry.start_date,
                'end_date': log_entry.end_date,
                'records_processed': log_entry.records_processed,
                'records_stored': log_entry.records_stored,
                'status': log_entry.status.value,
                'duration_seconds': log_entry.duration_seconds,
                'error_message': log_entry.error_message,
                'ingestion_date': log_entry.ingestion_date,
                'year': log_entry.ingestion_date.year,
                'month': log_entry.ingestion_date.month
            }])
            
            # Store in partitioned logs
            await storage_service._store_partitioned_parquet(log_df, 'ingestion_logs')
            
        except Exception as e:
            logger.error(f"Error logging ingestion: {e}")
    
    async def get_ingestion_status(
        self,
        ticker: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get ingestion status and statistics."""
        try:
            storage_service = await self._get_storage_service()
            
            # Get overall storage stats
            storage_stats = await storage_service.get_storage_stats()
            
            # Get recent ingestion logs (would need to implement log querying)
            # For now, return storage stats
            
            return {
                "storage_stats": storage_stats,
                "ingestion_summary": {
                    "total_tickers": storage_stats['daily_prices']['unique_tickers'],
                    "total_records": storage_stats['daily_prices']['total_records'],
                    "date_range": {
                        "earliest": storage_stats['daily_prices']['earliest_date'],
                        "latest": storage_stats['daily_prices']['latest_date']
                    },
                    "storage_format": "DuckDB + Parquet",
                    "compression": "Snappy (estimated 80-85% savings)"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting ingestion status: {e}")
            return {"error": str(e)}
    
    async def get_data_coverage(
        self,
        tickers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get data coverage analysis for tickers."""
        try:
            storage_service = await self._get_storage_service()
            
            if not tickers:
                # Get all available tickers
                all_data = await storage_service.query_price_data(columns=['ticker'])
                tickers = all_data['ticker'].unique().tolist() if not all_data.empty else []
            
            coverage_results = {}
            
            for ticker in tickers:
                ticker_data = await storage_service.query_price_data(
                    ticker=ticker,
                    columns=['date']
                )
                
                if not ticker_data.empty:
                    dates = pd.to_datetime(ticker_data['date'])
                    coverage_results[ticker] = {
                        "record_count": len(ticker_data),
                        "earliest_date": str(dates.min().date()),
                        "latest_date": str(dates.max().date()),
                        "date_range_days": (dates.max() - dates.min()).days,
                        "has_recent_data": (datetime.now().date() - dates.max().date()).days < 7
                    }
                else:
                    coverage_results[ticker] = {
                        "record_count": 0,
                        "earliest_date": None,
                        "latest_date": None,
                        "date_range_days": 0,
                        "has_recent_data": False
                    }
            
            return {
                "coverage_by_ticker": coverage_results,
                "summary": {
                    "total_tickers_analyzed": len(tickers),
                    "tickers_with_data": len([t for t in coverage_results.values() if t['record_count'] > 0]),
                    "tickers_with_recent_data": len([t for t in coverage_results.values() if t['has_recent_data']])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting data coverage: {e}")
            return {"error": str(e)}


# Global service instance
_ingestion_service: Optional[DuckDBIngestionService] = None

def get_ingestion_service() -> DuckDBIngestionService:
    """Get the global DuckDB ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DuckDBIngestionService()
    return _ingestion_service 