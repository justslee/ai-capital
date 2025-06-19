"""
DuckDB Storage Service

High-performance storage service using DuckDB + Parquet for financial data.
Optimized for time-series analysis and ML feature engineering.
"""

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import logging
import asyncio
from contextlib import asynccontextmanager
import json

from .duckdb_config import (
    get_storage_config, 
    DAILY_PRICES_SCHEMA, 
    TICKERS_SCHEMA,
    DUCKDB_SETTINGS,
    get_parquet_path,
    get_duckdb_extensions,
    ML_QUERY_TEMPLATES
)
from ..models.market_data import PriceDataPoint

logger = logging.getLogger(__name__)


class DuckDBStorageService:
    """High-performance storage service using DuckDB + Parquet."""
    
    def __init__(self):
        self.config = get_storage_config()
        self._ensure_directories()
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
        self._initialized = False
    
    def _ensure_directories(self):
        """Create necessary directories."""
        for path in [
            self.config.parquet_path,
            self.config.duckdb_path, 
            self.config.exports_path,
            self.config.temp_path,
            f"{self.config.parquet_path}/daily_prices",
            f"{self.config.parquet_path}/tickers",
            f"{self.config.parquet_path}/ingestion_logs"
        ]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize DuckDB connection and setup."""
        if self._initialized:
            return
            
        try:
            db_path = Path(self.config.duckdb_path) / self.config.duckdb_main_file
            self._connection = duckdb.connect(str(db_path))
            
            # Install extensions
            for extension in get_duckdb_extensions():
                try:
                    self._connection.execute(f"INSTALL {extension}")
                    self._connection.execute(f"LOAD {extension}")
                    logger.debug(f"Loaded DuckDB extension: {extension}")
                except Exception as e:
                    logger.warning(f"Could not load extension {extension}: {e}")
            
            # Apply optimization settings
            for setting, value in DUCKDB_SETTINGS.items():
                try:
                    self._connection.execute(f"SET {setting} = '{value}'")
                except Exception as e:
                    logger.warning(f"Could not set {setting}: {e}")
            
            # Create views for existing data
            await self._create_views()
            
            self._initialized = True
            logger.info("DuckDB storage service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB storage service: {e}")
            raise
    
    async def _create_views(self):
        """Create DuckDB views for Parquet files."""
        try:
            # Daily prices view
            daily_prices_pattern = f"{self.config.parquet_path}/daily_prices/**/*.parquet"
            self._connection.execute(f"""
                CREATE OR REPLACE VIEW daily_prices AS 
                SELECT * FROM read_parquet('{daily_prices_pattern}', hive_partitioning=true)
            """)
            
            # Tickers view
            tickers_pattern = f"{self.config.parquet_path}/tickers/*.parquet"
            self._connection.execute(f"""
                CREATE OR REPLACE VIEW tickers AS 
                SELECT * FROM read_parquet('{tickers_pattern}')
            """)
            
            # Useful analytical views
            self._connection.execute("""
                CREATE OR REPLACE VIEW latest_prices AS
                SELECT ticker, MAX(date) as latest_date, 
                       FIRST(close ORDER BY date DESC) as latest_close,
                       FIRST(volume ORDER BY date DESC) as latest_volume
                FROM daily_prices 
                GROUP BY ticker
            """)
            
            self._connection.execute("""
                CREATE OR REPLACE VIEW price_summary AS
                SELECT 
                    ticker,
                    COUNT(*) as record_count,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date,
                    AVG(close) as avg_close,
                    MIN(close) as min_close,
                    MAX(close) as max_close,
                    AVG(volume) as avg_volume
                FROM daily_prices 
                GROUP BY ticker
            """)
            
            logger.debug("Created DuckDB views successfully")
            
        except Exception as e:
            logger.warning(f"Could not create views (may be no data yet): {e}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get DuckDB connection with automatic initialization."""
        if not self._initialized:
            await self.initialize()
        
        try:
            yield self._connection
        except Exception as e:
            logger.error(f"Error in DuckDB operation: {e}")
            raise
    
    async def store_price_data(
        self, 
        data: List[PriceDataPoint],
        ticker: str = None
    ) -> Dict[str, Any]:
        """
        Store price data in Parquet format with DuckDB indexing.
        
        Args:
            data: List of price data points
            ticker: Optional ticker for single-ticker optimization
            
        Returns:
            Storage result summary
        """
        if not data:
            return {"records_stored": 0, "files_created": 0}
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'ticker': point.ticker,
                'date': point.date,
                'open': float(point.open) if point.open else None,
                'high': float(point.high) if point.high else None,
                'low': float(point.low) if point.low else None,
                'close': float(point.close) if point.close else None,
                'volume': point.volume,
                'adj_close': float(point.adj_close) if point.adj_close else None,
                'adj_open': float(point.adj_open) if point.adj_open else None,
                'adj_high': float(point.adj_high) if point.adj_high else None,
                'adj_low': float(point.adj_low) if point.adj_low else None,
                'adj_volume': point.adj_volume,
                'dividend_cash': float(point.dividend_cash) if point.dividend_cash else None,
                'split_factor': float(point.split_factor) if point.split_factor else None,
                'data_source': 'tiingo',
                'ingestion_date': datetime.utcnow(),
                'year': point.date.year  # For partitioning
            } for point in data])
            
            # Store in partitioned Parquet files
            files_created = await self._store_partitioned_parquet(df, 'daily_prices')
            
            # Update DuckDB views
            await self._create_views()
            
            logger.info(f"Stored {len(data)} records in {files_created} Parquet files")
            
            return {
                "records_stored": len(data),
                "files_created": files_created,
                "storage_format": "parquet",
                "partitioned": True,
                "compression": self.config.parquet_compression
            }
            
        except Exception as e:
            logger.error(f"Error storing price data: {e}")
            raise
    
    async def _store_partitioned_parquet(
        self, 
        df: pd.DataFrame, 
        table_name: str
    ) -> int:
        """Store DataFrame as partitioned Parquet files."""
        
        if table_name == 'daily_prices' and 'year' in df.columns:
            # Partition by year for optimal query performance
            files_created = 0
            
            for year in df['year'].unique():
                year_df = df[df['year'] == year].drop('year', axis=1)
                
                # Create partition path
                partition_path = get_parquet_path(table_name, {'year': year})
                Path(partition_path).mkdir(parents=True, exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{table_name}_{year}_{timestamp}.parquet"
                file_path = Path(partition_path) / filename
                
                # Write Parquet file with optimization
                year_df.to_parquet(
                    file_path,
                    compression=self.config.parquet_compression,
                    index=False,
                    engine='pyarrow',
                    row_group_size=self.config.parquet_row_group_size
                )
                
                files_created += 1
                logger.debug(f"Created Parquet file: {file_path}")
            
            return files_created
        else:
            # Single file for small tables
            file_path = Path(self.config.parquet_path) / table_name / f"{table_name}.parquet"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            df.to_parquet(
                file_path, 
                compression=self.config.parquet_compression, 
                index=False,
                engine='pyarrow'
            )
            return 1
    
    async def query_price_data(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Query price data with high performance.
        
        Args:
            ticker: Stock symbol filter
            start_date: Start date filter
            end_date: End date filter
            columns: Specific columns to return
            limit: Maximum number of rows
            
        Returns:
            DataFrame with query results
        """
        async with self.get_connection() as conn:
            # Build query
            select_cols = ", ".join(columns) if columns else "*"
            query = f"SELECT {select_cols} FROM daily_prices WHERE 1=1"
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
            
            logger.debug(f"Query returned {len(result)} rows")
            return result
    
    async def get_ml_features(
        self,
        feature_type: str,
        ticker: str,
        start_date: date,
        end_date: date,
        **kwargs
    ) -> pd.DataFrame:
        """
        Generate ML features using optimized queries.
        
        Args:
            feature_type: Type of features ('returns', 'moving_averages', 'volatility', etc.)
            ticker: Stock symbol
            start_date: Start date
            end_date: End date
            **kwargs: Additional parameters for specific feature types
            
        Returns:
            DataFrame with ML features
        """
        async with self.get_connection() as conn:
            if feature_type not in ML_QUERY_TEMPLATES:
                raise ValueError(f"Unknown feature type: {feature_type}")
            
            query = ML_QUERY_TEMPLATES[feature_type]
            params = [ticker, start_date, end_date]
            
            # Handle special cases
            if feature_type == "cross_sectional":
                tickers = kwargs.get('tickers', [ticker])
                placeholders = ','.join(['?' for _ in tickers])
                query = query.format(placeholders)
                params = [start_date, end_date] + tickers
            
            result = conn.execute(query, params).fetchdf()
            logger.debug(f"Generated {feature_type} features: {len(result)} rows")
            return result
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics and performance metrics."""
        async with self.get_connection() as conn:
            stats = {}
            
            try:
                # Daily prices stats
                result = conn.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT ticker) as unique_tickers,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        COUNT(DISTINCT date) as trading_days
                    FROM daily_prices
                """).fetchone()
                
                stats['daily_prices'] = {
                    'total_records': result[0] if result[0] else 0,
                    'unique_tickers': result[1] if result[1] else 0, 
                    'earliest_date': str(result[2]) if result[2] else None,
                    'latest_date': str(result[3]) if result[3] else None,
                    'trading_days': result[4] if result[4] else 0
                }
            except Exception as e:
                logger.warning(f"Could not get daily_prices stats: {e}")
                stats['daily_prices'] = {'total_records': 0, 'unique_tickers': 0}
            
            # File system stats
            parquet_path = Path(self.config.parquet_path)
            if parquet_path.exists():
                total_size = sum(f.stat().st_size for f in parquet_path.rglob('*.parquet'))
                file_count = len(list(parquet_path.rglob('*.parquet')))
                
                stats['storage'] = {
                    'total_size_mb': round(total_size / (1024 * 1024), 2),
                    'parquet_files': file_count,
                    'compression_ratio': 'estimated 80-85%',
                    'storage_format': 'parquet + duckdb'
                }
            else:
                stats['storage'] = {'total_size_mb': 0, 'parquet_files': 0}
            
            return stats
    
    async def export_data(
        self,
        format: str = 'csv',
        ticker: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Export data in various formats.
        
        Args:
            format: Export format ('csv', 'parquet', 'json')
            ticker: Optional ticker filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            output_path: Optional custom output path
            
        Returns:
            Path to exported file
        """
        # Query data
        df = await self.query_price_data(ticker, start_date, end_date)
        
        if df.empty:
            raise ValueError("No data found for export criteria")
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ticker_suffix = f"_{ticker}" if ticker else "_all"
        filename = f"export{ticker_suffix}_{timestamp}.{format}"
        
        if output_path:
            file_path = Path(output_path) / filename
        else:
            file_path = Path(self.config.exports_path) / filename
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export in requested format
        if format == 'csv':
            df.to_csv(file_path, index=False)
        elif format == 'parquet':
            df.to_parquet(file_path, compression='snappy', index=False)
        elif format == 'json':
            df.to_json(file_path, orient='records', date_format='iso')
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Exported {len(df)} records to {file_path}")
        return str(file_path)
    
    async def optimize_storage(self):
        """Optimize storage by compacting small files and updating statistics."""
        async with self.get_connection() as conn:
            try:
                # Update table statistics
                conn.execute("ANALYZE")
                
                # TODO: Implement file compaction logic
                # This would merge small Parquet files into larger ones
                
                logger.info("Storage optimization completed")
                
            except Exception as e:
                logger.error(f"Error during storage optimization: {e}")
                raise
    
    async def backup_to_single_file(self, backup_path: str = None) -> str:
        """
        Create a single-file backup of all data.
        
        Args:
            backup_path: Optional custom backup path
            
        Returns:
            Path to backup file
        """
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.config.exports_path}/backup_{timestamp}.parquet"
        
        async with self.get_connection() as conn:
            # Export all data to single Parquet file
            conn.execute(f"""
                COPY (SELECT * FROM daily_prices ORDER BY ticker, date) 
                TO '{backup_path}' (FORMAT PARQUET, COMPRESSION 'snappy')
            """)
            
            logger.info(f"Created backup at {backup_path}")
            return backup_path
    
    async def close(self):
        """Close the DuckDB connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._initialized = False
            logger.info("DuckDB connection closed")


# Global service instance
_storage_service: Optional[DuckDBStorageService] = None

async def get_storage_service() -> DuckDBStorageService:
    """Get the global DuckDB storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = DuckDBStorageService()
        await _storage_service.initialize()
    return _storage_service 