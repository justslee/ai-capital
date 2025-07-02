"""
S3 DuckDB API Endpoints

FastAPI endpoints for S3-backed financial data storage and retrieval.
Zero local storage footprint for work devices.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from ..services.s3_duckdb_ingestion_service import get_s3_ingestion_service
from ..storage.s3_duckdb_service import get_s3_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/s3-duckdb", tags=["modeling", "s3-duckdb"])


# Request/Response Models
class TickerIngestionRequest(BaseModel):
    ticker: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    force_refresh: bool = False


class BulkIngestionRequest(BaseModel):
    tickers: List[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_concurrent: int = 3
    force_refresh: bool = False


class PriceDataResponse(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float
    adj_open: float
    adj_high: float
    adj_low: float
    adj_volume: int
    dividend_cash: Optional[float] = None
    split_factor: float = 1.0


# Ingestion Endpoints
@router.post("/ingest/ticker")
async def ingest_ticker(request: TickerIngestionRequest):
    """Ingest historical data for a single ticker and store in S3."""
    try:
        service = await get_s3_ingestion_service()
        result = await service.ingest_single_ticker(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            force_refresh=request.force_refresh
        )
        return result
    except Exception as e:
        logger.error(f"Error in ticker ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/bulk")
async def ingest_bulk_tickers(request: BulkIngestionRequest):
    """Ingest historical data for multiple tickers in parallel and store in S3."""
    try:
        service = await get_s3_ingestion_service()
        result = await service.ingest_bulk_tickers(
            tickers=request.tickers,
            start_date=request.start_date,
            end_date=request.end_date,
            max_concurrent=request.max_concurrent,
            force_refresh=request.force_refresh
        )
        return result
    except Exception as e:
        logger.error(f"Error in bulk ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/ticker/{ticker}")
async def ingest_ticker_simple(
    ticker: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    force_refresh: bool = Query(False)
):
    """Simple endpoint to ingest a single ticker."""
    try:
        service = await get_s3_ingestion_service()
        result = await service.ingest_single_ticker(
            ticker=ticker.upper(),
            start_date=start_date,
            end_date=end_date,
            force_refresh=force_refresh
        )
        return result
    except Exception as e:
        logger.error(f"Error ingesting {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Retrieval Endpoints
@router.get("/data/{ticker}")
async def get_ticker_data(
    ticker: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(1000, le=10000)
) -> List[Dict[str, Any]]:
    """Get historical price data for a ticker from S3."""
    try:
        storage_service = await get_s3_storage_service()
        df = await storage_service.query_price_data(
            ticker=ticker.upper(),
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        
        # Convert to JSON-serializable format
        result = []
        for record in data:
            # Handle NaN and infinite values
            record_dict = {}
            for key, value in record.items():
                if isinstance(value, float):
                    if value != value or value == float('inf') or value == float('-inf'):
                        record_dict[key] = None
                    else:
                        record_dict[key] = value
                else:
                    record_dict[key] = value
            result.append(record_dict)
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/latest")
async def get_latest_price(ticker: str) -> Dict[str, Any]:
    """Get the latest price data for a ticker from S3."""
    try:
        storage_service = await get_s3_storage_service()
        df = await storage_service.query_price_data(
            ticker=ticker.upper(),
            limit=1
        )
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
        
        # Handle NaN and infinite values
        record = data[0]
        result = {}
        for key, value in record.items():
            if isinstance(value, float):
                if value != value or value == float('inf') or value == float('-inf'):
                    result[key] = None
                else:
                    result[key] = value
            else:
                result[key] = value
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving latest price for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/{ticker}/stats")
async def get_ticker_stats(ticker: str) -> Dict[str, Any]:
    """Get statistics for a ticker's data in S3."""
    try:
        storage_service = await get_s3_storage_service()
        stats = await storage_service.get_ticker_stats(ticker.upper())
        
        # Handle NaN and infinite values in stats
        clean_stats = {}
        for key, value in stats.items():
            if isinstance(value, float):
                if value != value or value == float('inf') or value == float('-inf'):
                    clean_stats[key] = None
                else:
                    clean_stats[key] = value
            else:
                clean_stats[key] = value
        
        return clean_stats
    except Exception as e:
        logger.error(f"Error retrieving stats for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analysis Endpoints
@router.get("/analysis/coverage")
async def get_data_coverage() -> Dict[str, Any]:
    """Get overall data coverage analysis from S3."""
    try:
        service = await get_s3_ingestion_service()
        coverage = await service.get_data_coverage()
        return coverage
    except Exception as e:
        logger.error(f"Error getting data coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/tickers")
async def get_available_tickers() -> List[str]:
    """Get list of all available tickers in S3."""
    try:
        storage_service = await get_s3_storage_service()
        tickers = await storage_service.get_available_tickers()
        return sorted(tickers)
    except Exception as e:
        logger.error(f"Error getting available tickers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/stats")
async def get_storage_stats() -> Dict[str, Any]:
    """Get S3 storage statistics."""
    try:
        storage_service = await get_s3_storage_service()
        stats = await storage_service.get_storage_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health Check
@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check for S3 DuckDB service."""
    try:
        storage_service = await get_s3_storage_service()
        # Simple test query
        await storage_service.get_storage_stats()
        return {"status": "healthy", "storage": "s3_duckdb"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)} 