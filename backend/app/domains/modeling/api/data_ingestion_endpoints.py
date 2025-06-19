"""
Data Ingestion API Endpoints

API endpoints for managing data ingestion operations in the modeling domain.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_db
from ..data_ingestion.price_data_ingestion import price_data_ingestion_service
from ..config.modeling_config import get_sp100_symbols, get_all_target_symbols, get_index_symbols

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/modeling", tags=["modeling", "data-ingestion"])


# Request/Response Models
class IngestRequest(BaseModel):
    """Request model for price data ingestion."""
    ticker: str = Field(..., description="Stock symbol to ingest")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    source: str = Field("tiingo", description="Data source (tiingo or alphavantage)")


class BulkIngestRequest(BaseModel):
    """Request model for bulk price data ingestion."""
    tickers: Optional[List[str]] = Field(None, description="List of tickers (defaults to S&P 100)")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    source: str = Field("tiingo", description="Data source")
    max_concurrent: int = Field(5, description="Maximum concurrent requests")


class IngestResponse(BaseModel):
    """Response model for ingestion operations."""
    ticker: str
    status: str
    records_processed: Optional[int] = None
    records_inserted: Optional[int] = None
    records_updated: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    error: Optional[str] = None
    ingestion_date: str


class BulkIngestResponse(BaseModel):
    """Response model for bulk ingestion operations."""
    total_tickers: int
    successful: int
    failed: int
    total_records: int
    errors: List[str]
    started_at: str


# Individual Ticker Ingestion
@router.post("/ingest/{ticker}", response_model=IngestResponse)
async def ingest_ticker_data(
    ticker: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    source: str = Query("tiingo", description="Data source"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest historical price data for a single ticker.
    """
    try:
        logger.info(f"API request to ingest data for {ticker}")
        
        result = await price_data_ingestion_service.ingest_historical_prices(
            ticker=ticker.upper(),
            start_date=start_date,
            end_date=end_date,
            source=source,
            db=db
        )
        
        if "error" in result:
            return IngestResponse(
                ticker=ticker.upper(),
                status="failed",
                error=result["error"],
                ingestion_date=result["ingestion_date"]
            )
        else:
            return IngestResponse(
                ticker=ticker.upper(),
                status="completed",
                records_processed=result.get("records_processed"),
                records_inserted=result.get("records_inserted"),
                records_updated=result.get("records_updated"),
                start_date=result.get("start_date"),
                end_date=result.get("end_date"),
                ingestion_date=result["ingestion_date"]
            )
            
    except Exception as e:
        logger.error(f"API error ingesting data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Bulk Ingestion Endpoints
@router.post("/ingest/bulk/sp100", response_model=BulkIngestResponse)
async def bulk_ingest_sp100(
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    max_concurrent: int = Query(5, description="Maximum concurrent requests"),
    run_async: bool = Query(True, description="Run ingestion in background"),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk ingest historical data for S&P 100 companies.
    """
    try:
        logger.info("API request to bulk ingest S&P 100 data")
        
        if run_async:
            # Run in background
            background_tasks.add_task(
                _run_bulk_ingestion,
                price_data_ingestion_service.bulk_ingest_sp100,
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                db=db
            )
            
            return BulkIngestResponse(
                total_tickers=len(get_sp100_symbols()),
                successful=0,
                failed=0,
                total_records=0,
                errors=[],
                started_at=datetime.now().isoformat()
            )
        else:
            # Run synchronously
            result = await price_data_ingestion_service.bulk_ingest_sp100(
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                db=db
            )
            
            return BulkIngestResponse(
                total_tickers=result["total_tickers"],
                successful=result["successful"],
                failed=result["failed"],
                total_records=result["total_records"],
                errors=result["errors"],
                started_at=datetime.now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"API error in S&P 100 bulk ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/bulk/all", response_model=BulkIngestResponse)
async def bulk_ingest_all_targets(
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    max_concurrent: int = Query(5, description="Maximum concurrent requests"),
    run_async: bool = Query(True, description="Run ingestion in background"),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk ingest historical data for all target symbols (S&P 100 + indexes + ETFs).
    """
    try:
        logger.info("API request to bulk ingest all target symbols")
        
        if run_async:
            # Run in background
            background_tasks.add_task(
                _run_bulk_ingestion,
                price_data_ingestion_service.bulk_ingest_all_targets,
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                db=db
            )
            
            return BulkIngestResponse(
                total_tickers=len(get_all_target_symbols()),
                successful=0,
                failed=0,
                total_records=0,
                errors=[],
                started_at=datetime.now().isoformat()
            )
        else:
            # Run synchronously
            result = await price_data_ingestion_service.bulk_ingest_all_targets(
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                db=db
            )
            
            return BulkIngestResponse(
                total_tickers=result["total_tickers"],
                successful=result["successful"],
                failed=result["failed"],
                total_records=result["total_records"],
                errors=result["errors"],
                started_at=datetime.now().isoformat()
            )
            
    except Exception as e:
        logger.error(f"API error in bulk ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/bulk/custom")
async def bulk_ingest_custom_tickers(
    request: BulkIngestRequest,
    background_tasks: BackgroundTasks,
    run_async: bool = Query(True, description="Run ingestion in background"),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk ingest historical data for custom list of tickers.
    """
    try:
        tickers = request.tickers or get_sp100_symbols()
        logger.info(f"API request to bulk ingest {len(tickers)} custom tickers")
        
        if run_async:
            # Run in background
            background_tasks.add_task(
                _run_bulk_ingestion,
                price_data_ingestion_service.bulk_ingest_tickers,
                tickers=[ticker.upper() for ticker in tickers],
                start_date=request.start_date,
                end_date=request.end_date,
                max_concurrent=request.max_concurrent,
                db=db
            )
            
            return {
                "total_tickers": len(tickers),
                "message": "Bulk ingestion started in background",
                "started_at": datetime.now().isoformat()
            }
        else:
            # Run synchronously
            result = await price_data_ingestion_service.bulk_ingest_tickers(
                tickers=[ticker.upper() for ticker in tickers],
                start_date=request.start_date,
                end_date=request.end_date,
                max_concurrent=request.max_concurrent,
                db=db
            )
            
            return result
            
    except Exception as e:
        logger.error(f"API error in custom bulk ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Status and Monitoring Endpoints
@router.get("/ingest/status")
async def get_ingestion_status(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    source: Optional[str] = Query(None, description="Filter by source"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of data ingestion activities.
    """
    try:
        logs = await price_data_ingestion_service.get_ingestion_status(
            ticker=ticker.upper() if ticker else None,
            source=source,
            db=db
        )
        return {"ingestion_logs": logs}
        
    except Exception as e:
        logger.error(f"API error getting ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/coverage")
async def get_data_coverage(
    tickers: Optional[str] = Query(None, description="Comma-separated list of tickers"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get data coverage summary for tickers.
    """
    try:
        ticker_list = None
        if tickers:
            ticker_list = [ticker.strip().upper() for ticker in tickers.split(",")]
        
        coverage = await price_data_ingestion_service.get_data_coverage(
            tickers=ticker_list,
            db=db
        )
        
        return {"data_coverage": coverage}
        
    except Exception as e:
        logger.error(f"API error getting data coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols")
async def get_target_symbols():
    """
    Get lists of target symbols for ingestion.
    """
    return {
        "sp100_symbols": get_sp100_symbols(),
        "index_symbols": get_index_symbols(),
        "all_symbols": get_all_target_symbols(),
        "total_count": len(get_all_target_symbols())
    }


# Health Check
@router.get("/health")
async def health_check():
    """
    Health check endpoint for modeling domain.
    """
    try:
        # Test Tiingo connection if API key is available
        from ..services.tiingo_client import TiingoClient
        
        async with TiingoClient() as client:
            connection_ok = await client.test_connection()
            
        return {
            "status": "healthy",
            "tiingo_connection": "ok" if connection_ok else "failed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Background task helper
async def _run_bulk_ingestion(ingestion_func, **kwargs):
    """Helper function to run bulk ingestion in background."""
    try:
        logger.info("Starting background bulk ingestion task")
        result = await ingestion_func(**kwargs)
        logger.info(f"Background bulk ingestion completed: {result['successful']}/{result['total_tickers']} successful")
    except Exception as e:
        logger.error(f"Background bulk ingestion failed: {e}") 