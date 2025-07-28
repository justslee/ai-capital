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

app = FastAPI(
    title="AI Capital API",
    description="API for fetching and analyzing financial data with summarization and modeling capabilities.",
    version="1.0.0",
    contact={
        "name": "API Support",
        "url": "http://www.example.com/contact",
    },
    openapi_tags=[
        {"name": "Summarization", "description": "Endpoints for summarizing SEC filings."},
        {"name": "Price Prediction", "description": "Endpoints for predicting stock prices."},
    ],
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc"
)

# Create the main API router
api_router = APIRouter(prefix="/api/v1")

# Routers for each domain
api_router.include_router(public_price_prediction_router, prefix="/predict", tags=["Price Prediction"])
api_router.include_router(summarization_router, prefix="/summarizer", tags=["Summarization"])
api_router.include_router(query_router, prefix="/summarizer", tags=["Summarization"])


app.include_router(api_router)


# Example usage for the root endpoint
@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Welcome to the AI Capital API. Visit /api/v1/docs for documentation.",
        "endpoints": {
            "summarization": "GET /api/v1/summarizer/summary/{ticker} - SEC filing summarization",
            "query": "GET /api/v1/summarizer/query/{ticker}?q=... - Q&A on filings",
            "price_prediction": "GET /api/v1/predict/price/{ticker} - Stock price prediction",
        }
    }

# Add CORS middleware
# ... existing code ...
# You can include your API routers here later
# Example: from .api.endpoints import items
# app.include_router(items.router, prefix="/items", tags=["items"]) 