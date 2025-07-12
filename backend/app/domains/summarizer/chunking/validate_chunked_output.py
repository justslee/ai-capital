import psycopg2
import sys
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load .env file
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    # Try loading from parent directory if not in current test/ directory
    # This is useful if .env is in the project root
    PARENT_DOTENV_PATH = os.path.join(os.path.dirname(PROJECT_ROOT), '.env')
    if os.path.exists(PARENT_DOTENV_PATH):
        load_dotenv(dotenv_path=PARENT_DOTENV_PATH)
        print(f"Loaded .env from project root: {PARENT_DOTENV_PATH}")
    else:
        print(f"Warning: .env file not found at {DOTENV_PATH} or {PARENT_DOTENV_PATH}")

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Configuration for Validation ---
TICKER_TO_VALIDATE = "AAPL"  # Change this to the ticker you want to inspect
# Specify accession number if you want a specific filing, otherwise None for latest
ACCESSION_NUMBER_TO_VALIDATE = "0000320193-24-000123" # Or None to fetch latest for the ticker

# Sections to prioritize for display, and number of chunks to show from them
SECTIONS_TO_FOCUS_ON = {
    "Risk Factors": 5, # Show 5 chunks from Risk Factors
    "MD&A": 5,         # Show 5 chunks from MD&A
    "Business": 3      # Show 3 chunks from Business
}
MAX_OTHER_CHUNKS_TO_SHOW = 5 # Max number of chunks to show from other sections combined
# -------------------------------------

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables.")
    sys.exit(1)

parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))
conn_params = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require'
}

conn = None
cur = None

def estimate_word_count(text_content):
    if not text_content: return 0
    return len(text_content.split())

try:
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    print(f"Connected to database '{conn_params['dbname']}'.")



    target_accession_number = ACCESSION_NUMBER_TO_VALIDATE

    if not target_accession_number:
        print(f"Querying latest filing accession number for ticker: {TICKER_TO_VALIDATE}")
        latest_filing_query = """ 
        SELECT accession_number 
        FROM sec_filings 
        WHERE ticker = %s 
        ORDER BY filing_date DESC 
        LIMIT 1;
        """
        cur.execute(latest_filing_query, (TICKER_TO_VALIDATE.upper(),))
        record = cur.fetchone()
        if not record:
            print(f"No filings found for ticker {TICKER_TO_VALIDATE} in 'sec_filings' table.")
            sys.exit(0)
        target_accession_number = record[0]
        print(f"Latest filing accession number for {TICKER_TO_VALIDATE} is: {target_accession_number}")
    else:
        print(f"Using specified accession number: {target_accession_number} for ticker {TICKER_TO_VALIDATE}")

    print(f"\nFetching chunks for Ticker: {TICKER_TO_VALIDATE}, Accession: {target_accession_number}\n")

    chunks_to_display = []
    processed_chunk_ids = set()

    # Fetch focused sections first
    for section_key, num_chunks_to_fetch in SECTIONS_TO_FOCUS_ON.items():
        query = """
        SELECT id, filing_accession_number, section_db_id, company_name, ticker, form_type, 
               filing_year, section_key, subsection_title, chunk_order_in_section, 
               chunk_text, char_count, is_table, is_footnote
        FROM sec_filing_section_chunks
        WHERE filing_accession_number = %s AND section_key = %s
        ORDER BY chunk_order_in_section
        LIMIT %s;
        """
        cur.execute(query, (target_accession_number, section_key, num_chunks_to_fetch))
        fetched_chunks = cur.fetchall()
        for chunk_row in fetched_chunks:
            if chunk_row[0] not in processed_chunk_ids:
                chunks_to_display.append(chunk_row)
                processed_chunk_ids.add(chunk_row[0])
    
    # Fetch a few other chunks
    if MAX_OTHER_CHUNKS_TO_SHOW > 0:
        other_sections_query = """
        SELECT id, filing_accession_number, section_db_id, company_name, ticker, form_type, 
               filing_year, section_key, subsection_title, chunk_order_in_section, 
               chunk_text, char_count, is_table, is_footnote
        FROM sec_filing_section_chunks
        WHERE filing_accession_number = %s 
          AND section_key NOT IN %s
        ORDER BY section_key, chunk_order_in_section
        LIMIT %s;
        """ 
        # Create a tuple of section keys already fetched for the NOT IN clause
        focused_section_keys_tuple = tuple(SECTIONS_TO_FOCUS_ON.keys())
        if not focused_section_keys_tuple: # Handle case where SECTIONS_TO_FOCUS_ON might be empty
            # If there are no focused sections, we don't want an empty `NOT IN ()` which is invalid SQL
            # or `NOT IN ('',)` which might unintentionally exclude sections with empty key (though unlikely here)
            # A better approach if no focused_section_keys is to not have the NOT IN clause or fetch all.
            # For now, if it's empty, this part of query might not run or fetch anything, 
            # which is acceptable if MAX_OTHER_CHUNKS_TO_SHOW > 0 but no focused keys.
            # However, SECTIONS_TO_FOCUS_ON is not empty in current config.
            # To prevent SQL error with an empty tuple for NOT IN, ensure it has at least one (dummy) value if it were possible to be empty.
            focused_section_keys_tuple = ('dummy_non_existent_key',)
            
        cur.execute(other_sections_query, (target_accession_number, focused_section_keys_tuple, MAX_OTHER_CHUNKS_TO_SHOW))
        fetched_chunks = cur.fetchall()
        for chunk_row in fetched_chunks:
            if chunk_row[0] not in processed_chunk_ids:
                chunks_to_display.append(chunk_row)
                processed_chunk_ids.add(chunk_row[0])

    if not chunks_to_display:
        print(f"No chunks found in 'sec_filing_section_chunks' for accession number: {target_accession_number}")
        sys.exit(0)

    print(f"Displaying {len(chunks_to_display)} sample chunks for validation:\n")
    print("=" * 80)

    for i, chunk_data in enumerate(chunks_to_display):
        (
            chunk_id, acc_num, sec_db_id, comp_name, tick, f_type, f_year, 
            s_key, sub_title, order, text, chars, is_tab, is_foot
        ) = chunk_data

        word_count = estimate_word_count(text)

        print(f"CHUNK {i+1} / {len(chunks_to_display)}")
        print("-" * 20)
        print(f"  Chunk ID (DB):         {chunk_id}")
        print(f"  Filing Accession No:   {acc_num}")
        print(f"  Company:               {comp_name} ({tick})")
        print(f"  Form Type / Year:      {f_type} / {f_year}")
        print(f"  Parent Section DB ID:  {sec_db_id}")
        print(f"  Section Key:           {s_key}")
        print(f"  Subsection Title:      {sub_title if sub_title else 'N/A'}")
        print(f"  Order in Section:      {order}")
        print(f"  Is Table:              {is_tab}")
        print(f"  Is Footnote:           {is_foot}")
        print(f"  Character Count:       {chars:,}")
        print(f"  Estimated Word Count:  ~{word_count:,}")
        print("-" * 20 + " TEXT " + "-" * 20)
        print(text)
        print("=" * 80 + "\n")

except psycopg2.Error as db_error:
    print(f"Database query error: {db_error}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    import traceback
    traceback.print_exc()

finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
    print("\nDatabase connection closed.") 