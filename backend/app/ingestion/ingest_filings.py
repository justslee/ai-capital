import asyncio
import logging
from datetime import datetime
import sys
import os
from typing import List, Dict, Any

from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Load environment variables from .env file
load_dotenv()

from app.domains.data_collection.clients.sec_client import SECClient
from app.domains.data_collection.storage.s3_storage_service import S3StorageService
from app.sec_utils import get_company_info_by_ticker
from app.domains.summarizer.parsing.extract_text_from_html import (
    preprocess_html,
    normalize_text,
    segment_sec_sections,
    chunk_section_content,
)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of tickers to process
TICKERS_TO_INGEST = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]
FILING_TYPES_TO_INGEST = ["10-K", "10-Q"]
RECENT_FILINGS_COUNT = 2 # How many recent filings to check for each type

async def save_chunks_to_s3(
    s3_storage_service: S3StorageService,
    chunks: List[Dict[str, Any]],
    ticker: str,
    accession_number: str,
    section_key: str
):
    """Saves a list of chunks for a given section to S3."""
    tasks = []
    for i, chunk_data in enumerate(chunks):
        task = s3_storage_service.save_chunk_text(
            chunk_text=chunk_data['text'],
            ticker=ticker,
            accession_number=accession_number,
            section_key=section_key,
            chunk_index=i
        )
        tasks.append(task)
    await asyncio.gather(*tasks)

async def ingest_and_chunk_filings_for_ticker(client: SECClient, s3_service: S3StorageService, ticker: str):
    """Fetches filings, chunks them, and stores chunks in S3."""
    logger.info(f"Starting ingestion for ticker: {ticker}")

    company_info = get_company_info_by_ticker(ticker)
    if not company_info:
        logger.error(f"Could not resolve CIK or company name for ticker: {ticker}. Skipping.")
        return

    cik = company_info["cik"]
    logger.info(f"Processing ticker {ticker} (CIK: {cik})")

    try:
        recent_filings_metadata = client.get_company_filings(
            cik=cik,
            filing_types=FILING_TYPES_TO_INGEST,
            count=RECENT_FILINGS_COUNT
        )
    except Exception as e:
        logger.error(f"Error fetching filings metadata for {ticker} (CIK: {cik}): {e}", exc_info=True)
        return

    if not recent_filings_metadata:
        logger.info(f"No recent filings found for {ticker} of types {FILING_TYPES_TO_INGEST}.")
        return

    logger.info(f"Found {len(recent_filings_metadata)} filings for {ticker}. Processing...")

    for filing_meta in recent_filings_metadata:
        accession_number = filing_meta["accession_number"]
        primary_doc = filing_meta["primary_doc"]
        form_type = filing_meta["form_type"]

        logger.info(f"Processing filing {accession_number} ({form_type}) for {ticker}...")

        # 1. Download HTML content
        logger.info(f"  - Downloading HTML content...")
        try:
            raw_html_content = client.download_filing_html(cik, accession_number, primary_doc)
            if not raw_html_content:
                logger.warning(f"  - No HTML content for {accession_number}. Skipping.")
                continue
        except Exception as e:
            logger.error(f"  - Error downloading HTML for {accession_number}: {e}", exc_info=True)
            continue

        # 2. Parse and Chunk the HTML
        logger.info(f"  - Parsing and chunking HTML...")
        try:
            preprocessed_text = preprocess_html(raw_html_content)
            normalized_text = normalize_text(preprocessed_text)
            sections_data = segment_sec_sections(normalized_text)

            if not sections_data:
                logger.warning(f"  - No sections extracted for {accession_number}. Skipping.")
                continue

            total_chunks_saved = 0
            for section_key, (original_header, section_text) in sections_data.items():
                if not section_text.strip():
                    continue

                chunks = chunk_section_content(section_text)
                if chunks:
                    logger.info(f"    - Section '{section_key}': Found {len(chunks)} chunks. Saving to S3...")
                    await save_chunks_to_s3(
                        s3_service, chunks, ticker, accession_number, section_key
                    )
                    total_chunks_saved += len(chunks)

            logger.info(f"  - Finished processing for {accession_number}. Total chunks saved: {total_chunks_saved}")

        except Exception as e:
            logger.error(f"  - Error processing or saving chunks for {accession_number}: {e}", exc_info=True)
            continue

    logger.info(f"Finished ingestion for ticker: {ticker}")


async def main_ingestion_loop():
    logger.info("Starting main SEC filings ingestion and chunking loop (DB-free)...")
    
    # Check for required environment variables for S3
    if not all(os.getenv(k) for k in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET"]):
        logger.error("Missing required AWS environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET).")
        return

    sec_client = SECClient()
    s3_service = S3StorageService()

    for ticker_symbol in TICKERS_TO_INGEST:
        try:
            await ingest_and_chunk_filings_for_ticker(sec_client, s3_service, ticker_symbol)
        except Exception as e:
            logger.error(f"Unhandled error processing ticker {ticker_symbol}: {e}", exc_info=True)

    logger.info("Main SEC filings ingestion and chunking loop finished.")

if __name__ == "__main__":
    asyncio.run(main_ingestion_loop()) 