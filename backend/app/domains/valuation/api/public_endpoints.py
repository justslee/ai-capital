"""
Public Valuation API Endpoints

Client-facing endpoints for company valuation functionality.
Only includes endpoints that external clients should access.
"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db

# Shared imports
from ...shared.response_models import ValuationResponse
from ...shared.exceptions import (
    FinancialDataNotFoundException, ValuationCalculationException
)

router = APIRouter()

@router.get("/valuation/dcf/{ticker}", response_model=ValuationResponse)
async def get_dcf_valuation(
    ticker: str = Path(
        ..., 
        title="Stock Ticker", 
        description="The ticker symbol of the company (e.g., AAPL)", 
        min_length=1, 
        max_length=10
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate DCF (Discounted Cash Flow) valuation for a company.
    
    **Public API Endpoint**
    
    This endpoint calculates the intrinsic value of a company using DCF analysis
    based on historical financial data. This is the main valuation endpoint
    for external clients.
    
    Returns:
        - Intrinsic value per share
        - Total intrinsic value
        - Shares outstanding
        - Calculation methodology summary
    """
    try:
        from app.domains.valuation.services.valuation import calculate_dcf_valuation
        
        ticker_upper = ticker.upper()
        
        valuation_result = await calculate_dcf_valuation(ticker_upper, db)
        
        if not valuation_result:
            raise FinancialDataNotFoundException(ticker_upper, "DCF valuation data")
        
        # Return standardized response for public API
        return ValuationResponse(
            status="success",
            message="DCF valuation calculated successfully",
            data={
                "intrinsic_value_per_share": valuation_result.intrinsic_value_per_share,
                "total_intrinsic_value": valuation_result.total_intrinsic_value,
                "shares_outstanding": valuation_result.shares_outstanding,
                "valuation_methodology": "Discounted Cash Flow (DCF)",
                "calculation_summary": valuation_result.message
            },
            ticker=ticker_upper,
            valuation_type="DCF"
        )
        
    except FinancialDataNotFoundException:
        raise
    except Exception as e:
        raise ValuationCalculationException(ticker.upper(), "DCF", str(e)) 