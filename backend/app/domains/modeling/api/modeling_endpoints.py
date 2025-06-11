"""
Modeling API Endpoints

FastAPI endpoints for price prediction modeling functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db  # Reuse existing dependency

router = APIRouter()

@router.get("/modeling/predict/{ticker}")
async def predict_price(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company (e.g., AAPL)", min_length=1, max_length=10),
    days_ahead: int = 30,
    model_type: str = "linear_regression",
    db: AsyncSession = Depends(get_db)
):
    """
    Predict stock price for a given ticker and time horizon.
    
    This endpoint will generate price predictions using various models
    based on historical data and technical indicators.
    """
    try:
        from app.domains.modeling.services.price_prediction_service import price_prediction_service
        
        ticker_upper = ticker.upper()
        print(f"Received price prediction request for ticker: {ticker_upper}")
        
        prediction_result = await price_prediction_service.predict_price(
            ticker=ticker_upper,
            days_ahead=days_ahead,
            model_type=model_type,
            db=db
        )
        
        return prediction_result
        
    except Exception as e:
        print(f"Error predicting price for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to predict price: {str(e)}"
        )

@router.post("/modeling/ingest/{ticker}")
async def ingest_price_data(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company", min_length=1, max_length=10),
    days_back: int = 365,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest historical price data for modeling purposes.
    """
    try:
        from app.domains.modeling.data_ingestion.price_data_ingestion import price_data_ingestion_service
        from datetime import datetime, timedelta
        
        ticker_upper = ticker.upper()
        print(f"Received data ingestion request for ticker: {ticker_upper}")
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        ingestion_result = await price_data_ingestion_service.ingest_historical_prices(
            ticker=ticker_upper,
            start_date=start_date,
            db=db
        )
        
        return ingestion_result
        
    except Exception as e:
        print(f"Error ingesting data for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest data: {str(e)}"
        ) 