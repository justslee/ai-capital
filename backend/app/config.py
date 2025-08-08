from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    fmp_api_key: Optional[str] = None
    redis_host: str = "localhost" 
    redis_port: int = 6379     
    cache_ttl_seconds: int = 3600
 
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    openai_api_key: str
    
    # Database Configuration
    database_url: Optional[str] = None
    db_echo: bool = False
    
    # AWS Credentials
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = 'us-east-1'
    
    # S3 Storage
    s3_bucket: Optional[str] = None
    s3_prefix: Optional[str] = None

    # External API Keys
    fred_api_key: Optional[str] = None
    tiingo_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None

    # Storage Configuration
    storage_type: Optional[str] = None

    class Config:
        # Use absolute path to root .env file
        project_root = Path(__file__).resolve().parents[2]  # Go up to ai-capital/
        env_file = str(project_root / '.env')
        env_file_encoding = 'utf-8'

def get_settings() -> Settings:
    """Get fresh settings instance - no caching to avoid stale API keys."""
    return Settings()

# Keep backward compatibility with existing imports
settings = get_settings() 