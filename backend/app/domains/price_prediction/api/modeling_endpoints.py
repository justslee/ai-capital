"""
Main Modeling Domain API Endpoints

Consolidates all API endpoints for the modeling domain.
"""

from fastapi import APIRouter
from .s3_duckdb_endpoints import router as s3_duckdb_router
from .s3_fmp_fundamentals_endpoints import router as s3_fmp_fundamentals_router
from .tiingo_financial_statements_endpoints import router as tiingo_statements_router

# Create main modeling router
router = APIRouter(prefix="/modeling")

# Include essential S3-based sub-routers
router.include_router(s3_duckdb_router, tags=["modeling", "s3-duckdb"])
router.include_router(s3_fmp_fundamentals_router, tags=["modeling", "fmp-fundamentals"])
router.include_router(tiingo_statements_router, tags=["modeling", "tiingo-statements"])

# Future endpoints can be added here
# router.include_router(prediction_router, tags=["modeling", "prediction"])
# router.include_router(analysis_router, tags=["modeling", "analysis"]) 