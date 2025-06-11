"""
Valuation API Endpoints

FastAPI endpoints for company valuation functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db  # Reuse existing dependency

router = APIRouter()

@router.get("/valuation/dcf/{ticker}")
async def get_dcf_valuation(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company (e.g., AAPL)", min_length=1, max_length=10),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate DCF (Discounted Cash Flow) valuation for a company.
    
    This endpoint calculates the intrinsic value of a company using DCF analysis
    based on historical financial data. If data is not available in the database,
    it will be fetched from external sources.
    """
    try:
        from app.domains.valuation.services.valuation import calculate_dcf_valuation
        
        ticker_upper = ticker.upper()
        print(f"Received DCF valuation request for ticker: {ticker_upper}")
        
        valuation_result = await calculate_dcf_valuation(ticker_upper, db)
        
        if not valuation_result:
            raise HTTPException(
                status_code=404,
                detail=f"Could not calculate DCF valuation for {ticker_upper}. Data may not be available."
            )
        
        return {
            "ticker": ticker_upper,
            "valuation_type": "DCF",
            "total_intrinsic_value": valuation_result.total_intrinsic_value,
            "shares_outstanding": valuation_result.shares_outstanding,
            "intrinsic_value_per_share": valuation_result.intrinsic_value_per_share,
            "message": valuation_result.message
        }
        
    except Exception as e:
        print(f"Error calculating DCF valuation for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate DCF valuation: {str(e)}"
        )

@router.get("/valuation/financials/{ticker}")
async def get_financial_data(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company", min_length=1, max_length=10),
    limit: int = 5,
    period: str = "annual",
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch and return financial data for a company.
    """
    try:
        from app.domains.valuation.services.financials import get_stock_financials
        
        ticker_upper = ticker.upper()
        print(f"Received financial data request for ticker: {ticker_upper}")
        
        financials = await get_stock_financials(db, ticker_upper, limit=limit, period=period)
        
        if not financials:
            raise HTTPException(
                status_code=404,
                detail=f"Could not retrieve financial data for {ticker_upper}"
            )
        
        return {
            "ticker": ticker_upper,
            "period": period,
            "limit": limit,
            "income_statements_count": len(financials.income_statements) if financials.income_statements else 0,
            "balance_sheets_count": len(financials.balance_sheets) if financials.balance_sheets else 0,
            "cash_flows_count": len(financials.cash_flows) if financials.cash_flows else 0
        }
        
    except Exception as e:
        print(f"Error fetching financial data for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch financial data: {str(e)}"
        ) 