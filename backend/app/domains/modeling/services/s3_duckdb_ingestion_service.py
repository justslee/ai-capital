"""
S3 DuckDB Ingestion Service

Ingests financial data and stores it directly in AWS S3 using DuckDB.
Zero local storage footprint for work devices.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd

from .tiingo_client import TiingoClient
from ..storage.s3_duckdb_service import get_s3_storage_service
from ..models.market_data import PriceDataPoint, IngestionLog, IngestionStatus
from ..config.modeling_config import get_modeling_config

logger = logging.getLogger(__name__)


class S3DuckDBIngestionService:
    """Ingestion service that stores data in S3 using DuckDB."""
    
    def __init__(self):
        self.config = get_modeling_config()
        self._storage_service = None
    
    async def get_storage_service(self):
        """Get the S3 storage service."""
        if self._storage_service is None:
            self._storage_service = await get_s3_storage_service()
        return self._storage_service
    
    async def ingest_single_ticker(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest historical data for a single ticker and store in S3.
        
        Args:
            ticker: Stock symbol
            start_date: Start date for data fetch
            end_date: End date for data fetch
            force_refresh: Whether to re-fetch existing data
            
        Returns:
            Dictionary with ingestion results
        """
        try:
            logger.info(f"Starting S3 ingestion for {ticker}")
            
            # Set default dates - get ALL available historical data
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = None  # Let Tiingo return all available data
            
            # Fetch data from Tiingo
            async with TiingoClient() as client:
                price_points = await client.get_historical_prices(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date
                )
            
            if not price_points:
                logger.warning(f"No data received for {ticker}")
                return {
                    "status": "no_data",
                    "ticker": ticker,
                    "message": f"No data available for {ticker}",
                    "records_processed": 0,
                    "records_stored": 0
                }
            
            # Price points already have the data we need from TiingoClient
            # No need to modify them as they're already PriceDataPoint objects
            
            # Store in S3
            storage_service = await self.get_storage_service()
            storage_result = await storage_service.store_price_data(
                data=price_points,
                ticker=ticker
            )
            
            logger.info(f"S3 ingestion completed for {ticker}: {len(price_points)} records")
            
            return {
                "status": "success",
                "ticker": ticker,
                "records_processed": len(price_points),
                "records_stored": len(price_points),
                "files_created": storage_result.get("files_created", 0),
                "storage_format": "s3_parquet",
                "s3_bucket": storage_result.get("s3_bucket"),
                "s3_prefix": storage_result.get("s3_prefix"),
                "compression": storage_result.get("compression"),
                "duration_seconds": 0  # Will be calculated by caller
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {ticker}: {e}")
            return {
                "status": "error",
                "ticker": ticker,
                "error": str(e),
                "records_processed": 0,
                "records_stored": 0
            }
    
    async def ingest_bulk_tickers(
        self,
        tickers: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_concurrent: int = 3,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Ingest historical data for multiple tickers in parallel.
        
        Args:
            tickers: List of stock symbols
            start_date: Start date for data fetch
            end_date: End date for data fetch
            max_concurrent: Maximum concurrent requests
            force_refresh: Whether to re-fetch existing data
            
        Returns:
            Dictionary with bulk ingestion results
        """
        start_time = datetime.utcnow()
        
        logger.info(f"Starting S3 bulk ingestion for {len(tickers)} tickers")
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def ingest_with_semaphore(ticker: str):
            async with semaphore:
                return await self.ingest_single_ticker(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh
                )
        
        # Execute all ingestions concurrently
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
            elif result['status'] == 'no_data':
                skipped += 1
            else:
                failed += 1
                errors.append(f"{tickers[i]}: {result.get('error', 'Unknown error')}")
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"S3 bulk ingestion completed: {successful} successful, {failed} failed, {skipped} skipped")
        
        return {
            "status": "completed",
            "total_tickers": len(tickers),
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "total_records_stored": total_records,
            "duration_seconds": duration,
            "storage_format": "s3_parquet",
            "errors": errors[:10]  # Limit to first 10 errors
        }
    
    async def get_data_coverage(
        self,
        tickers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get data coverage analysis from S3."""
        try:
            storage_service = await self.get_storage_service()
            stats = await storage_service.get_storage_stats()
            
            return {
                "total_records": stats['daily_prices']['total_records'],
                "unique_tickers": stats['daily_prices']['unique_tickers'],
                "date_range": {
                    "earliest": stats['daily_prices']['earliest_date'],
                    "latest": stats['daily_prices']['latest_date']
                },
                "storage": {
                    "format": "s3_parquet",
                    "size_mb": stats['storage']['total_size_mb'],
                    "files": stats['storage']['parquet_files'],
                    "bucket": stats['storage'].get('s3_bucket'),
                    "prefix": stats['storage'].get('s3_prefix')
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting data coverage: {e}")
            return {
                "total_records": 0,
                "unique_tickers": 0,
                "error": str(e)
            }


# Global service instance
_s3_ingestion_service = None

async def get_s3_ingestion_service() -> S3DuckDBIngestionService:
    """Get the global S3 DuckDB ingestion service."""
    global _s3_ingestion_service
    if _s3_ingestion_service is None:
        _s3_ingestion_service = S3DuckDBIngestionService()
    return _s3_ingestion_service 