from fastapi import FastAPI

# Using absolute import starting from backend
from backend.app.api.endpoints import financials, valuation

app = FastAPI(
    title="AI Capital API",
    description="API for fetching and analyzing financial data.",
    version="0.1.0"
)

# Include routers
app.include_router(financials.router, prefix="/api/v1/financials", tags=["financials"])
app.include_router(valuation.router, prefix="/api/v1/valuation", tags=["valuation"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to AI Capital API"}

# You can include your API routers here later
# Example: from .api.endpoints import items
# app.include_router(items.router, prefix="/items", tags=["items"]) 