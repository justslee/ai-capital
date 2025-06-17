from fastapi import FastAPI

# Import domain-based routers with relative imports
from app.domains.summarization.api.summary_endpoint import router as summarization_router
from app.domains.valuation.api.valuation_endpoints import router as valuation_router
# from app.domains.modeling.api.modeling_endpoints import router as modeling_router  # Temporarily disabled due to import issues
from app.domains.modeling.api.duckdb_endpoints import router as duckdb_router
from app.domains.modeling.endpoints.s3_duckdb_endpoints import router as s3_duckdb_router

app = FastAPI(
    title="AI Capital API",
    description="API for fetching and analyzing financial data with summarization, valuation, and modeling capabilities.",
    version="0.1.0"
)

# Include domain routers
app.include_router(summarization_router, prefix="/api/v1", tags=["summarization"])
app.include_router(valuation_router, prefix="/api/v1", tags=["valuation"])
# app.include_router(modeling_router, prefix="/api/v1", tags=["modeling"])  # Temporarily disabled
app.include_router(duckdb_router, prefix="/api/v1", tags=["duckdb-storage"])
app.include_router(s3_duckdb_router, prefix="/api/v1", tags=["s3-duckdb-storage"])

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to AI Capital API",
        "domains": {
            "summarization": "Financial statement and SEC filing summarization",
            "valuation": "Company valuation calculations (DCF, financial data)",
            "modeling": "Price prediction and modeling functionality",
            "duckdb_storage": "High-performance DuckDB + Parquet data storage (10-100x faster than PostgreSQL)",
            "s3_duckdb_storage": "S3-backed DuckDB storage (zero local storage footprint for work devices)"
        },
        "version": "0.1.0",
        "storage_systems": {
            "postgresql": "Traditional relational database (existing)",
            "duckdb_parquet": "High-performance columnar storage (local files)",
            "s3_duckdb": "S3-backed DuckDB storage (zero local footprint - perfect for work devices)"
        }
    }

# You can include your API routers here later
# Example: from .api.endpoints import items
# app.include_router(items.router, prefix="/items", tags=["items"]) 