import sys
import os

# Adjust the path to include the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from backend.app.domains.data_collection.clients.sec_client import SECClient

def get_latest_10k_accession_number(ticker: str):
    """
    Fetches the most recent 10-K filing for a given ticker
    and returns its accession number.
    """
    client = SECClient()
    try:
        # We need to specify the user agent as per SEC requirements.
        # The SECClient seems to handle this, but it's good practice to be aware.
        filings = client.get_company_filings_by_ticker(ticker, filing_types=["10-K"], count=1)
        if filings:
            accession_number = filings[0]['accession_number']
            print(f"Latest 10-K for {ticker} has accession number: {accession_number}")
            return accession_number
        else:
            print(f"No 10-K filings found for {ticker}.")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ticker_symbol = sys.argv[1]
        get_latest_10k_accession_number(ticker_symbol)
    else:
        print("Please provide a ticker symbol.")
        sys.exit(1) 