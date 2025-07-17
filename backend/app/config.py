from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    fmp_api_key: Optional[str] = None
    redis_host: str = "localhost" 
    redis_port: int = 6379     
    # redis_password: Optional[str] = None # Add if your Redis requires authentication
    cache_ttl_seconds: int = 3600 # Default cache TTL: 1 hour
    database_url: str = "postgresql+asyncpg://postgres:D2i2OufzIJmZWGLxchzJ@database-1.cj6qsswemdys.us-east-2.rds.amazonaws.com:5432/company_data" 
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    openai_api_key: str
    
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
        env_file = '.env'
        env_file_encoding = 'utf-8'

settings = Settings() 