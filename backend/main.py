from fastapi import FastAPI
from app.api.endpoints import summary_endpoint # Corrected import path assuming summary_endpoint.py is in app/api/endpoints
from app.core.config import DATABASE_URL, OPENAI_API_KEY # To trigger early config load and checks
import sys

# Perform a basic check that essential configs are loaded.
# app.core.config already prints errors if these are missing.
if not DATABASE_URL or not OPENAI_API_KEY:
    print("CRITICAL: FastAPI application cannot start due to missing DATABASE_URL or OPENAI_API_KEY.", file=sys.stderr)
    print("Please ensure your .env file is correctly set up at the project root and contains these variables.", file=sys.stderr)
    # sys.exit(1) # In a deployed app, this might cause the process to fail to start, which is often desired.

app = FastAPI(
    title="SEC Filing Summarization API",
    description="API to retrieve and generate summaries of SEC filings, including detailed top-level summaries for financial analysis.",
    version="0.1.0"
)

# Include the summary router
app.include_router(summary_endpoint.router, prefix="/api/v1", tags=["Summaries"])

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    # In a real app, you might check DB connectivity or other critical service statuses here.
    return {"status": "ok", "message": "API is running"}

# To run this application (from the project root directory, e.g., /Users/justinlee/ai_capital):
# poetry run uvicorn app.main:app --reload  (if using Poetry)
# or
# python -m uvicorn app.main:app --reload (if uvicorn is in your Python path)
# 
# The API will then be available at http://127.0.0.1:8000
# The summary endpoint will be at http://127.0.0.1:8000/api/v1/summary/{ticker}/{year}/{form_type}

print("FastAPI app initialized. Routers included. Ready to run with Uvicorn.") 