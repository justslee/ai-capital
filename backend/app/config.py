from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    fmp_api_key: str
    redis_host: str = "localhost" # Default for local development
    redis_port: int = 6379      # Default for local development
    # redis_password: Optional[str] = None # Add if your Redis requires authentication
    cache_ttl_seconds: int = 3600 # Default cache TTL: 1 hour

    # Database URL (adjust for your RDS/local setup)
    # Example: postgresql+asyncpg://user:password@host:port/dbname
    database_url: str = "postgresql+asyncpg://postgres:D2i2OufzIJmZWGLxchzJ@database-1.cj6qsswemdys.us-east-2.rds.amazonaws.com:5432/company_data" # Using company_data database

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

settings = Settings() 