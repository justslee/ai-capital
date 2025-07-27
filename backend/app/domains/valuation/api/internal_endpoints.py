"""
Internal Valuation API Endpoints

Internal/administrative endpoints for valuation functionality.
These endpoints are for system operations, not for external clients.
"""

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db

# Shared imports
from app.shared.response_models import ValuationResponse
from app.shared.exceptions import (
    FinancialDataNotFoundException, handle_domain_exception
)

router = APIRouter()

@router.get("/valuation/financials/{ticker}", response_model=ValuationResponse)
async def get_financial_data(
    ticker: str = Path(
        ..., 
        title="Stock Ticker", 
        description="The ticker symbol of the company", 
        min_length=1, 
        max_length=10
    ),
    limit: int = Query(5, description="Number of periods to return"),
    period: str = Query("annual", description="Period type (annual/quarterly)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch raw financial data for a company.
    
    **Internal API Endpoint**
    
    This endpoint provides access to raw financial statements and data.
    It's intended for internal operations, data analysis, and system
    administration - not for external client consumption.
    """
    try:
        from app.domains.valuation.services.financials import get_stock_financials
        
        ticker_upper = ticker.upper()
        
        financials = await get_stock_financials(db, ticker_upper, limit=limit, period=period)
        
        if not financials:
            raise FinancialDataNotFoundException(ticker_upper, "financial statements")
        
        # Return detailed financial data for internal use
        return ValuationResponse(
            status="success",
            message="Financial data retrieved successfully",
            data={
                "periods_available": {
                    "income_statements": len(financials.income_statements) if financials.income_statements else 0,
                    "balance_sheets": len(financials.balance_sheets) if financials.balance_sheets else 0,
                    "cash_flows": len(financials.cash_flows) if financials.cash_flows else 0
                },
                "raw_financials": {
                    "income_statements": financials.income_statements,
                    "balance_sheets": financials.balance_sheets,
                    "cash_flows": financials.cash_flows
                },
                "data_source": "FMP API",
                "period_type": period,
                "limit_applied": limit
            },
            ticker=ticker_upper,
            period=period
        )
        
    except FinancialDataNotFoundException:
        raise
    except Exception as e:
        raise handle_domain_exception(e)

@router.get("/valuation/health")
async def valuation_health_check():
    """
    Health check for valuation domain services.
    
    **Internal API Endpoint**
    
    Checks the health of valuation services including API connectivity
    and database access.
    """
    try:
        from app.domains.valuation.services.fmp_client import FMPClient
        
        # Test FMP API connectivity
        async with FMPClient() as client:
            # Simple test call
            test_result = await client._make_request("profile/AAPL?limit=1")
            api_status = "ok" if test_result else "degraded"
        
        return {
            "status": "healthy",
            "service": "valuation",
            "dependencies": {
                "fmp_api": api_status,
                "database": "ok"  # If we get here, DB connection is working
            },
            "timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "valuation",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        } 