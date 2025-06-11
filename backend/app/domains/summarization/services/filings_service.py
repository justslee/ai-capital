import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.filings import SECFilingDB
from app.schemas.filings import SECFiling # Pydantic model for type hinting if needed

logger = logging.getLogger(__name__)

async def get_filing_by_accession_number(db: AsyncSession, accession_number: str) -> Optional[SECFilingDB]:
    """Retrieve a filing by its accession number."""
    result = await db.execute(select(SECFilingDB).where(SECFilingDB.accession_number == accession_number))
    return result.scalar_one_or_none()

async def store_filing(
    db: AsyncSession,
    accession_number: str,
    company_name: str,
    ticker: str,
    cik: str,
    filing_type: str,
    filing_date: datetime, # Ensure this is a datetime object
    form_url: str,
    raw_html: Optional[str] = None
) -> Optional[SECFilingDB]:
    """
    Stores a new SEC filing in the database if it doesn't already exist.

    Args:
        db: The SQLAlchemy async session.
        accession_number: Unique ID for the filing.
        company_name: Name of the company.
        ticker: Stock ticker.
        cik: Company CIK.
        filing_type: Type of filing (e.g., '10-K').
        filing_date: Date of the filing.
        form_url: URL to the filing document on SEC Edgar.
        raw_html: The raw HTML content of the filing (optional).

    Returns:
        The created SECFilingDB object if successful, None otherwise (e.g., if duplicate).
    """
    logger.info(f"Attempting to store filing: {accession_number} for {ticker}")

    # 1. Check if filing already exists
    existing_filing = await get_filing_by_accession_number(db, accession_number)
    if existing_filing:
        logger.info(f"Filing {accession_number} already exists in the database. Skipping.")
        return None # Or return existing_filing if that's preferred

    # 2. Create new filing object
    new_filing = SECFilingDB(
        accession_number=accession_number,
        company_name=company_name,
        ticker=ticker,
        cik=cik,
        filing_type=filing_type,
        filing_date=filing_date, # Should be a datetime object
        form_url=form_url,
        raw_html=raw_html
        # created_at and updated_at will be handled by server_default in the model
    )

    try:
        db.add(new_filing)
        await db.commit()
        await db.refresh(new_filing)
        logger.info(f"Successfully stored new filing: {accession_number} for {ticker}")
        return new_filing
    except Exception as e:
        await db.rollback()
        logger.error(f"Error storing filing {accession_number}: {e}", exc_info=True)
        return None 