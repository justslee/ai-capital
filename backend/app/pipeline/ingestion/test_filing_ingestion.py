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

async def test_filing_ingestion():
    logger.info("Starting filing ingestion test for AAPL")
    
    # Initialize SEC client
    sec_client = SECClient()
    
    # Get company info
    company_info = get_company_info_by_ticker("AAPL")
    if not company_info:
        logger.error("Could not resolve company info for AAPL")
        return
    
    cik = company_info["cik"]
    company_name = company_info["company_name"]
    logger.info(f"Processing {company_name} (CIK: {cik})")
    
    # Fetch recent 10-K filing
    try:
        recent_filings = sec_client.get_company_filings(
            cik=cik,
            filing_types=["10-K"],
            count=1
        )
    except Exception as e:
        logger.error(f"Error fetching filings metadata: {e}")
        return
    
    if not recent_filings:
        logger.error("No recent filings found")
        return
    
    filing_meta = recent_filings[0]
    logger.info(f"Found filing: {filing_meta}")
    
    # Parse filing date
    try:
        filing_date = datetime.strptime(filing_meta["filing_date"], "%Y-%m-%d")
    except ValueError as e:
        logger.error(f"Error parsing filing date: {e}")
        return
    
    # Get the filing URL
    form_url = sec_client.get_filing_html_url(
        cik=cik,
        accession_number=filing_meta["accession_number"],
        primary_doc=filing_meta["primary_doc"]
    )
    
    # Download the filing content
    try:
        raw_html = sec_client.download_filing_html(
            cik=cik,
            accession_number=filing_meta["accession_number"],
            primary_doc=filing_meta["primary_doc"]
        )
    except Exception as e:
        logger.error(f"Error downloading filing content: {e}")
        return
    
    # Store in database
    async with AsyncSessionFactory() as db:
        try:
            stored_filing = await store_filing(
                db=db,
                accession_number=filing_meta["accession_number"],
                company_name=company_name,
                ticker="AAPL",
                cik=cik,
                filing_type=filing_meta["form_type"],
                filing_date=filing_date,
                form_url=form_url,
                raw_html=raw_html
            )
            if stored_filing:
                logger.info(f"Successfully stored filing: {stored_filing}")
            else:
                logger.info("Filing already exists in database")
        except Exception as e:
            import traceback
            logger.error(f"Error storing filing: {e}")
            traceback.print_exc()
            return

if __name__ == "__main__":
    asyncio.run(test_filing_ingestion()) 