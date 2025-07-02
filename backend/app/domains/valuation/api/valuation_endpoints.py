"""
Valuation API Endpoints

FastAPI endpoints for company valuation functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db  # Reuse existing dependency

# Shared imports
from ...shared.response_models import ValuationResponse, create_success_response
from ...shared.exceptions import (
    FinancialDataNotFoundException, ValuationCalculationException,
    handle_domain_exception
)

router = APIRouter()

@router.get("/valuation/dcf/{ticker}", response_model=ValuationResponse)
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
        
        valuation_result = await calculate_dcf_valuation(ticker_upper, db)
        
        if not valuation_result:
            raise FinancialDataNotFoundException(ticker_upper, "DCF valuation data")
        
        # Return standardized response
        return ValuationResponse(
            status="success",
            message="DCF valuation calculated successfully",
            data={
                "total_intrinsic_value": valuation_result.total_intrinsic_value,
                "shares_outstanding": valuation_result.shares_outstanding,
                "intrinsic_value_per_share": valuation_result.intrinsic_value_per_share,
                "calculation_details": valuation_result.message
            },
            ticker=ticker_upper,
            valuation_type="DCF"
        )
        
    except FinancialDataNotFoundException:
        raise
    except Exception as e:
        raise ValuationCalculationException(ticker.upper(), "DCF", str(e))

@router.get("/valuation/financials/{ticker}", response_model=ValuationResponse)
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
        
        financials = await get_stock_financials(db, ticker_upper, limit=limit, period=period)
        
        if not financials:
            raise FinancialDataNotFoundException(ticker_upper, "financial statements")
        
        # Return standardized response
        return ValuationResponse(
            status="success",
            message="Financial data retrieved successfully",
            data={
                "income_statements_count": len(financials.income_statements) if financials.income_statements else 0,
                "balance_sheets_count": len(financials.balance_sheets) if financials.balance_sheets else 0,
                "cash_flows_count": len(financials.cash_flows) if financials.cash_flows else 0,
                "financials": {
                    "income_statements": financials.income_statements,
                    "balance_sheets": financials.balance_sheets,
                    "cash_flows": financials.cash_flows
                }
            },
            ticker=ticker_upper,
            period=period
        )
        
    except FinancialDataNotFoundException:
        raise
    except Exception as e:
        raise handle_domain_exception(e) 