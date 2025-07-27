"""
Public Modeling API Endpoints

Client-facing endpoints for price prediction and modeling functionality.
Only includes endpoints that external clients should access.
"""

from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.shared.response_models import APIResponse
from app.shared.exceptions import handle_domain_exception
from ..price_prediction_service import PricePredictionService

router = APIRouter()

@router.post("/predict/{ticker}")
async def predict_stock_price(
    ticker: str = Path(
        ..., 
        title="Stock Ticker", 
        description="The ticker symbol of the company (e.g., AAPL)", 
        min_length=1, 
        max_length=10
    ),
    days_ahead: int = Query(
        30, 
        description="Number of days to predict ahead", 
        ge=1, 
        le=90
    ),
    model_type: str = Query(
        "lstm", 
        description="Prediction model type",
        regex="^(lstm|linear_regression|ensemble)$"
    ),
    db: Session = Depends(deps.get_db)
):
    """
    Predict future stock price for a given ticker.
    
    **Public API Endpoint**
    
    This endpoint provides AI-powered stock price predictions using advanced
    machine learning models. Predictions include confidence intervals and
    risk assessments.
    
    **Currently Not Implemented** - Returns implementation status.
    
    When fully implemented, this will return:
        - Predicted price for target date
        - Confidence intervals
        - Risk assessment
        - Model performance metrics
        - Feature importance insights
    """
    try:
        price_prediction_service = PricePredictionService()
        
        # This will raise PricePredictionNotImplementedException
        result = await price_prediction_service.predict_price(
            ticker=ticker.upper(),
            days_ahead=days_ahead,
            model_type=model_type,
            db=db
        )
        
        return result
        
    except Exception as e:
        # Handle the not implemented exception gracefully for public API
        if "not yet implemented" in str(e):
            return APIResponse(
                status="pending",
                message="Price prediction functionality is currently under development",
                data={
                    "ticker": ticker.upper(),
                    "requested_prediction_date": (datetime.now() + timedelta(days=days_ahead)).isoformat(),
                    "model_type": model_type,
                    "implementation_status": "In Development",
                    "expected_completion": "Q2 2024",
                    "available_alternatives": [
                        "DCF valuation analysis via /api/v1/valuation/dcf/{ticker}",
                        "SEC filing summaries via /api/v1/summary/{ticker}/{year}/10-K"
                    ]
                }
            )
        else:
            raise handle_domain_exception(e) 