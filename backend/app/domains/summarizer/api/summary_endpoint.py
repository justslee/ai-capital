# Standard library imports
import sys
from typing import Optional

# Third-party imports
from fastapi import APIRouter, HTTPException, Path, Query

# Domain imports (relative)
from ..services import get_summarization_service

# Shared imports
from app.shared.response_models import SummarizationResponse
from app.shared.exceptions import handle_domain_exception

router = APIRouter()

@router.get("/summary/{ticker}", response_model=SummarizationResponse)
async def get_filing_summary(
    ticker: str = Path(..., description="The stock ticker symbol (e.g., AAPL)", min_length=1, max_length=10),
    year: Optional[int] = Query(None, description="The year of the filing"),
    form_type: Optional[str] = Query(None, description="The form type of the filing (e.g., 10-K)")
):
    """
    Provides a top-level summary for a specified company filing.

    If year and form_type are provided, it fetches that specific filing.
    Otherwise, it fetches the latest available filing for the ticker.
    """
    try:
        summarization_service = get_summarization_service()
        summary_url = await summarization_service.get_summary(ticker=ticker.upper(), year=year, form_type=form_type)
        return SummarizationResponse(
            status="success",
            message="Summary processing pipeline initiated.",
            data={"summary_url": summary_url},
            ticker=ticker.upper(),
            year=year or 0, # Default to 0 if not provided
            form_type=form_type or "Unknown", # Default to "Unknown"
            accession_number="000-00-000000" # Placeholder, will be updated
        )
    except Exception as e:
        raise handle_domain_exception(e) 