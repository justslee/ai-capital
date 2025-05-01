from fastapi import FastAPI

app = FastAPI(title="AI Capital API")

@app.get("/")
async def root():
    return {"message": "Welcome to AI Capital API"}

# You can include your API routers here later
# Example: from .api.endpoints import items
# app.include_router(items.router, prefix="/items", tags=["items"]) 