import requests
from typing import List, Optional, Dict
from app.sec_utils import ticker_to_cik
from sec_downloader import Downloader
from sec_downloader.types import RequestedFilings

# Updated User-Agent to be more specific and include a placeholder for contact info
USER_AGENT = "Mozilla/5.0 (compatible; SEC-lookup/1.0; +http://yourdomain.com/bot.html)" 

class SECClient:
    def __init__(self):
        self.downloader = Downloader("AI Capital", "contact@ai-capital.com")

    def get_company_filings_by_ticker(self, ticker: str, filing_types: Optional[List[str]] = None, count: int = 10) -> List[Dict]:
        """
        Fetch recent filings for a given ticker symbol using sec-downloader.
        """
        req_filings = RequestedFilings(
            ticker_or_cik=ticker,
            form_type=filing_types[0] if filing_types else None, # sec-downloader expects a single form_type
            limit=count,
        )
        metadatas = self.downloader.get_filing_metadatas(req_filings)
        
        results = []
        for metadata in metadatas:
            # sec-downloader returns FilingMetadata objects, convert to original dict format
            results.append({
                "accession_number": metadata.accession_number,
                "filing_date": metadata.filing_date,
                "form_type": metadata.form_type,
                "primary_doc": metadata.primary_doc_url.split('/')[-1], # Extract document name from URL
                "primary_doc_description": metadata.primary_doc_description,
                "primary_doc_url": metadata.primary_doc_url, # Add this line
            })
        return results

    def download_filing_html_by_ticker(self, ticker: str, accession_number: str, primary_doc: Optional[str] = None, form_type: Optional[str] = None) -> Optional[str]:
        """
        Download the raw HTML content of a filing using a ticker symbol and accession number.
        This method leverages the sec-downloader to get the full URL and download content.
        
        Args:
            ticker: The company's ticker symbol
            accession_number: The filing's accession number
            primary_doc: The primary document name (optional, if sec-downloader can infer)
            form_type: The type of filing (e.g., "10-K", "10-Q") (optional)
            
        Returns:
            str: The raw HTML content of the filing, or None if not found/error
            
        Raises:
            ValueError: If the ticker cannot be resolved to a CIK or filing is not found
            RuntimeError: If the download fails for other reasons
        """
        try:
            # Fetch filings using the existing method which now returns primary_doc_url
            # Filter by form_type if provided to narrow down the search
            filings = self.get_company_filings_by_ticker(ticker, filing_types=[form_type] if form_type else None, count=10) # Fetch a few recent ones
            
            target_filing_url = None
            for filing in filings:
                if filing['accession_number'] == accession_number:
                    # If primary_doc is specified, ensure it matches
                    if primary_doc and primary_doc != filing['primary_doc']:
                        continue
                    # If form_type is specified, ensure it matches
                    if form_type and form_type != filing['form_type']:
                        continue
                    target_filing_url = filing['primary_doc_url']
                    break
            
            if not target_filing_url:
                raise ValueError(f"Filing with accession {accession_number}, primary doc {primary_doc}, and form type {form_type} not found for {ticker}")

            downloaded_file_content = self.downloader.download_filing(url=target_filing_url)
            return downloaded_file_content.decode('utf-8') if downloaded_file_content else None
        except Exception as e:
            raise RuntimeError(f"Failed to download filing HTML using sec-downloader: {e}") from e





_sec_client = None

def get_sec_client() -> "SECClient":
    """
    Provides a singleton instance of the SECClient.
    """
    global _sec_client
    if _sec_client is None:
        _sec_client = SECClient()
    return _sec_client 