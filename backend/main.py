import sys
import os
from fastapi import FastAPI
from app.api.deps import get_db
from app.domains.summarization.api.summary_endpoint import router as summary_router
from app.domains.valuation.api.valuation_endpoints import router as valuation_router
from app.domains.modeling.api.modeling_endpoints import router as modeling_router

# Check for required environment variables
if not os.getenv("DATABASE_URL") or not os.getenv("OPENAI_API_KEY"):
    print("CRITICAL: FastAPI application cannot start due to missing DATABASE_URL or OPENAI_API_KEY.", file=sys.stderr)
    print("Please ensure your .env file is correctly set up at the project root and contains these variables.", file=sys.stderr)
    sys.exit(1)

app = FastAPI(
    title="AI Capital API",
    description="AI-powered capital markets analysis platform",
    version="1.0.0"
)

# Include routers
app.include_router(summary_router, prefix="/api/v1/summarization", tags=["summarization"])
app.include_router(valuation_router, prefix="/api/v1/valuation", tags=["valuation"]) 
app.include_router(modeling_router, prefix="/api/v1/modeling", tags=["modeling"])

# Commented out router - needs investigation:
# app.include_router(duckdb_router, prefix="/api/v1/duckdb", tags=["duckdb"])

@app.get("/")
async def root():
    return {"message": "AI Capital API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Application ready - silent startup

# To run this application (from the project root directory, e.g., /Users/justinlee/ai_capital):
# poetry run uvicorn app.main:app --reload  (if using Poetry)
# or
# python -m uvicorn app.main:app --reload (if uvicorn is in your Python path)
# 
# The API will then be available at http://127.0.0.1:8000
# The summary endpoint will be at http://127.0.0.1:8000/api/v1/summary/{ticker}/{year}/{form_type} 