"""
DuckDB + Parquet Storage Configuration

High-performance storage strategy using DuckDB for querying and 
Parquet for columnar storage with optimal compression.
"""

import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class DuckDBStorageConfig(BaseSettings):
    """DuckDB + Parquet storage configuration."""
    
    # Storage Paths
    data_root_path: str = "./data"
    parquet_path: str = "./data/parquet"
    duckdb_path: str = "./data/duckdb"
    exports_path: str = "./data/exports"
    temp_path: str = "./data/temp"
    
    # DuckDB Settings
    duckdb_main_file: str = "market_data.db"
    duckdb_analytics_file: str = "analytics.db"
    duckdb_memory_limit: str = "2GB"
    duckdb_threads: int = 4
    
    # Parquet Settings
    parquet_compression: str = "snappy"  # snappy, gzip, brotli
    parquet_row_group_size: int = 100000
    enable_partitioning: bool = True
    partition_by_year: bool = True
    partition_by_ticker: bool = False  # For very large datasets
    
    # Performance Settings
    enable_parallel_writes: bool = True
    batch_size: int = 10000
    enable_statistics: bool = True
    enable_bloom_filters: bool = True
    
    # Data Retention
    keep_raw_csv: bool = False  # Don't keep CSV after Parquet conversion
    compress_old_data: bool = True
    archive_threshold_years: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Parquet Schema Definitions
DAILY_PRICES_SCHEMA = {
    "ticker": "VARCHAR",
    "date": "DATE",
    "open": "DECIMAL(20,6)",
    "high": "DECIMAL(20,6)", 
    "low": "DECIMAL(20,6)",
    "close": "DECIMAL(20,6)",
    "volume": "BIGINT",
    "adj_close": "DECIMAL(20,6)",
    "adj_open": "DECIMAL(20,6)",
    "adj_high": "DECIMAL(20,6)",
    "adj_low": "DECIMAL(20,6)",
    "adj_volume": "BIGINT",
    "dividend_cash": "DECIMAL(10,6)",
    "split_factor": "DECIMAL(10,6)",
    "data_source": "VARCHAR",
    "ingestion_date": "TIMESTAMP"
}

TICKERS_SCHEMA = {
    "ticker": "VARCHAR PRIMARY KEY",
    "name": "VARCHAR",
    "exchange": "VARCHAR",
    "sector": "VARCHAR", 
    "industry": "VARCHAR",
    "market_cap": "DECIMAL(20,2)",
    "currency": "VARCHAR",
    "country": "VARCHAR",
    "is_active": "BOOLEAN",
    "created_at": "TIMESTAMP",
    "updated_at": "TIMESTAMP"
}

# DuckDB Optimization Settings
DUCKDB_SETTINGS = {
    "memory_limit": "2GB",
    "threads": 4,
    "enable_progress_bar": True,
    "preserve_insertion_order": False,
    "enable_object_cache": True
}

# Parquet Partitioning Strategy
PARTITIONING_STRATEGY = {
    "daily_prices": {
        "partition_cols": ["year"],
        "file_size_mb": 100,
        "compression": "snappy",
        "enable_statistics": True
    },
    "tickers": {
        "partition_cols": None,  # Small table, no partitioning
        "compression": "gzip",
        "enable_statistics": True
    },
    "ingestion_logs": {
        "partition_cols": ["year", "month"],
        "compression": "gzip",
        "enable_statistics": False
    }
}

# Query Optimization Patterns
QUERY_PATTERNS = {
    "time_series": {
        "description": "Time series analysis for single ticker",
        "example": "SELECT * FROM daily_prices WHERE ticker = ? AND date BETWEEN ? AND ?",
        "indexes": ["ticker", "date"],
        "partitioning": "year"
    },
    "cross_sectional": {
        "description": "Cross-sectional analysis at specific date",
        "example": "SELECT * FROM daily_prices WHERE date = ? AND ticker IN (?)",
        "indexes": ["date", "ticker"],
        "partitioning": "year"
    },
    "aggregations": {
        "description": "Aggregated statistics",
        "example": "SELECT ticker, AVG(close), MAX(volume) FROM daily_prices GROUP BY ticker",
        "indexes": ["ticker"],
        "partitioning": "year"
    }
}

# Common ML Feature Engineering Queries
ML_QUERY_TEMPLATES = {
    "returns": """
        SELECT ticker, date, close,
               (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / LAG(close) OVER (PARTITION BY ticker ORDER BY date) as daily_return
        FROM daily_prices 
        WHERE ticker = ? AND date BETWEEN ? AND ?
        ORDER BY date
    """,
    
    "moving_averages": """
        SELECT ticker, date, close,
               AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma_20,
               AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) as ma_50
        FROM daily_prices 
        WHERE ticker = ? AND date BETWEEN ? AND ?
        ORDER BY date
    """,
    
    "volatility": """
        SELECT ticker, date, close,
               STDDEV(daily_return) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as volatility_20d
        FROM (
            SELECT ticker, date, close,
                   (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / LAG(close) OVER (PARTITION BY ticker ORDER BY date) as daily_return
            FROM daily_prices 
            WHERE ticker = ? AND date BETWEEN ? AND ?
        ) returns
        ORDER BY date
    """,
    
    "cross_sectional": """
        SELECT date, ticker, close,
               RANK() OVER (PARTITION BY date ORDER BY close DESC) as price_rank,
               PERCENT_RANK() OVER (PARTITION BY date ORDER BY volume DESC) as volume_percentile
        FROM daily_prices 
        WHERE date BETWEEN ? AND ? AND ticker IN ({})
        ORDER BY date, ticker
    """
}

def get_storage_config() -> DuckDBStorageConfig:
    """Get the DuckDB storage configuration."""
    return DuckDBStorageConfig()

def get_parquet_path(table_name: str, partition_values: Dict[str, Any] = None) -> str:
    """Generate parquet file path with partitioning."""
    config = get_storage_config()
    base_path = Path(config.parquet_path) / table_name
    
    if partition_values:
        for key, value in partition_values.items():
            base_path = base_path / f"{key}={value}"
    
    return str(base_path)

def estimate_storage_savings() -> Dict[str, str]:
    """Estimate storage savings with Parquet vs PostgreSQL."""
    return {
        "postgresql_estimated": "2-3 GB",
        "parquet_compressed": "300-500 MB", 
        "savings_percent": "80-85%",
        "query_performance": "10-100x faster for analytics",
        "backup_size": "50-100 MB (compressed)"
    }

def get_recommended_parquet_settings() -> Dict[str, Any]:
    """Get recommended Parquet settings for financial data."""
    return {
        "compression": "snappy",  # Good balance of speed and compression
        "row_group_size": 100000,  # Optimal for time series queries
        "page_size": 1024 * 1024,  # 1MB pages
        "enable_dictionary": True,  # Great for ticker symbols
        "enable_statistics": True,  # Essential for query optimization
        "write_batch_size": 10000
    }

def get_duckdb_extensions() -> List[str]:
    """Get list of DuckDB extensions to install."""
    return [
        "parquet",      # Parquet file support
        "httpfs",       # HTTP/S3 file system support
        "json",         # JSON support
        "excel",        # Excel file support (for exports)
        "fts",          # Full-text search
        "spatial"       # Spatial extensions (future use)
    ] 