import psycopg2
import sys
import os
import json # For serializing list to TEXT
from dotenv import load_dotenv
from urllib.parse import urlparse
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec, PodSpec # Updated import
import time

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2' # Or any other SentenceTransformer model
VECTOR_DIMENSION = 384 
BATCH_SIZE = 32 # Number of chunks to process at a time

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "pcsk_2Ps7dw_JbdnQnKkzKkoJ9Syc8Q4tW5QEGCJ8w2y7iNuW6a7UdvphPkj4kVqgJoHQksNYUJ")
# 중요: REPLACE "gcp-starter" WITH YOUR ACTUAL PINECONE ENVIRONMENT
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter") 
PINECONE_INDEX_NAME = "sec-filings"

# Load .env file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Assuming .env is in project root
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    print(f"Loaded .env from: {DOTENV_PATH}")
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}. Script might fail if DATABASE_URL is not set.")

# Re-check Pinecone API Key from .env if not hardcoded directly above
if PINECONE_API_KEY == "pcsk_2Ps7dw_JbdnQnKkzKkoJ9Syc8Q4tW5QEGCJ8w2y7iNuW6a7UdvphPkj4kVqgJoHQksNYUJ" and os.getenv("PINECONE_API_KEY"):
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if PINECONE_ENVIRONMENT == "gcp-starter" and os.getenv("PINECONE_ENVIRONMENT"):
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables.")
    sys.exit(1)
if not PINECONE_API_KEY:
    print("Error: PINECONE_API_KEY not found in environment variables or script.")
    sys.exit(1)
if not PINECONE_ENVIRONMENT:
    print("Error: PINECONE_ENVIRONMENT not found in environment variables or script. Please set it.")
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

# --- Main Script Logic ---
def main():
    print(f"Loading SentenceTransformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    print("Model loaded.")

    # Initialize Pinecone
    print(f"Initializing Pinecone with environment: {PINECONE_ENVIRONMENT}...")
    pinecone = Pinecone(api_key=PINECONE_API_KEY) #, environment=PINECONE_ENVIRONMENT) <- environment not needed for new client init
    
    # Corrected way to check for index existence
    index_list_response = pinecone.list_indexes()
    # Extract names from the IndexModel objects in the list
    existing_index_names = [index.name for index in index_list_response] if index_list_response else []
    
    if PINECONE_INDEX_NAME not in existing_index_names:
        print(f"Pinecone index '{PINECONE_INDEX_NAME}' not found. Creating it...")
        # Serverless is generally easier to start with, change if using Pod-based
        pinecone.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=VECTOR_DIMENSION,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1') # Choose your preferred cloud/region
            # For Pod-based:
            # spec=PodSpec(environment=PINECONE_ENVIRONMENT, pod_type="p1.x1", pods=1)
        )
        # Wait for index to be ready
        while not pinecone.describe_index(PINECONE_INDEX_NAME).status['ready']:
            print("Waiting for index to be ready...")
            time.sleep(5)
        print(f"Pinecone index '{PINECONE_INDEX_NAME}' created and ready.")
    else:
        print(f"Found existing Pinecone index: '{PINECONE_INDEX_NAME}'.")

    index = pinecone.Index(PINECONE_INDEX_NAME)
    print(f"Connected to Pinecone index: '{PINECONE_INDEX_NAME}'.")
    print(f"Index stats: {index.describe_index_stats()}")

    conn = None
    cur = None

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print(f"Connected to PostgreSQL database '{conn_params['dbname']}'.")

        # Fetch all chunks with their metadata from sec_filing_section_chunks
        # We will process all chunks and upsert them. Pinecone handles duplicates by overwriting.
        fetch_chunks_query = """
        SELECT 
            sfc.id, 
            sfc.filing_accession_number, 
            sfc.company_name, 
            sfc.ticker, 
            sfc.form_type, 
            sfc.filing_year, 
            sfc.section_key, 
            sfc.subsection_title, 
            sfc.chunk_order_in_section, 
            sfc.char_count, 
            sfc.is_table, 
            sfc.is_footnote,
            sfc.chunk_text
        FROM sec_filing_section_chunks sfc
        ORDER BY sfc.id; 
        """
        print("Executing query to fetch all chunks from sec_filing_section_chunks...")
        cur.execute(fetch_chunks_query)
        all_db_records = cur.fetchall()
        total_to_process = len(all_db_records)
        print(f"Total chunks fetched from database: {total_to_process}")

        if total_to_process == 0:
            print("No chunks found in sec_filing_section_chunks to process.")
            return

        current_record_index = 0
        total_chunks_upserted_to_pinecone = 0
        
        while current_record_index < total_to_process:
            batch_end_index = min(current_record_index + BATCH_SIZE, total_to_process)
            records_batch = all_db_records[current_record_index:batch_end_index]
            
            if not records_batch:
                break 
            
            print(f"Processing batch: {len(records_batch)} chunks (DB index {current_record_index} to {batch_end_index-1}).")
            
            chunk_texts_for_embedding = [r[12] for r in records_batch] # chunk_text is the 13th item (0-indexed)
            
            if not chunk_texts_for_embedding:
                print("No text found in fetched batch, skipping.")
                current_record_index += len(records_batch)
                continue

            print(f"Generating embeddings for {len(chunk_texts_for_embedding)} texts (Batch {total_chunks_upserted_to_pinecone // BATCH_SIZE + 1})...")
            embeddings = model.encode(chunk_texts_for_embedding, show_progress_bar=True)
            print("Embeddings generated.")

            pinecone_batch_to_upsert = []
            for i, db_record in enumerate(records_batch):
                chunk_id = str(db_record[0]) # Pinecone ID must be string
                embedding_list = embeddings[i].tolist()
                
                metadata = {
                    "filing_accession_number": db_record[1] or "",
                    "company_name": db_record[2] or "",
                    "ticker": db_record[3] or "",
                    "form_type": db_record[4] or "",
                    "filing_year": db_record[5], # Assuming this is an INTEGER and non-nullable, or handle if it can be None
                    "section_key": db_record[6] or "",
                    "subsection_title": db_record[7] or "", # Handle None by converting to empty string
                    "chunk_order_in_section": db_record[8], # Assuming INTEGER, non-nullable
                    "char_count": db_record[9], # Assuming INTEGER, non-nullable
                    "is_table": bool(db_record[10]),
                    "is_footnote": bool(db_record[11]),
                    "original_chunk_text": db_record[12] or "" # Ensure text is not None
                }
                pinecone_batch_to_upsert.append((chunk_id, embedding_list, metadata))
            
            if pinecone_batch_to_upsert:
                print(f"Upserting {len(pinecone_batch_to_upsert)} vectors to Pinecone...")
                index.upsert(vectors=pinecone_batch_to_upsert)
                total_chunks_upserted_to_pinecone += len(pinecone_batch_to_upsert)
                print(f"Upserted batch to Pinecone. Total upserted so far: {total_chunks_upserted_to_pinecone} out of {total_to_process}")
            
            current_record_index += len(records_batch)

        print(f"\nFinished processing. Total chunks upserted to Pinecone: {total_chunks_upserted_to_pinecone} out of {total_to_process}")
        print(f"Final Pinecone index stats: {index.describe_index_stats()}")

    except psycopg2.Error as db_err:
        print(f"\nDatabase error occurred: {db_err}")
        import traceback
        traceback.print_exc()
        if conn: conn.rollback()
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
        if conn: conn.rollback() # Should rollback for general errors too if DB conn involved
    finally:
        if cur: cur.close()
        if conn: conn.close()
        print("\nPostgreSQL connection closed.")
        # Pinecone client does not need explicit close typically

if __name__ == "__main__":
    # The specific "embeddings/embeddings" subdirectory creation is no longer strictly needed by this script
    # as it doesn't save files there, but keeping it doesn't harm.
    embeddings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "embeddings")
    if not os.path.exists(embeddings_dir):
        try:
            os.makedirs(embeddings_dir)
            print(f"Created directory: {embeddings_dir}")
        except OSError as e:
            print(f"Error creating directory {embeddings_dir}: {e}")
    
    main() 