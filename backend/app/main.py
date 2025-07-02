from fastapi import FastAPI

# Import public API routers (client-facing)
from app.domains.summarization.api.summary_endpoint import router as summarization_router
from app.domains.valuation.api.public_endpoints import router as public_valuation_router
from app.domains.modeling.api.public_endpoints import router as public_modeling_router

# Import internal API routers (admin/operations)
from app.domains.valuation.api.internal_endpoints import router as internal_valuation_router
from app.domains.modeling.api.modeling_endpoints import router as modeling_router
from app.domains.modeling.api.duckdb_endpoints import router as duckdb_router

app = FastAPI(
    title="AI Capital API",
    description="API for fetching and analyzing financial data with summarization, valuation, and modeling capabilities.",
    version="0.1.0"
)

# Include public API routers (client-facing)
app.include_router(summarization_router, prefix="/api/v1", tags=["public-api", "summarization"])
app.include_router(public_valuation_router, prefix="/api/v1", tags=["public-api", "valuation"])
app.include_router(public_modeling_router, prefix="/api/v1", tags=["public-api", "prediction"])

# Include internal API routers (admin/operations only)
app.include_router(internal_valuation_router, prefix="/internal", tags=["internal-api", "valuation"])
app.include_router(modeling_router, prefix="/internal", tags=["internal-api", "modeling"])
app.include_router(duckdb_router, prefix="/internal", tags=["internal-api", "storage"])

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to AI Capital API",
        "version": "0.1.0",
        "api_structure": {
            "public_api": {
                "description": "Client-facing endpoints for core business functionality",
                "base_url": "/api/v1",
                "endpoints": {
                    "filing_summary": "GET /api/v1/summary/{ticker}/{year}/{form_type} - SEC filing analysis",
                    "dcf_valuation": "GET /api/v1/valuation/dcf/{ticker} - Company valuation",
                    "price_prediction": "POST /api/v1/predict/{ticker} - AI price forecasting (coming soon)"
                }
            },
            "internal_api": {
                "description": "Administrative and operational endpoints for system management",
                "base_url": "/internal",
                "access": "Internal use only - not for external clients",
                "categories": [
                    "Data ingestion and management",
                    "Storage operations",
                    "Health monitoring",
                    "Raw financial data access"
                ]
            }
        },
        "domains": {
            "summarization": "SEC filing summarization and analysis",
            "valuation": "Company valuation using DCF methodology", 
            "prediction": "AI-powered stock price forecasting"
        },
        "documentation": {
            "public_api": "/docs - Swagger UI for public endpoints",
            "full_api": "/docs - Complete API documentation (includes internal endpoints)"
        }
    }

# You can include your API routers here later
# Example: from .api.endpoints import items
# app.include_router(items.router, prefix="/items", tags=["items"]) 