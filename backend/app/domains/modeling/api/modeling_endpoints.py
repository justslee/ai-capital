"""
Main Modeling Domain API Endpoints

Consolidates all API endpoints for the modeling domain.
"""

from fastapi import APIRouter
from .data_ingestion_endpoints import router as data_ingestion_router

# Create main modeling router
router = APIRouter()

# Include all sub-routers
router.include_router(data_ingestion_router, tags=["modeling", "data-ingestion"])

# Add any additional modeling endpoints here in the future
# router.include_router(prediction_router, tags=["modeling", "prediction"])
# router.include_router(analysis_router, tags=["modeling", "analysis"]) 