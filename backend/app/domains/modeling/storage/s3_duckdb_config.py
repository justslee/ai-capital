"""
S3-backed DuckDB Configuration

Store Parquet files in AWS S3 and query them directly with DuckDB.
Zero local storage footprint for work devices.
"""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


class S3DuckDBConfig(BaseSettings):
    """Configuration for S3-backed DuckDB storage."""
    
    # AWS S3 Configuration
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    s3_bucket: str = Field(default="ai-capital-data", env="S3_BUCKET")
    s3_prefix: str = Field(default="market-data", env="S3_PREFIX")
    
    # DuckDB Configuration
    duckdb_memory_limit: str = "1GB"
    duckdb_threads: int = 4
    
    # Parquet Configuration
    parquet_compression: str = "snappy"
    parquet_row_group_size: int = 50000
    
    # Local cache (minimal)
    local_cache_dir: str = "./cache"
    max_cache_size_mb: int = 100  # Very small cache
    
    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_s3_path(self, table_name: str, partition: dict = None) -> str:
        """Get S3 path for a table/partition."""
        path = f"s3://{self.s3_bucket}/{self.s3_prefix}/{table_name}"
        
        if partition:
            for key, value in partition.items():
                path += f"/{key}={value}"
        
        return path
    
    def get_s3_client(self):
        """Get configured S3 client."""
        return boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
    
    def test_s3_connection(self) -> bool:
        """Test S3 connection and bucket access."""
        try:
            s3_client = self.get_s3_client()
            s3_client.head_bucket(Bucket=self.s3_bucket)
            return True
        except (NoCredentialsError, ClientError) as e:
            print(f"S3 connection failed: {e}")
            return False
    
    def create_bucket_if_not_exists(self) -> bool:
        """Create S3 bucket if it doesn't exist."""
        try:
            s3_client = self.get_s3_client()
            
            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=self.s3_bucket)
                print(f"✅ S3 bucket '{self.s3_bucket}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # Bucket doesn't exist, create it
                    if self.aws_region == 'us-east-1':
                        s3_client.create_bucket(Bucket=self.s3_bucket)
                    else:
                        s3_client.create_bucket(
                            Bucket=self.s3_bucket,
                            CreateBucketConfiguration={'LocationConstraint': self.aws_region}
                        )
                    print(f"✅ Created S3 bucket '{self.s3_bucket}'")
                    return True
                else:
                    raise
        except Exception as e:
            print(f"❌ Failed to create S3 bucket: {e}")
            return False


# Global configuration instance
_s3_config = None

def get_s3_config() -> S3DuckDBConfig:
    """Get the global S3 DuckDB configuration."""
    global _s3_config
    if _s3_config is None:
        _s3_config = S3DuckDBConfig()
    return _s3_config


# DuckDB S3 setup queries
DUCKDB_S3_SETUP = """
-- Install and load S3 extension
INSTALL httpfs;
LOAD httpfs;

-- Configure S3 credentials
SET s3_region='{region}';
SET s3_access_key_id='{access_key}';
SET s3_secret_access_key='{secret_key}';
"""

# Create views for S3-stored data
S3_VIEW_TEMPLATES = {
    "daily_prices": """
    CREATE OR REPLACE VIEW daily_prices AS 
    SELECT * FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
    """,
    
    "tickers": """
    CREATE OR REPLACE VIEW tickers AS 
    SELECT * FROM read_parquet('{s3_path}/tickers/**/*.parquet')
    """
}

# ML query templates for S3 data
S3_ML_QUERIES = {
    "returns": """
    SELECT 
        ticker,
        date,
        close,
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close,
        (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / 
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) as daily_return,
        (close - LAG(close, 5) OVER (PARTITION BY ticker ORDER BY date)) / 
        LAG(close, 5) OVER (PARTITION BY ticker ORDER BY date) as weekly_return,
        (close - LAG(close, 21) OVER (PARTITION BY ticker ORDER BY date)) / 
        LAG(close, 21) OVER (PARTITION BY ticker ORDER BY date) as monthly_return
    FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
    WHERE ticker = ? AND date BETWEEN ? AND ?
    ORDER BY date DESC
    """,
    
    "moving_averages": """
    SELECT 
        ticker,
        date,
        close,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as ma_5,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) as ma_10,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma_20,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) as ma_50,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) as ma_200
    FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
    WHERE ticker = ? AND date BETWEEN ? AND ?
    ORDER BY date DESC
    """,
    
    "volatility": """
    WITH returns AS (
        SELECT 
            ticker,
            date,
            close,
            (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / 
            LAG(close) OVER (PARTITION BY ticker ORDER BY date) as daily_return
        FROM read_parquet('{s3_path}/daily_prices/**/*.parquet')
        WHERE ticker = ? AND date BETWEEN ? AND ?
    )
    SELECT 
        ticker,
        date,
        close,
        daily_return,
        STDDEV(daily_return) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as volatility_20d,
        STDDEV(daily_return) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW) as volatility_60d
    FROM returns
    ORDER BY date DESC
    """
} 