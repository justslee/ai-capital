"""
HTML Parsing Service for SEC Filings

This service is responsible for parsing the HTML content of SEC filings
to extract sections based on their semantic structure.
"""
import logging
from typing import Dict, Optional

from ...data_collection.storage.s3_storage_service import S3StorageService, get_s3_storage_service
from .sec_parser_service import SecParserService, get_sec_parser_service

logger = logging.getLogger(__name__)


class DocumentParsingService:
    """
    Service responsible for fetching raw documents and parsing them into clean, section-aware text.
    """
    def __init__(self, s3_storage_service: S3StorageService):
        """Initializes the service with a dependency on the S3 storage service."""
        self.s3_service = s3_storage_service
        self.sec_parser_service = get_sec_parser_service()

    async def get_filing_sections(self, ticker: str, accession_number: str, form_type: str = '10-Q') -> Dict[str, str]:
        """
        Fetches a filing's HTML, parses it, and splits it into sections using semantic parsing.
        Downloads from SEC if not in S3.

        :param ticker: The stock ticker.
        :param accession_number: The filing's accession number.
        :param form_type: The type of filing (10-Q, 10-K, etc.)
        :return: A dictionary where keys are section titles and values are the aggregated text content.
        """
        logger.info(f"Fetching filing HTML for {ticker} ({accession_number}) from S3.")
        html_content = await self.s3_service.get_filing_html(ticker, accession_number)
        
        if not html_content:
            logger.info(f"HTML not found in S3, downloading from SEC for {accession_number}")
            html_content = await self._download_filing_from_sec(ticker, accession_number, form_type)
            
            if not html_content:
                raise ValueError(f"Could not retrieve HTML for {accession_number} from SEC or S3.")
            
            logger.info(f"Storing downloaded HTML in S3 for {accession_number}")
            await self.s3_service.save_filing_html(html_content, ticker, accession_number)

        logger.info("Parsing HTML using semantic sec-parser approach.")
        return self.sec_parser_service.parse_filing_to_sections(html_content, form_type)
    
    async def _download_filing_from_sec(self, ticker: str, accession_number: str, form_type: str) -> Optional[str]:
        """
        Downloads filing HTML directly from SEC Edgar.
        """
        import asyncio
        from ...data_collection.clients.sec_client import get_sec_client

        sec_client = get_sec_client()
        logger.info(f"Attempting to download filing {accession_number} for {ticker}")

        try:
            html_content = await asyncio.to_thread(
                sec_client.download_filing_html_by_ticker, ticker, accession_number, primary_doc=None, form_type=form_type
            )
            if html_content and len(html_content) > 1000:
                logger.info(f"Successfully downloaded HTML for {accession_number} using sec-downloader.")
                return html_content
            else:
                logger.warning(f"Downloaded HTML for {accession_number} is empty or too small (<1000 chars).")
                return None
        except Exception as e:
            logger.error(f"Failed to download filing {accession_number} for {ticker} using sec-downloader: {e}")
            return None


# Singleton instance
_parsing_service: Optional[DocumentParsingService] = None

def get_parsing_service() -> "DocumentParsingService":
    """
    Provides a singleton instance of the DocumentParsingService.
    """
    global _parsing_service
    if _parsing_service is None:
        s3_service = get_s3_storage_service()
        _parsing_service = DocumentParsingService(s3_service)
    return _parsing_service 