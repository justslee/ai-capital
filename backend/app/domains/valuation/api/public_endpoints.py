"""
Public Valuation API Endpoints

Client-facing endpoints for company valuation functionality.
Only includes endpoints that external clients should access.
"""

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api import deps
from app.shared.response_models import ValuationResponse
from app.shared.exceptions import (
    FinancialDataNotFoundException, ValuationCalculationException
)
from ..services.valuation import get_valuation_service, ValuationService

router = APIRouter()


@router.get("/{ticker}", response_model=ValuationResponse)
async def get_dcf_valuation(
    ticker: str = Path(
        ...,
        description="The stock ticker symbol (e.g., AAPL)",
        min_length=1,
        max_length=10
    ),
    valuation_service: ValuationService = Depends(get_valuation_service)
):
    """
    Performs a Discounted Cash Flow (DCF) valuation for a given stock ticker.
    """
    try:
        ticker_upper = ticker.upper()
        
        valuation_result = await valuation_service.calculate_dcf(ticker_upper)
        
        if not valuation_result:
            raise FinancialDataNotFoundException(f"Could not calculate DCF for {ticker_upper}. Financial data may be missing or insufficient.")
        
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