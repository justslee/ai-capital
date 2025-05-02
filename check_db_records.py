import psycopg2
import sys
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load .env file from the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    print(f"Loading environment variables from: {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

DATABASE_URL = os.getenv("DATABASE_URL")
TICKER_TO_CHECK = "AAPL"

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables.")
    sys.exit(1)

# Parse the DATABASE_URL
# Note: psycopg2 doesn't directly use the +asyncpg part
parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))

conn_params = {
    'dbname': parsed_url.path[1:], # Remove leading /
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require' # Assuming RDS requires SSL
}

tables_to_check = ["income_statements", "balance_sheets", "cash_flows"]

conn = None
cur = None

try:
    print(f"Connecting to database '{conn_params['dbname']}' at {conn_params['host']}...")
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    print("Connection successful!")

    for table in tables_to_check:
        print(f"\n--- Checking table: {table} for ticker: {TICKER_TO_CHECK} ---")
        query = f"SELECT COUNT(*) FROM {table} WHERE ticker = %s;"
        cur.execute(query, (TICKER_TO_CHECK,))
        count = cur.fetchone()[0]
        print(f"Found {count} record(s).")

        if count > 0:
            # Fetch and print the first 3 records (or fewer if less than 3 exist)
            query_data = f"SELECT * FROM {table} WHERE ticker = %s LIMIT 3;"
            cur.execute(query_data, (TICKER_TO_CHECK,))
            records = cur.fetchall()
            print(f"First {len(records)} record(s):")
            # Get column names
            colnames = [desc[0] for desc in cur.description]
            print(", ".join(colnames))
            for record in records:
                # Print record values, converting None to 'NULL' for clarity
                print(", ".join([str(val) if val is not None else 'NULL' for val in record]))

except Exception as e:
    print(f"\nError during database check: {e}")
    sys.exit(1)

finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
    print("\nDatabase connection closed.") 