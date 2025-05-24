import asyncio
import logging
from datetime import datetime

from backend.app.db.session import SessionLocalAsync # Corrected import path
from backend.app.services.sec_client import SECClient
from backend.app.services.filings_service import store_filing
from backend.app.sec_utils import get_company_info_by_ticker

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of tickers to process
TICKERS_TO_INGEST = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
FILING_TYPES_TO_INGEST = ["10-K", "10-Q", "8-K"]
RECENT_FILINGS_COUNT = 10 # How many recent filings to check for each type

async def ingest_filings_for_ticker(db: SessionLocalAsync, client: SECClient, ticker: str):
    logger.info(f"Starting ingestion for ticker: {ticker}")

    company_info = get_company_info_by_ticker(ticker)
    if not company_info:
        logger.error(f"Could not resolve CIK or company name for ticker: {ticker}. Skipping.")
        return

    cik = company_info["cik"]
    company_name = company_info["company_name"]
    logger.info(f"Processing {company_name} (CIK: {cik})")

    try:
        # Fetch recent filings (10-K, 10-Q, 8-K)
        # The get_company_filings method handles CIK formatting
        recent_filings_metadata = client.get_company_filings(
            cik=cik,
            filing_types=FILING_TYPES_TO_INGEST,
            count=RECENT_FILINGS_COUNT 
        )
    except Exception as e:
        logger.error(f"Error fetching filings metadata for {ticker} (CIK: {cik}): {e}", exc_info=True)
        return

    if not recent_filings_metadata:
        logger.info(f"No recent filings found for {ticker} (CIK: {cik}) of types {FILING_TYPES_TO_INGEST}.")
        return

    logger.info(f"Found {len(recent_filings_metadata)} filings for {ticker}. Processing...")

    for filing_meta in recent_filings_metadata:
        accession_number = filing_meta["accession_number"]
        form_type = filing_meta["form_type"]
        primary_doc = filing_meta["primary_doc"]
        
        # Parse filing_date string to datetime object
        try:
            filing_date_obj = datetime.strptime(filing_meta["filing_date"], "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Error parsing filing_date '{filing_meta['filing_date']}' for {accession_number}: {e}")
            continue # Skip this filing

        # Construct the full form URL
        form_url = client.get_filing_html_url(cik, accession_number, primary_doc)

        logger.info(f"Fetching HTML for {accession_number} ({form_type}) for {ticker}...")
        try:
            raw_html_content = client.download_filing_html(cik, accession_number, primary_doc)
        except Exception as e:
            logger.error(f"Error downloading HTML for {accession_number} ({ticker}): {e}", exc_info=True)
            continue # Skip this filing
        
        logger.info(f"Storing filing {accession_number} ({form_type}) for {ticker}...")
        await store_filing(
            db=db,
            accession_number=accession_number,
            company_name=company_name,
            ticker=ticker,
            cik=cik,
            filing_type=form_type,
            filing_date=filing_date_obj,
            form_url=form_url,
            raw_html=raw_html_content
        )
    logger.info(f"Finished ingestion for ticker: {ticker}")

async def main_ingestion_loop():
    logger.info("Starting main SEC filings ingestion loop...")
    sec_client = SECClient()
    
    async with SessionLocalAsync() as db_session:
        for ticker_symbol in TICKERS_TO_INGEST:
            try:
                await ingest_filings_for_ticker(db_session, sec_client, ticker_symbol)
            except Exception as e:
                logger.error(f"Unhandled error processing ticker {ticker_symbol}: {e}", exc_info=True)
        
    logger.info("Main SEC filings ingestion loop finished.")

if __name__ == "__main__":
    # To run this script from the project root (e.g., /Users/justinlee/ai_capital):
    # PYTHONPATH=. python backend/app/ingestion/ingest_filings.py
    # Or from backend/ directory:
    # PYTHONPATH=.. python app/ingestion/ingest_filings.py
    asyncio.run(main_ingestion_loop()) 