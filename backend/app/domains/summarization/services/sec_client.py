import requests
from typing import List, Optional, Dict
from app.sec_utils import ticker_to_cik

BASE_EDGAR_URL = "https://data.sec.gov"
# Updated User-Agent to be more specific and include a placeholder for contact info
USER_AGENT = "Mozilla/5.0 (compatible; SEC-lookup/1.0; +http://yourdomain.com/bot.html)" 
HEADERS = {"User-Agent": USER_AGENT}

class SECClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_company_filings(self, cik: str, filing_types: Optional[List[str]] = None, count: int = 10) -> List[Dict]:
        """
        Fetch recent filings for a given CIK from the SEC EDGAR API.
        Optionally filter by filing types (e.g., ['10-K', '10-Q', '8-K']).
        Returns a list of filings metadata dicts.
        """
        # CIK must be zero-padded to 10 digits for submissions API
        cik_padded = str(cik).lstrip("0").zfill(10)
        url = f"{BASE_EDGAR_URL}/submissions/CIK{cik_padded}.json"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        results = []
        for i in range(len(filings.get("accessionNumber", []))):
            form_type = filings["form"].get(i) if isinstance(filings["form"], dict) else filings["form"][i]
            if filing_types and form_type not in filing_types:
                continue
            filing = {
                "accession_number": filings["accessionNumber"][i],
                "filing_date": filings["filingDate"][i],
                "form_type": form_type,
                "primary_doc": filings["primaryDocument"][i],
                "primary_doc_description": filings.get("primaryDocDescription", [None]*len(filings["accessionNumber"]))[i],
            }
            results.append(filing)
            if len(results) >= count:
                break
        return results

    def get_company_filings_by_ticker(self, ticker: str, filing_types: Optional[List[str]] = None, count: int = 10) -> List[Dict]:
        """
        Fetch recent filings for a given ticker symbol using SEC's ticker-to-CIK mapping.
        """
        cik = ticker_to_cik(ticker)
        if cik is None:
            raise ValueError(f"CIK not found for ticker: {ticker}")
        return self.get_company_filings(cik, filing_types=filing_types, count=count)

    def get_filing_html_url(self, cik: str, accession_number: str, primary_doc: str) -> str:
        """
        Construct the URL to the raw HTML filing document.
        The CIK in the path should NOT be zero-padded.
        """
        accession_nodash = accession_number.replace("-", "")
        cik_for_url = str(cik).lstrip("0") # Correct for archive URLs
        return f"https://www.sec.gov/Archives/edgar/data/{cik_for_url}/{accession_nodash}/{primary_doc}"

    def download_filing_html(self, cik: str, accession_number: str, primary_doc: str) -> str:
        """
        Download the raw HTML content of a filing.
        Returns the HTML content as a string.
        
        Args:
            cik: The company's CIK number
            accession_number: The filing's accession number
            primary_doc: The primary document name
            
        Returns:
            str: The raw HTML content of the filing
            
        Raises:
            requests.exceptions.RequestException: If the download fails
        """
        url = self.get_filing_html_url(cik, accession_number, primary_doc)
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.text

    def download_filing_html_by_ticker(self, ticker: str, accession_number: str, primary_doc: str) -> str:
        """
        Download the raw HTML content of a filing using a ticker symbol.
        Returns the HTML content as a string.
        
        Args:
            ticker: The company's ticker symbol
            accession_number: The filing's accession number
            primary_doc: The primary document name
            
        Returns:
            str: The raw HTML content of the filing
            
        Raises:
            ValueError: If the ticker cannot be resolved to a CIK
            requests.exceptions.RequestException: If the download fails
        """
        cik = ticker_to_cik(ticker)
        if cik is None:
            raise ValueError(f"CIK not found for ticker: {ticker}")
        # Pass the original CIK (which might be padded or not, get_filing_html_url will strip leading zeros)
        return self.download_filing_html(cik, accession_number, primary_doc) 