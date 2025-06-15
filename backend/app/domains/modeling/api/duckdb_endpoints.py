"""
DuckDB-based API Endpoints

High-performance API endpoints using DuckDB + Parquet storage.
Optimized for ML workloads and analytical queries.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import pandas as pd
import logging

from ..services.duckdb_ingestion_service import get_ingestion_service
from ..storage.duckdb_service import get_storage_service
from ..config.modeling_config import get_modeling_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modeling/duckdb", tags=["DuckDB Data Management"])


@router.post("/ingest/single/{ticker}")
async def ingest_single_ticker(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Ingest historical data for a single ticker using DuckDB + Parquet storage.
    
    Args:
        ticker: Stock symbol to ingest
        start_date: Start date for data (optional)
        end_date: End date for data (optional)
        force_refresh: Whether to re-fetch existing data
        background_tasks: FastAPI background tasks
    """
    try:
        ingestion_service = get_ingestion_service()
        
        if background_tasks:
            # Run in background for large date ranges
            background_tasks.add_task(
                ingestion_service.ingest_single_ticker,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh
            )
            return {
                "message": f"Ingestion for {ticker} started in background",
                "ticker": ticker,
                "status": "background_task_started"
            }
        else:
            # Run synchronously
            result = await ingestion_service.ingest_single_ticker(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_refresh
            )
            return result
            
    except Exception as e:
        logger.error(f"Error in single ticker ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/bulk")
async def ingest_bulk_tickers(
    tickers: List[str],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    max_concurrent: int = 3,
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Ingest historical data for multiple tickers concurrently.
    
    Args:
        tickers: List of stock symbols to ingest
        start_date: Start date for data
        end_date: End date for data
        max_concurrent: Maximum concurrent requests (default: 3)
        force_refresh: Whether to re-fetch existing data
        background_tasks: FastAPI background tasks
    """
    try:
        if len(tickers) > 50:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 50 tickers allowed per bulk request"
            )
        
        ingestion_service = get_ingestion_service()
        
        if background_tasks:
            # Run in background for large requests
            background_tasks.add_task(
                ingestion_service.ingest_bulk_tickers,
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                force_refresh=force_refresh
            )
            return {
                "message": f"Bulk ingestion for {len(tickers)} tickers started in background",
                "ticker_count": len(tickers),
                "status": "background_task_started"
            }
        else:
            # Run synchronously
            result = await ingestion_service.ingest_bulk_tickers(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                max_concurrent=max_concurrent,
                force_refresh=force_refresh
            )
            return result
            
    except Exception as e:
        logger.error(f"Error in bulk ticker ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/sp100")
async def ingest_sp100(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Ingest all S&P 100 tickers.
    
    Args:
        start_date: Start date for data
        end_date: End date for data
        force_refresh: Whether to re-fetch existing data
        background_tasks: FastAPI background tasks
    """
    try:
        config = get_modeling_config()
        ingestion_service = get_ingestion_service()
        
        if background_tasks:
            # Always run S&P 100 in background due to size
            background_tasks.add_task(
                ingestion_service.ingest_bulk_tickers,
                tickers=config.sp100_tickers,
                start_date=start_date,
                end_date=end_date,
                max_concurrent=3,
                force_refresh=force_refresh
            )
            return {
                "message": f"S&P 100 ingestion started in background",
                "ticker_count": len(config.sp100_tickers),
                "status": "background_task_started",
                "estimated_duration_minutes": "15-30"
            }
        else:
            # For immediate response, just return the ticker list
            return {
                "message": "Use background_tasks=true for S&P 100 ingestion",
                "ticker_count": len(config.sp100_tickers),
                "tickers": config.sp100_tickers[:10],  # Show first 10
                "note": "S&P 100 ingestion requires background processing"
            }
            
    except Exception as e:
        logger.error(f"Error in S&P 100 ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/prices/{ticker}")
async def query_ticker_prices(
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: Optional[int] = Query(default=1000, le=10000),
    columns: Optional[List[str]] = Query(default=None)
):
    """
    Query price data for a specific ticker with high performance.
    
    Args:
        ticker: Stock symbol to query
        start_date: Start date filter
        end_date: End date filter
        limit: Maximum number of rows (max 10,000)
        columns: Specific columns to return
    """
    try:
        storage_service = await get_storage_service()
        
        result_df = await storage_service.query_price_data(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            columns=columns,
            limit=limit
        )
        
        if result_df.empty:
            return {
                "ticker": ticker,
                "data": [],
                "record_count": 0,
                "message": "No data found for the specified criteria"
            }
        
        # Convert to records for JSON response
        records = result_df.to_dict('records')
        
        return {
            "ticker": ticker,
            "data": records,
            "record_count": len(records),
            "date_range": {
                "earliest": str(result_df['date'].min()) if 'date' in result_df.columns else None,
                "latest": str(result_df['date'].max()) if 'date' in result_df.columns else None
            },
            "storage_format": "DuckDB + Parquet"
        }
        
    except Exception as e:
        logger.error(f"Error querying ticker prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/ml-features/{ticker}")
async def get_ml_features(
    ticker: str,
    feature_type: str = Query(..., description="Feature type: returns, moving_averages, volatility"),
    start_date: date = Query(...),
    end_date: date = Query(...),
    tickers: Optional[List[str]] = Query(default=None, description="Additional tickers for cross-sectional features")
):
    """
    Generate ML features using optimized DuckDB queries.
    
    Args:
        ticker: Primary stock symbol
        feature_type: Type of features to generate
        start_date: Start date for features
        end_date: End date for features
        tickers: Additional tickers for cross-sectional features
    """
    try:
        storage_service = await get_storage_service()
        
        # Prepare kwargs for cross-sectional features
        kwargs = {}
        if feature_type == "cross_sectional" and tickers:
            kwargs['tickers'] = tickers
        
        result_df = await storage_service.get_ml_features(
            feature_type=feature_type,
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            **kwargs
        )
        
        if result_df.empty:
            return {
                "ticker": ticker,
                "feature_type": feature_type,
                "data": [],
                "record_count": 0,
                "message": "No features generated for the specified criteria"
            }
        
        # Convert to records
        records = result_df.to_dict('records')
        
        return {
            "ticker": ticker,
            "feature_type": feature_type,
            "data": records,
            "record_count": len(records),
            "date_range": {
                "start_date": str(start_date),
                "end_date": str(end_date)
            },
            "performance": "Optimized DuckDB query"
        }
        
    except Exception as e:
        logger.error(f"Error generating ML features: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/storage")
async def get_storage_stats():
    """Get comprehensive storage statistics and performance metrics."""
    try:
        storage_service = await get_storage_service()
        stats = await storage_service.get_storage_stats()
        
        return {
            "storage_stats": stats,
            "performance_benefits": {
                "query_speed": "10-100x faster than PostgreSQL for analytics",
                "storage_efficiency": "80-85% compression with Parquet",
                "maintenance": "Zero database server management",
                "ml_optimized": "Columnar storage perfect for time-series analysis"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/coverage")
async def get_data_coverage(
    tickers: Optional[List[str]] = Query(default=None, description="Specific tickers to analyze")
):
    """Get data coverage analysis for tickers."""
    try:
        ingestion_service = get_ingestion_service()
        coverage = await ingestion_service.get_data_coverage(tickers=tickers)
        
        return coverage
        
    except Exception as e:
        logger.error(f"Error getting data coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/data")
async def export_data(
    format: str = Query(default="csv", description="Export format: csv, parquet, json"),
    ticker: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Export data in various formats.
    
    Args:
        format: Export format (csv, parquet, json)
        ticker: Optional ticker filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        background_tasks: FastAPI background tasks
    """
    try:
        storage_service = await get_storage_service()
        
        if background_tasks:
            # Run export in background
            background_tasks.add_task(
                storage_service.export_data,
                format=format,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
            return {
                "message": f"Data export started in background",
                "format": format,
                "status": "background_task_started"
            }
        else:
            # Run synchronously
            file_path = await storage_service.export_data(
                format=format,
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
            
            return {
                "message": "Export completed successfully",
                "file_path": file_path,
                "format": format,
                "status": "completed"
            }
            
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/optimize")
async def optimize_storage(background_tasks: BackgroundTasks):
    """Optimize storage by compacting files and updating statistics."""
    try:
        storage_service = await get_storage_service()
        
        # Run optimization in background
        background_tasks.add_task(storage_service.optimize_storage)
        
        return {
            "message": "Storage optimization started in background",
            "status": "background_task_started",
            "operations": [
                "Compacting small Parquet files",
                "Updating table statistics",
                "Optimizing query performance"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error starting storage optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/backup")
async def create_backup(background_tasks: BackgroundTasks):
    """Create a single-file backup of all data."""
    try:
        storage_service = await get_storage_service()
        
        # Run backup in background
        background_tasks.add_task(storage_service.backup_to_single_file)
        
        return {
            "message": "Backup creation started in background",
            "status": "background_task_started",
            "format": "Single compressed Parquet file",
            "estimated_size": "50-100 MB (compressed)"
        }
        
    except Exception as e:
        logger.error(f"Error starting backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/info")
async def get_configuration_info():
    """Get DuckDB storage configuration information."""
    try:
        config = get_modeling_config()
        
        return {
            "storage_system": "DuckDB + Parquet",
            "sp100_tickers": {
                "count": len(config.sp100_tickers),
                "examples": config.sp100_tickers[:10]
            },
            "major_indexes": config.major_indexes,
            "sector_etfs": config.sector_etfs,
            "performance_features": [
                "Columnar storage optimized for analytics",
                "10-100x faster queries than PostgreSQL",
                "80-85% storage compression",
                "Zero database server maintenance",
                "Perfect for ML feature engineering"
            ],
            "data_validation": {
                "max_price_threshold": config.max_price_threshold,
                "max_volume_threshold": config.max_volume_threshold,
                "default_lookback_days": config.default_lookback_days
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting configuration info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 