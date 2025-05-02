from fastapi import APIRouter, HTTPException, Path, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure absolute imports from backend.app
from backend.app.services.financials import get_stock_financials
from backend.app.schemas.financials import FinancialsResponse
from backend.app.api.deps import get_db

router = APIRouter()

@router.get(
    "/financials/{ticker}",
    response_model=FinancialsResponse,
    summary="Get and Store Financial Statements for a Stock Ticker",
    tags=["financials"],
    responses={
        200: {"description": "Successfully retrieved and stored financial statements."},
        404: {"description": "Financial statements not found for the given ticker.",
              "content": {"application/json": {"example": {"detail": "Financial statements not found for ticker 'XYZ'."}}}},
        500: {"description": "Internal server error."}
    }
)
async def get_and_store_financials(
    ticker: str = Path(..., title="Stock Ticker Symbol", description="The stock ticker symbol (e.g., AAPL)", min_length=1, max_length=10),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the latest annual Income Statement, Balance Sheet, and Cash Flow statement data
    for a given stock ticker symbol and stores it in the database.
    """
    try:
        print(f"API endpoint received request for ticker: {ticker}")
        financials_data = await get_stock_financials(db=db, symbol=ticker, period='annual', limit=5)

        if financials_data is None:
            print(f"Financial data not found or failed to fetch for ticker: {ticker}. Raising 404.")
            raise HTTPException(
                status_code=404,
                detail=f"Financial statements not found for ticker '{ticker}'. It might be invalid or data unavailable."
            )

        print(f"Successfully fetched and stored financial data for ticker: {ticker}")
        return financials_data

    except HTTPException as http_exc:
        print(f"HTTP Exception in endpoint for {ticker}: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"Unhandled exception in /financials/{ticker} endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while processing financials for '{ticker}'."
        ) 