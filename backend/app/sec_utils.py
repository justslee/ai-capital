import requests
import os
import json
from typing import Optional, Dict, Any

SEC_TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_FILE = "/tmp/sec_company_tickers.json"
# Define a common User-Agent, similar to SECClient
REQUESTS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEC-lookup/1.0; +http://yourdomain.com/bot.html)"} 
# It's good practice to include contact info in the UA string if you have a domain/project page.

def download_ticker_cik_json(force_refresh: bool = False) -> dict:
    """
    Download and cache the SEC's company_tickers.json file.
    Returns the parsed JSON as a dict.
    """
    if not force_refresh and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    # Use the defined headers for the request
    resp = requests.get(SEC_TICKER_CIK_URL, headers=REQUESTS_HEADERS)
    resp.raise_for_status()
    data = resp.json()
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)
    return data

def get_company_info_by_ticker(ticker: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Given a ticker, return a dict with CIK and company name (title).
    CIK is 10-digit zero-padded.
    Returns None if not found.
    Example: {"cik": "0000320193", "company_name": "Apple Inc."}
    """
    ticker_upper = ticker.upper()
    data = download_ticker_cik_json(force_refresh=force_refresh)
    for entry in data.values():
        if "ticker" in entry and "cik_str" in entry and "title" in entry and entry["ticker"].upper() == ticker_upper:
            cik_int = int(entry["cik_str"])
            return {
                "cik": f"{cik_int:010d}",
                "company_name": entry["title"]
            }
    return None

# Keep the old ticker_to_cik for compatibility or remove if not used elsewhere
def ticker_to_cik(ticker: str, force_refresh: bool = False) -> Optional[str]:
    """
    Given a ticker, return the 10-digit zero-padded CIK as a string, or None if not found.
    (Deprecated in favor of get_company_info_by_ticker if name is also needed)
    """
    company_info = get_company_info_by_ticker(ticker, force_refresh)
    return company_info["cik"] if company_info else None 