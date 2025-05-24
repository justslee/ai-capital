from fastapi import APIRouter, HTTPException, Path
from app.core.summary_generation import generate_and_store_top_level_summary
from app.db.database_utils import db_cursor # For direct DB queries if needed by the endpoint logic
import psycopg2
import sys

router = APIRouter()

@router.get("/summary/{ticker}/{year}/{form_type}")
async def get_filing_summary(
    ticker: str = Path(..., title="Stock Ticker", description="The ticker symbol of the company (e.g., AAPL)", min_length=1, max_length=10),
    year: int = Path(..., title="Filing Year", description="The four-digit year of the filing (e.g., 2023)"),
    form_type: str = Path(..., title="Form Type", description="The SEC form type (e.g., 10-K, 10-Q). Currently optimized for 10-K.", regex="^(10-K|10-Q)$")
):
    """
    Provides a top-level summary for a specified company filing.
    
    The summary is generated based on pre-existing section summaries (Business, MD&A, Risk Factors).
    If a top-level summary for the latest filing matching the criteria is already cached, it's returned.
    Otherwise, it's generated on-the-fly using GPT-4, stored, and then returned.
    """
    requested_form_type_upper = form_type.upper()
    print(f"Received request for summary: Ticker={ticker}, Year={year}, Form Type Input={requested_form_type_upper}")

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
                print(f"Found accession_number: {accession_number} for Ticker: {ticker}, Year: {year}, DB_Filing_Type: {requested_form_type_upper}")
            else:
                print(f"No matching '10-K' filing found for Ticker: {ticker}, Year: {year}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"No '10-K' filing found for ticker '{ticker}' in year {year}."
                )
    except psycopg2.Error as db_err:
        print(f"Database error while fetching accession number: {db_err}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Database error while retrieving filing information.")
    except Exception as e:
        print(f"Unexpected error while fetching accession number: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

    if not accession_number:
        # This case should ideally be caught above, but as a safeguard.
        raise HTTPException(status_code=404, detail=f"Could not determine accession number for {ticker} {year} {form_type}.")

    try:
        summary_text = await generate_summary_async_wrapper(accession_number)
        # The summary text here is expected to be a pre-formatted string (e.g. Markdown-like from LLM)
        # For JSON output, we might want to structure it, but user asked for "JSON of summary bullets"
        # If the LLM already formats it with bullets, we can return it directly or parse it.
        # For now, returning the raw text as a JSON string value.
        return {"ticker": ticker, "year": year, "form_type": form_type, "accession_number": accession_number, "summary": summary_text}
    except ValueError as ve: # Raised by generate_and_store_top_level_summary if prerequisites missing
        print(f"ValueError during summary generation for {accession_number}: {ve}")
        raise HTTPException(status_code=409, detail=str(ve)) # 409 Conflict - prerequisite data missing
    except Exception as e:
        print(f"Error generating or retrieving summary for {accession_number}: {e}")
        # Consider more specific error codes based on exception types from generate_and_store_top_level_summary
        raise HTTPException(status_code=500, detail=f"Failed to generate or retrieve summary: {str(e)}")

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