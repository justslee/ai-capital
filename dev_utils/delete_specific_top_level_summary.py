import psycopg2
import sys
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# --- Configuration for deletion ---
ACCESSION_TO_DELETE = "0000320193-24-000123"
MODEL_NAME_TO_DELETE = "gpt-3.5-turbo-0125" # Model used for the summary to be deleted
SOURCE_KEYS_TO_DELETE = sorted(["Business", "Risk Factors", "MD&A"]) # Must match how it's stored

# --- Load .env and set DB URL ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}.")
    sys.exit(1)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env. Exiting.")
    sys.exit(1)

# --- Database Connection Parameters ---
parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))
conn_params = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require'
}

def main():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print(f"Connected to PostgreSQL database '{conn_params['dbname']}'.")

        delete_query = """
        DELETE FROM sec_filing_top_level_summaries
        WHERE filing_accession_number = %s
          AND summarization_model_name = %s
          AND source_section_keys = %s;
        """
        
        cur.execute(delete_query, (ACCESSION_TO_DELETE, MODEL_NAME_TO_DELETE, SOURCE_KEYS_TO_DELETE))
        deleted_rows = cur.rowcount
        conn.commit()

        if deleted_rows > 0:
            print(f"Successfully deleted {deleted_rows} top-level summary record(s) for accession {ACCESSION_TO_DELETE}, model {MODEL_NAME_TO_DELETE}, and sources {SOURCE_KEYS_TO_DELETE}.")
        else:
            print(f"No top-level summary records found matching accession {ACCESSION_TO_DELETE}, model {MODEL_NAME_TO_DELETE}, and sources {SOURCE_KEYS_TO_DELETE} for deletion.")

    except psycopg2.Error as db_err:
        print(f"Database error occurred: {db_err}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("PostgreSQL connection closed.")

if __name__ == "__main__":
    main() 