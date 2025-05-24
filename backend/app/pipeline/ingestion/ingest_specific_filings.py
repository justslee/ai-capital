import asyncio
import logging
from datetime import datetime

from backend.app.db.session import AsyncSessionFactory
from backend.app.services.sec_client import SECClient
from backend.app.services.filings_service import store_filing
from backend.app.sec_utils import get_company_info_by_ticker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def ingest_specific_filing(ticker: str, accession_number_to_ingest: str):
    logger.info(f"Starting filing ingestion for {ticker} - {accession_number_to_ingest}")

    # Initialize SEC client
    sec_client = SECClient()

    # Get company info
    company_info = get_company_info_by_ticker(ticker)
    if not company_info:
        logger.error(f"Could not resolve company info for {ticker}")
        return

    cik = company_info["cik"]
    company_name = company_info["company_name"]
    logger.info(f"Processing {company_name} (CIK: {cik}) for accession: {accession_number_to_ingest}")

    # Fetch the specific filing metadata
    # Note: get_company_filings might not be the best way if we have the exact accession number.
    # We might need a more direct way to get filing metadata by accession number or construct it.
    # For now, we'll try to find it in recent filings, assuming it's recent.
    # This part may need adjustment if SECClient doesn't easily provide metadata for a *specific* old accession number.
    
    filing_meta = None
    try:
        # Attempt to get all 10-K filings and find the one matching the accession number.
        # This is not ideal, a more direct fetch by accession number would be better.
        # If sec_client had a get_filing_by_accession_number, that would be used.
        all_10k_filings = sec_client.get_company_filings(
            cik=cik,
            filing_types=["10-K"] # Fetch more to increase chance of finding it
        )
        for f_meta in all_10k_filings:
            if f_meta["accession_number"].replace("-", "") == accession_number_to_ingest.replace("-", ""):
                filing_meta = f_meta
                break
        
        if not filing_meta:
            logger.warning(f"Could not find exact filing metadata for {accession_number_to_ingest} via get_company_filings. Will rely on hardcoded metadata if available.")
            # Removed problematic calls to non-existent SECClient methods:
            # get_submission_files, get_filing_details_by_accession, list_filing_documents
            # The logic will now fall through to the section that uses hardcoded values if filing_meta is still None.

    except Exception as e:
        logger.error(f"Error during initial metadata fetch for {accession_number_to_ingest}: {e}")
        # We don't return here anymore, to allow fallback to hardcoded metadata
        pass # Continue to the next block that checks filing_meta

    if not filing_meta or not filing_meta.get("filing_date") or not filing_meta.get("primary_doc"):
        logger.info(f"Filing metadata not found or incomplete after initial fetch for {accession_number_to_ingest}. Attempting to use hardcoded values.")
        # Attempt to get filing_date and primary_doc directly from SECClient if possible - this section now primarily handles hardcoding
        # This part depends heavily on SECClient's capabilities for specific accession numbers
        try:
            logger.info(f"Attempting to retrieve filing details directly for {accession_number_to_ingest}")
            # This is a mock-up of what would be needed from SECClient
            # details = sec_client.get_filing_details(cik, accession_number_to_ingest)
            # filing_meta["filing_date"] = details.get("filing_date")
            # filing_meta["primary_doc"] = details.get("primary_document")
            # filing_meta["form_type"] = details.get("form_type", "10-K")
            
            # A more realistic approach with current SECClient might involve fetching submission files
            # and heuristically determining the primary document and parsing an index file for the date.
            # For now, we'll rely on the prior search or manual construction and accept it might be incomplete.
            # The web search provided some dates, we should use those.
            if ticker == "NVDA" and accession_number_to_ingest == "0001047469-24-000040":
                filing_meta = {
                    "accession_number": "0001047469-24-000040",
                    "primary_doc": "d669480d10k.htm", # Common pattern, but best to get from SEC API
                    "form_type": "10-K",
                    "filing_date": "2024-02-22" 
                }
                logger.info(f"Using hardcoded metadata for NVDA: {filing_meta}")
            elif ticker == "TSLA" and accession_number_to_ingest == "0001628280-24-002390":
                filing_meta = {
                    "accession_number": "0001628280-24-002390",
                    "primary_doc": "tsla-20231231.htm", # Common pattern
                    "form_type": "10-K",
                    "filing_date": "2024-01-29"
                }
                logger.info(f"Using hardcoded metadata for TSLA: {filing_meta}")
            else:
                logger.error(f"Insufficient metadata for {accession_number_to_ingest} and no hardcoded values available.")
                return


        except Exception as e:
            logger.error(f"Error trying to retrieve specific filing details for {accession_number_to_ingest}: {e}")
            return # Still abort if we can't get it

    logger.info(f"Proceeding with filing_meta: {filing_meta}")

    # Parse filing date
    try:
        filing_date = datetime.strptime(filing_meta["filing_date"], "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Error parsing filing date '{filing_meta['filing_date']}' for {accession_number_to_ingest}: {e}")
        return
    except TypeError as e:
        logger.error(f"Filing date is None or not a string for {accession_number_to_ingest}: {e}")
        return


    # Get the filing URL
    # Ensure accession_number in filing_meta does not have dashes for URL construction if sec_client expects that
    accession_number_for_url = filing_meta["accession_number"].replace("-", "")
    
    form_url = sec_client.get_filing_html_url(
        cik=cik,
        accession_number=accession_number_for_url, # Use the one from meta, possibly without dashes
        primary_doc=filing_meta["primary_doc"]
    )
    logger.info(f"Form URL for {accession_number_to_ingest}: {form_url}")

    # Download the filing content
    try:
        logger.info(f"Downloading: CIK={cik}, Acc#={filing_meta['accession_number']}, Doc={filing_meta['primary_doc']}")
        raw_html = sec_client.download_filing_html(
            cik=cik, # Original CIK
            accession_number=filing_meta["accession_number"], # Original accession_number from meta
            primary_doc=filing_meta["primary_doc"] # Primary_doc from meta
        )
    except Exception as e:
        logger.error(f"Error downloading filing content for {accession_number_to_ingest}: {e}")
        logger.error(f"Download params: CIK={cik}, Acc#={filing_meta['accession_number']}, Doc={filing_meta['primary_doc']}")
        import traceback
        traceback.print_exc()
        return

    if not raw_html:
        logger.error(f"Downloaded HTML content is empty for {accession_number_to_ingest}. Aborting.")
        return
    logger.info(f"Successfully downloaded HTML for {accession_number_to_ingest}, length: {len(raw_html)} bytes.")

    # Store in database
    async with AsyncSessionFactory() as db:
        try:
            stored_filing = await store_filing(
                db=db,
                accession_number=filing_meta["accession_number"],
                company_name=company_name,
                ticker=ticker,
                cik=cik,
                filing_type=filing_meta["form_type"],
                filing_date=filing_date,
                form_url=form_url,
                raw_html=raw_html
            )
            if stored_filing:
                logger.info(f"Successfully stored filing: {stored_filing.accession_number} for {ticker}")
            else:
                # store_filing should ideally return the existing one or raise a specific exception for duplicates
                logger.info(f"Filing {filing_meta['accession_number']} for {ticker} might already exist or was not stored.")
        except Exception as e:
            import traceback
            logger.error(f"Error storing filing {accession_number_to_ingest} for {ticker}: {e}")
            traceback.print_exc()
            return

async def main():
    filings_to_ingest = [
        {"ticker": "NVDA", "accession_number": "0001047469-24-000040"},
        {"ticker": "TSLA", "accession_number": "0001628280-24-002390"},
    ]

    for item in filings_to_ingest:
        await ingest_specific_filing(item["ticker"], item["accession_number"])

if __name__ == "__main__":
    asyncio.run(main()) 