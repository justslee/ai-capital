import psycopg2
import sys
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# --- Load .env and set API Keys & DB URL ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    print(f"Loading .env file from: {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}. Ensure DB URL is set.")

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
    'port': parsed_url.port,
    'sslmode': 'require' 
}

FILING_ACCESSION_TO_INSPECT = '0000320193-24-000123' # AAPL example
MODEL_TO_INSPECT = 'gpt-3.5-turbo-0125'

def main():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print(f"Connected to PostgreSQL database '{conn_params['dbname']}'.\n")

        # 1. Check section_key values in sec_filing_sections for the specific filing
        print(f"--- Section keys in 'sec_filing_sections' for accession {FILING_ACCESSION_TO_INSPECT} ---")
        query_sections = """
        SELECT DISTINCT section_key 
        FROM sec_filing_sections 
        WHERE filing_accession_number = %s 
        ORDER BY section_key;
        """
        cur.execute(query_sections, (FILING_ACCESSION_TO_INSPECT,))
        sections = cur.fetchall()
        if sections:
            for row in sections:
                print(f"  - '{row[0]}'")
        else:
            print(f"No sections found for accession {FILING_ACCESSION_TO_INSPECT}.")
        print("\n")

        # 2. Check existing entries in sec_section_summaries for the specific filing and model
        print(f"--- Entries in 'sec_section_summaries' for accession {FILING_ACCESSION_TO_INSPECT} and model {MODEL_TO_INSPECT} ---")
        query_summaries = """
        SELECT sss.id, sss.section_db_id, sss.section_key, sss.summarization_model_name, sss.processing_status, sss.error_message
        FROM sec_section_summaries sss
        WHERE sss.filing_accession_number = %s AND sss.summarization_model_name = %s
        ORDER BY sss.section_key;
        """
        cur.execute(query_summaries, (FILING_ACCESSION_TO_INSPECT, MODEL_TO_INSPECT))
        summaries = cur.fetchall()
        if summaries:
            for row in summaries:
                print(f"  Summary ID: {row[0]}, Section DB ID: {row[1]}, Key: '{row[2]}', Model: '{row[3]}', Status: '{row[4]}', Error: {row[5]}")
        else:
            print(f"No summaries found for accession {FILING_ACCESSION_TO_INSPECT} and model {MODEL_TO_INSPECT}.")
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
    main() 