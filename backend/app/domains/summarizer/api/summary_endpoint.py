# Standard library imports
import sys
from typing import Optional

# Third-party imports
from fastapi import APIRouter, HTTPException, Path, Query

# Domain imports (relative)
from ..services.summarization_service import get_summarization_service

# Shared imports
from ...shared.response_models import SummarizationResponse
from ...shared.exceptions import (
    handle_domain_exception
)

router = APIRouter()

@router.get("/summary/{ticker}", response_model=SummarizationResponse)
async def get_filing_summary(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company (e.g., AAPL)", min_length=1, max_length=10),
    year: Optional[int] = Query(None, title="Filing Year", description="Optional: The four-digit year of the filing (e.g., 2023)"),
    form_type: Optional[str] = Query(None, title="Form Type", description="Optional: The SEC form type (e.g., 10-K, 10-Q).", pattern="^(10-K|10-Q)$")
):
    """
    Provides a top-level summary for a specified company filing.

    If year and form_type are provided, it fetches that specific filing.
    Otherwise, it fetches the latest available filing for the ticker.
    """
    try:
        summarization_service = get_summarization_service()
        summary_url = await summarization_service.get_summary(ticker=ticker.upper(), year=year, form_type=form_type)

        # This response will be updated later to be more sophisticated.
        # For now, it returns the placeholder URL from the service.
        return SummarizationResponse(
            status="success",
            message="Summary processing pipeline initiated.",
            data={"summary_url": summary_url},
            ticker=ticker.upper(),
            year=year or 0, # Placeholder
            form_type=form_type or "Unknown", # Placeholder
            accession_number="000-00-000000" # Placeholder
        )
        
    except Exception as e:
        return handle_domain_exception(e) 