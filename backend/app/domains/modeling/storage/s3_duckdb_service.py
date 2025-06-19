"""
S3-backed DuckDB Storage Service

Store all data in AWS S3 and query directly from S3 using DuckDB.
Perfect for work devices with minimal local storage requirements.
"""

import asyncio
import logging
import pandas as pd
import duckdb
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

from .s3_duckdb_config import get_s3_config, DUCKDB_S3_SETUP, S3_VIEW_TEMPLATES, S3_ML_QUERIES
from ..models.market_data import PriceDataPoint

logger = logging.getLogger(__name__)


class S3DuckDBStorageService:
    """DuckDB storage service with S3 backend - zero local storage footprint."""
    
    def __init__(self):
        self.config = get_s3_config()
        self._connection = None
        self._s3_client = None
        self._ensure_minimal_cache()
    
    def _ensure_minimal_cache(self):
        """Create minimal local cache directory."""
        cache_path = Path(self.config.local_cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize S3 connection and DuckDB with S3 support."""
        try:
            # Test S3 connection
            if not self.config.test_s3_connection():
                raise Exception("Cannot connect to S3. Check AWS credentials.")
            
            # Create bucket if needed
            if not self.config.create_bucket_if_not_exists():
                raise Exception("Cannot access or create S3 bucket.")
            
            # Initialize DuckDB with S3 support
            async with self.get_connection() as conn:
                # Install and configure S3 extension
                setup_query = DUCKDB_S3_SETUP.format(
                    region=self.config.aws_region,
                    access_key=self.config.aws_access_key_id,
                    secret_key=self.config.aws_secret_access_key
                )
                
                for statement in setup_query.split(';'):
                    if statement.strip():
                        conn.execute(statement)
                
                # Create views for S3 data
                await self._create_s3_views(conn)
                
            logger.info("S3 DuckDB storage service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 DuckDB service: {e}")
            raise
    
    async def _create_s3_views(self, conn):
        """Create views that point to S3 data."""
        try:
            s3_base_path = f"s3://{self.config.s3_bucket}/{self.config.s3_prefix}"
            
            for view_name, template in S3_VIEW_TEMPLATES.items():
                try:
                    view_query = template.format(s3_path=s3_base_path)
                    conn.execute(view_query)
                    logger.debug(f"Created S3 view: {view_name}")
                except Exception as e:
                    logger.warning(f"Could not create S3 view {view_name}: {e}")
                    
        except Exception as e:
            logger.warning(f"Could not create S3 views: {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get DuckDB connection with S3 configuration."""
        conn = duckdb.connect(
            database=':memory:',  # In-memory for zero local storage
            config={
                'memory_limit': self.config.duckdb_memory_limit,
                'threads': self.config.duckdb_threads
            }
        )
        
        try:
            yield conn
        finally:
            conn.close()
    
    async def store_price_data(
        self, 
        data: List[PriceDataPoint],
        ticker: str = None
    ) -> Dict[str, Any]:
        """
        Store price data directly to S3 as Parquet files.
        Zero local storage footprint.
        """
        try:
            if not data:
                return {"status": "no_data", "message": "No data to store"}
            
            # Convert to DataFrame
            df = pd.DataFrame([point.dict() for point in data])
            
            # Add partitioning column
            df['year'] = pd.to_datetime(df['date']).dt.year
            
            # Store partitioned by year in S3
            files_created = await self._store_s3_partitioned_parquet(df, 'daily_prices', ticker)
            
            logger.info(f"Stored {len(data)} records for {ticker} in {files_created} S3 files")
            
            return {
                "status": "success",
                "records_stored": len(data),
                "files_created": files_created,
                "storage_format": "s3_parquet",
                "partitioned": True,
                "compression": self.config.parquet_compression,
                "s3_bucket": self.config.s3_bucket,
                "s3_prefix": self.config.s3_prefix
            }
            
        except Exception as e:
            logger.error(f"Error storing price data to S3: {e}")
            raise
    
    async def _store_s3_partitioned_parquet(
        self, 
        df: pd.DataFrame, 
        table_name: str,
        ticker: str = None
    ) -> int:
        """Store DataFrame as partitioned Parquet files directly in S3."""
        
        files_created = 0
        s3_client = self.config.get_s3_client()
        
        if table_name == 'daily_prices' and 'year' in df.columns:
            # Get ticker from DataFrame if not provided
            if ticker is None and 'ticker' in df.columns:
                ticker = df['ticker'].iloc[0]
            
            # Delete existing files for this ticker first
            if ticker:
                await self._delete_existing_ticker_files(ticker, s3_client)
            
            # Partition by year for optimal query performance
            for year in df['year'].unique():
                year_df = df[df['year'] == year].drop('year', axis=1)
                
                # Generate S3 key with ticker name
                ticker_part = f"_{ticker}" if ticker else ""
                s3_key = f"{self.config.s3_prefix}/{table_name}/year={year}/{table_name}{ticker_part}_{year}.parquet"
                
                # Write to temporary local file first (minimal footprint)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                temp_file = Path(self.config.local_cache_dir) / f"temp_{ticker}_{year}_{timestamp}.parquet"
                
                try:
                    # Write Parquet file locally (temporary)
                    year_df.to_parquet(
                        temp_file,
                        compression=self.config.parquet_compression,
                        index=False,
                        engine='pyarrow',
                        row_group_size=self.config.parquet_row_group_size
                    )
                    
                    # Upload to S3
                    s3_client.upload_file(
                        str(temp_file),
                        self.config.s3_bucket,
                        s3_key
                    )
                    
                    files_created += 1
                    logger.debug(f"Uploaded to S3: s3://{self.config.s3_bucket}/{s3_key}")
                    
                finally:
                    # Clean up temporary file immediately
                    if temp_file.exists():
                        temp_file.unlink()
            
            return files_created
        else:
            # Single file for small tables
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ticker_part = f"_{ticker}" if ticker else ""
            s3_key = f"{self.config.s3_prefix}/{table_name}/{table_name}{ticker_part}_{timestamp}.parquet"
            temp_file = Path(self.config.local_cache_dir) / f"temp_{ticker}_{timestamp}.parquet"
            
            try:
                df.to_parquet(
                    temp_file, 
                    compression=self.config.parquet_compression, 
                    index=False,
                    engine='pyarrow'
                )
                
                s3_client.upload_file(
                    str(temp_file),
                    self.config.s3_bucket,
                    s3_key
                )
                
                return 1
                
            finally:
                if temp_file.exists():
                    temp_file.unlink()
    
    async def query_price_data(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Query price data directly from S3 using DuckDB.
        High performance with zero local storage.
        """
        async with self.get_connection() as conn:
            # Configure S3 access
            setup_query = DUCKDB_S3_SETUP.format(
                region=self.config.aws_region,
                access_key=self.config.aws_access_key_id,
                secret_key=self.config.aws_secret_access_key
            )
            
            for statement in setup_query.split(';'):
                if statement.strip():
                    conn.execute(statement)
            
            # Build query for S3 data
            s3_path = f"s3://{self.config.s3_bucket}/{self.config.s3_prefix}"
            select_cols = ", ".join(columns) if columns else "*"
            
            query = f"""
            SELECT {select_cols} 
            FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
            WHERE 1=1
            """
            params = []
            
            if ticker:
                query += " AND ticker = ?"
                params.append(ticker)
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date)
            
            query += " ORDER BY date DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            result = conn.execute(query, params).fetchdf()
            
            logger.debug(f"S3 query returned {len(result)} rows")
            return result
    
    async def get_ml_features(
        self,
        feature_type: str,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> pd.DataFrame:
        """Generate ML features from S3 data using optimized queries."""
        async with self.get_connection() as conn:
            # Configure S3 access
            setup_query = DUCKDB_S3_SETUP.format(
                region=self.config.aws_region,
                access_key=self.config.aws_access_key_id,
                secret_key=self.config.aws_secret_access_key
            )
            
            for statement in setup_query.split(';'):
                if statement.strip():
                    conn.execute(statement)
            
            if feature_type not in S3_ML_QUERIES:
                raise ValueError(f"Unknown feature type: {feature_type}")
            
            s3_path = f"s3://{self.config.s3_bucket}/{self.config.s3_prefix}"
            query = S3_ML_QUERIES[feature_type].format(s3_path=s3_path)
            params = [ticker, start_date, end_date]
            
            result = conn.execute(query, params).fetchdf()
            logger.debug(f"Generated {feature_type} features from S3: {len(result)} rows")
            return result
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics from S3."""
        try:
            async with self.get_connection() as conn:
                # Configure S3 access
                setup_query = DUCKDB_S3_SETUP.format(
                    region=self.config.aws_region,
                    access_key=self.config.aws_access_key_id,
                    secret_key=self.config.aws_secret_access_key
                )
                
                for statement in setup_query.split(';'):
                    if statement.strip():
                        conn.execute(statement)
                
                stats = {}
                
                try:
                    # Query S3 data for stats
                    s3_path = f"s3://{self.config.s3_bucket}/{self.config.s3_prefix}"
                    result = conn.execute(f"""
                        SELECT 
                            COUNT(*) as total_records,
                            COUNT(DISTINCT ticker) as unique_tickers,
                            MIN(date) as earliest_date,
                            MAX(date) as latest_date,
                            COUNT(DISTINCT date) as trading_days
                        FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
                    """).fetchone()
                    
                    stats['daily_prices'] = {
                        'total_records': result[0] if result[0] else 0,
                        'unique_tickers': result[1] if result[1] else 0, 
                        'earliest_date': str(result[2]) if result[2] else None,
                        'latest_date': str(result[3]) if result[3] else None,
                        'trading_days': result[4] if result[4] else 0
                    }
                except Exception as e:
                    logger.warning(f"Could not get S3 data stats: {e}")
                    stats['daily_prices'] = {'total_records': 0, 'unique_tickers': 0}
                
                # S3 storage stats
                try:
                    s3_client = self.config.get_s3_client()
                    paginator = s3_client.get_paginator('list_objects_v2')
                    
                    total_size = 0
                    file_count = 0
                    
                    for page in paginator.paginate(
                        Bucket=self.config.s3_bucket,
                        Prefix=f"{self.config.s3_prefix}/"
                    ):
                        for obj in page.get('Contents', []):
                            if obj['Key'].endswith('.parquet'):
                                total_size += obj['Size']
                                file_count += 1
                    
                    stats['storage'] = {
                        'total_size_mb': round(total_size / (1024 * 1024), 2),
                        'parquet_files': file_count,
                        'compression_ratio': 'estimated 80-85%',
                        'storage_format': 's3_parquet + duckdb',
                        's3_bucket': self.config.s3_bucket,
                        's3_prefix': self.config.s3_prefix
                    }
                except Exception as e:
                    logger.warning(f"Could not get S3 storage stats: {e}")
                    stats['storage'] = {'total_size_mb': 0, 'parquet_files': 0}
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting S3 storage stats: {e}")
            return {
                'daily_prices': {'total_records': 0, 'unique_tickers': 0},
                'storage': {'total_size_mb': 0, 'parquet_files': 0}
            }
    
    async def get_ticker_stats(self, ticker: str) -> Dict[str, Any]:
        """Get statistics for a specific ticker from S3."""
        try:
            async with self.get_connection() as conn:
                # Configure S3 access
                setup_query = DUCKDB_S3_SETUP.format(
                    region=self.config.aws_region,
                    access_key=self.config.aws_access_key_id,
                    secret_key=self.config.aws_secret_access_key
                )
                
                for statement in setup_query.split(';'):
                    if statement.strip():
                        conn.execute(statement)
                
                s3_path = f"s3://{self.config.s3_bucket}/{self.config.s3_prefix}"
                result = conn.execute(f"""
                    SELECT 
                        ticker,
                        COUNT(*) as total_records,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        AVG(close) as avg_close,
                        MIN(close) as min_close,
                        MAX(close) as max_close,
                        AVG(volume) as avg_volume
                    FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
                    WHERE ticker = ?
                    GROUP BY ticker
                """, [ticker]).fetchone()
                
                if result:
                    return {
                        'ticker': result[0],
                        'total_records': result[1],
                        'earliest_date': str(result[2]) if result[2] else None,
                        'latest_date': str(result[3]) if result[3] else None,
                        'avg_close': float(result[4]) if result[4] else None,
                        'min_close': float(result[5]) if result[5] else None,
                        'max_close': float(result[6]) if result[6] else None,
                        'avg_volume': int(result[7]) if result[7] else None
                    }
                else:
                    return {'ticker': ticker, 'total_records': 0}
                    
        except Exception as e:
            logger.error(f"Error getting ticker stats for {ticker}: {e}")
            return {'ticker': ticker, 'total_records': 0, 'error': str(e)}
    
    async def get_available_tickers(self) -> List[str]:
        """Get list of all available tickers in S3."""
        try:
            async with self.get_connection() as conn:
                # Configure S3 access
                setup_query = DUCKDB_S3_SETUP.format(
                    region=self.config.aws_region,
                    access_key=self.config.aws_access_key_id,
                    secret_key=self.config.aws_secret_access_key
                )
                
                for statement in setup_query.split(';'):
                    if statement.strip():
                        conn.execute(statement)
                
                s3_path = f"s3://{self.config.s3_bucket}/{self.config.s3_prefix}"
                result = conn.execute(f"""
                    SELECT DISTINCT ticker 
                    FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
                    ORDER BY ticker
                """).fetchall()
                
                return [row[0] for row in result]
                
        except Exception as e:
            logger.error(f"Error getting available tickers: {e}")
            return []

    async def _delete_existing_ticker_files(self, ticker: str, s3_client):
        """Delete existing files for a ticker to replace with fresh data."""
        try:
            # List all objects with the ticker in the name
            paginator = s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(
                Bucket=self.config.s3_bucket,
                Prefix=f"{self.config.s3_prefix}/daily_prices/"
            ):
                for obj in page.get('Contents', []):
                    # Check if this file contains the ticker
                    if f"_{ticker}_" in obj['Key'] or obj['Key'].endswith(f"_{ticker}.parquet"):
                        try:
                            s3_client.delete_object(
                                Bucket=self.config.s3_bucket,
                                Key=obj['Key']
                            )
                            logger.debug(f"Deleted existing file: {obj['Key']}")
                        except Exception as e:
                            logger.warning(f"Could not delete {obj['Key']}: {e}")
                            
        except Exception as e:
            logger.warning(f"Error deleting existing files for {ticker}: {e}")

    async def cleanup_cache(self):
        """Clean up minimal local cache."""
        cache_path = Path(self.config.local_cache_dir)
        if cache_path.exists():
            for file in cache_path.glob("temp_*.parquet"):
                try:
                    file.unlink()
                except:
                    pass
    
    async def close(self):
        """Clean up resources."""
        await self.cleanup_cache()


# Global service instance
_s3_storage_service = None

async def get_s3_storage_service() -> S3DuckDBStorageService:
    """Get the global S3 DuckDB storage service."""
    global _s3_storage_service
    if _s3_storage_service is None:
        _s3_storage_service = S3DuckDBStorageService()
        await _s3_storage_service.initialize()
    return _s3_storage_service 