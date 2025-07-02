"""
Main Modeling Domain API Endpoints

Consolidates all API endpoints for the modeling domain.
"""

from fastapi import APIRouter
from .data_ingestion_endpoints import router as data_ingestion_router
from .s3_duckdb_endpoints import router as s3_duckdb_router

# Create main modeling router
router = APIRouter(prefix="/modeling")

# Include all sub-routers
router.include_router(data_ingestion_router, tags=["modeling", "data-ingestion"])
router.include_router(s3_duckdb_router, tags=["modeling", "s3-duckdb"])

# Add any additional modeling endpoints here in the future
# router.include_router(prediction_router, tags=["modeling", "prediction"])
# router.include_router(analysis_router, tags=["modeling", "analysis"]) 