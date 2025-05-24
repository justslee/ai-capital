import psycopg2
import sys
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# --- Load .env and set DB URL ---
# Assuming this script is in dev_utils or similar, adjust path to .env accordingly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}. DB URL must be set.")
    # sys.exit(1) # Or handle error as appropriate

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found. Please set it in .env or as an environment variable.")
    sys.exit(1)

# --- Database Connection Parameters ---
parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))
conn_params = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port or 5432,
    'sslmode': 'require' 
}

ACCESSION_TO_CHECK = '0000320193-24-000123' # AAPL example

def main():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print(f"Connected to PostgreSQL database '{conn_params['dbname']}'.\n")

        query_filing_info = """
        SELECT ticker, filing_type, filing_date, EXTRACT(YEAR FROM filing_date) as extracted_year
        FROM sec_filings 
        WHERE accession_number = %s;
        """
        cur.execute(query_filing_info, (ACCESSION_TO_CHECK,))
        filing_info = cur.fetchone()
        
        if filing_info:
            ticker, filing_type, filing_date, extracted_year = filing_info
            print(f"--- Info for Accession Number: {ACCESSION_TO_CHECK} ---")
            print(f"  Ticker: {ticker}")
            print(f"  Filing Type: {filing_type}")
            print(f"  Filing Date: {filing_date}")
            print(f"  Extracted Year (from filing_date): {int(extracted_year) if extracted_year else 'N/A'}")
            print("\nTo use this filing with the API, if it's a 10-K, try the URL:")
            print(f"  http://127.0.0.1:8000/api/v1/summary/{ticker}/{int(extracted_year) if extracted_year else '[YEAR]'}/10-K")
        else:
            print(f"No filing found for accession number {ACCESSION_TO_CHECK}.")
        print("\n")

    except psycopg2.Error as db_err:
        print(f"Database error occurred: {db_err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()
        print("PostgreSQL connection closed.")

if __name__ == "__main__":
    # Create a directory for these utility scripts if it doesn't exist
    # dev_utils_dir = os.path.join(PROJECT_ROOT, "dev_utils")
    # if not os.path.exists(dev_utils_dir):
    #     try:
    #         os.makedirs(dev_utils_dir)
    #         print(f"Created directory: {dev_utils_dir}")
    #     except OSError as e:
    #         print(f"Error creating directory {dev_utils_dir}: {e}")
    main() 