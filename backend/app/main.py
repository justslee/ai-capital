import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi import APIRouter
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).resolve().parents[2]  # Go up to ai-capital/
env_path = project_root / '.env'
if env_path.exists():
    # Force override existing environment variables
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"Loaded .env from {env_path} with override=True")
else:
    print(f"Warning: .env file not found at {env_path}")

# Configure logging to show INFO level logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to INFO level
logging.getLogger("app.domains.data_collection.tiingo_client").setLevel(logging.INFO)

# Import API routers from each domain
from .domains.summarizer.api.summary_endpoint import router as summarization_router
from .domains.summarizer.api.query_endpoint import router as query_router
from .domains.price_prediction.api.public_endpoints import router as public_price_prediction_router
from .domains.valuation.api.public_endpoints import router as public_valuation_router
from .domains.valuation.api.internal_endpoints import router as internal_valuation_router

app = FastAPI(
    title="AI Capital API",
    description="API for fetching and analyzing financial data with summarization, valuation, and modeling capabilities.",
    version="0.1.0"
)

# Create a main API router to group all versioned endpoints
api_router = APIRouter()

# Routers for each domain
api_router.include_router(public_valuation_router, prefix="/valuation", tags=["Valuation"])
api_router.include_router(public_price_prediction_router, prefix="/predict", tags=["Price Prediction"])
api_router.include_router(summarization_router, prefix="/summarizer", tags=["Summarization"])
api_router.include_router(query_router, prefix="/summarizer", tags=["Summarization"])
api_router.include_router(internal_valuation_router, prefix="/internal/valuation", tags=["Valuation (Internal)"])


app.include_router(api_router, prefix="/api/v1")


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