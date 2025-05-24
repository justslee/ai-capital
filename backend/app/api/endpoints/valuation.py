import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api import deps
from backend.app.schemas.valuation import ValuationResponse
from backend.app.services.valuation import calculate_dcf_valuation

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{ticker}", response_model=ValuationResponse)
async def get_valuation(
    ticker: str,
    db: AsyncSession = Depends(deps.get_db),
) -> ValuationResponse:
    """
    Retrieve the DCF valuation for a given stock ticker.
    
    If financial data is not present in the database, it will be fetched
    from the FMP API first.
    """
    logger.info(f"Received request for valuation of {ticker}")
    try:
        valuation_result = await calculate_dcf_valuation(ticker=ticker, db=db)
        # Check if the per-share value is None and there's a message (indicates calculation issue)
        if valuation_result.intrinsic_value_per_share is None and valuation_result.message:
             # Handle cases where valuation couldn't be performed (e.g., no data, no shares)
             # Log the specific message from the service
             logger.warning(f"Valuation incomplete for {ticker}: {valuation_result.message}")
             # Return a 404 or 422 depending on the reason.
             if "not found" in valuation_result.message.lower():
                  raise HTTPException(status_code=404, detail=valuation_result.message)
             else:
                  # For other calculation issues (e.g., no positive FCF, WACC<=g, no shares)
                  raise HTTPException(status_code=422, detail=valuation_result.message)

        logger.info(f"Successfully calculated valuation for {ticker}")
        return valuation_result
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions raised within the endpoint or service call check
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error calculating valuation for {ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error calculating valuation for {ticker}.") 