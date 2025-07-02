"""
Modeling Services

Core services for price prediction modeling including:
- Price prediction service
- Model training and evaluation
- Feature engineering
- Data ingestion and management
"""

from .price_prediction_service import price_prediction_service, PricePredictionService
from .tiingo_client import TiingoClient, get_tiingo_client
from .duckdb_ingestion_service import DuckDBIngestionService, get_ingestion_service
from .s3_duckdb_ingestion_service import S3DuckDBIngestionService, get_s3_ingestion_service

__all__ = [
    # Price prediction
    "PricePredictionService",
    "price_prediction_service",
    
    # Data clients
    "TiingoClient", 
    "get_tiingo_client",
    
    # Data ingestion
    "DuckDBIngestionService",
    "get_ingestion_service",
    "S3DuckDBIngestionService", 
    "get_s3_ingestion_service",
] 