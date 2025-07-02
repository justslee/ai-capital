# Standard library imports
import sys

# Third-party imports
import psycopg2
from fastapi import APIRouter, HTTPException, Path

# App imports
from app.db.database_utils import db_cursor

# Domain imports (relative)
from ..services.summary_generation import generate_and_store_top_level_summary

# Shared imports
from ...shared.response_models import SummarizationResponse, create_success_response
from ...shared.exceptions import (
    FilingNotFoundException, SummaryGenerationException, 
    PrerequisiteDataMissingException, handle_domain_exception
)

router = APIRouter()

@router.get("/summary/{ticker}/{year}/{form_type}", response_model=SummarizationResponse)
async def get_filing_summary(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company (e.g., AAPL)", min_length=1, max_length=10),
    year: int = Path(..., title="Filing Year", description="The four-digit year of the filing (e.g., 2023)"),
    form_type: str = Path(..., title="Form Type", description="The SEC form type (e.g., 10-K, 10-Q). Currently optimized for 10-K.", pattern="^(10-K|10-Q)$")
):
    """
    Provides a top-level summary for a specified company filing.
    
    The summary is generated based on pre-existing section summaries (Business, MD&A, Risk Factors).
    If a top-level summary for the latest filing matching the criteria is already cached, it's returned.
    Otherwise, it's generated on-the-fly using GPT-4, stored, and then returned.
    """
    requested_form_type_upper = form_type.upper()
    
    if requested_form_type_upper != "10-K":
        raise HTTPException(
            status_code=400,
            detail=f"Currently, only '10-K' form types are fully supported for top-level summaries. Requested: {requested_form_type_upper}"
        )

    accession_number = None
    try:
        with db_cursor() as cursor:
            cursor.execute(
                """SELECT accession_number 
                   FROM sec_filings
                   WHERE ticker = %s 
                     AND filing_type = %s 
                     AND EXTRACT(YEAR FROM filing_date) = %s
                   ORDER BY filing_date DESC
                   LIMIT 1""", 
                (ticker.upper(), requested_form_type_upper, year)
            )
            result = cursor.fetchone()
            if result:
                accession_number = result[0]
            else:
                raise FilingNotFoundException(ticker.upper(), year, requested_form_type_upper)
                
    except psycopg2.Error as db_err:
        raise HTTPException(status_code=500, detail="Database error while retrieving filing information.")
    except FilingNotFoundException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    if not accession_number:
        raise FilingNotFoundException(ticker.upper(), year, requested_form_type_upper)

    try:
        summary_text = await generate_summary_async_wrapper(accession_number)
        
        # Return standardized response
        return SummarizationResponse(
            status="success",
            message="Summary generated successfully",
            data={
                "summary": summary_text
            },
            ticker=ticker.upper(),
            year=year,
            form_type=form_type,
            accession_number=accession_number
        )
        
    except ValueError as ve: # Raised by generate_and_store_top_level_summary if prerequisites missing
        # Check if it's a prerequisite data missing error
        if "missing" in str(ve).lower():
            raise PrerequisiteDataMissingException(accession_number, ["section summaries"])
        else:
            raise SummaryGenerationException(accession_number, str(ve))
    except Exception as e:
        raise handle_domain_exception(e)

async def generate_summary_async_wrapper(accession_number: str):
    # FastAPI runs in an async event loop. CPU-bound tasks like LLM calls or intensive processing
    # should be run in a separate thread pool to avoid blocking the event loop.
    # For simplicity here, if your LLM client library is already async-compatible or if the calls are quick enough
    # for your load, direct calling might seem okay. But for production, use `run_in_executor`.
    # However, `psycopg2` is synchronous. Direct calls to DB within an async def without `run_in_executor` 
    # for the DB part AND the LLM part will block. 
    # `generate_and_store_top_level_summary` is currently fully synchronous.
    
    # This is a simplified approach. Ideally, make generate_and_store_top_level_summary async
    # or properly use FastAPI's `run_in_executor` for the entire synchronous function.
    # For now, this will work but might block the event loop under load.
    try:
        # This call is synchronous and will block the event loop.
        summary = generate_and_store_top_level_summary(accession_number)
        return summary
    except Exception as e:
        # Propagate exception to be handled by the main endpoint function
        raise 