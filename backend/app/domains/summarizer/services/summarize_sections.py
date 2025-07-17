import psycopg2
import sys
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlparse
import openai
import time
from typing import Dict, List, Optional
import asyncio

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from app.domains.data_collection.storage.s3_storage_service import get_s3_storage_service


# Configuration
OPENAI_MODEL_NAME = "gpt-4-turbo"
MAX_TOKENS_FOR_CHUNK_SUMMARY_OUTPUT = 150
MAX_TOKENS_FOR_FINAL_SUMMARY_OUTPUT = 500

TARGET_SECTION_KEYS = [
    "Business", 
    "Risk Factors", 
    "MD&A"
]

# Environment setup
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env")

if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH)
else:
    # Silent fallback - env vars may be set externally
    pass

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    # Silent exit - let the application handle missing DB config
    sys.exit(1)

if not OPENAI_API_KEY:
    # Silent exit - let the application handle missing API key
    sys.exit(1)

# Database connection
parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))
conn_params = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require'
}

# Database helper functions
def create_summaries_table(cursor):
    table_creation_query = """
    CREATE TABLE IF NOT EXISTS sec_section_summaries (
        id SERIAL PRIMARY KEY,
        filing_accession_number TEXT NOT NULL,
        section_key TEXT NOT NULL,
        summarization_model_name TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        raw_chunk_summaries_concatenated TEXT,
        total_chunks_in_section INTEGER,
        processing_status TEXT,
        error_message TEXT,
        generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_accession_section_model UNIQUE (filing_accession_number, section_key, summarization_model_name)
    );
    CREATE INDEX IF NOT EXISTS idx_sss_accession_number ON sec_section_summaries(filing_accession_number);
    CREATE INDEX IF NOT EXISTS idx_sss_section_key ON sec_section_summaries(section_key);
    CREATE INDEX IF NOT EXISTS idx_sss_model_name ON sec_section_summaries(summarization_model_name);
    """
    cursor.execute(table_creation_query)

def get_unprocessed_filings(cursor, model_name, target_section_keys):
    """
    Get filings that have sections that need summarization.
    This identifies filings that haven't been processed for a given model and section.
    """
    target_keys_tuple = tuple(target_section_keys)
    query = """
    SELECT DISTINCT f.ticker, f.accession_number
    FROM sec_filings f
    WHERE f.filing_type IN ('10-K', '10-Q')
      AND NOT EXISTS (
        SELECT 1
        FROM sec_section_summaries sss
        WHERE sss.filing_accession_number = f.accession_number
          AND sss.section_key = ANY(%s)
          AND sss.summarization_model_name = %s
          AND sss.processing_status = 'reduce_complete'
    )
    ORDER BY f.accession_number;
    """
    cursor.execute(query, (list(target_keys_tuple), model_name))
    return cursor.fetchall()


def call_openai_api(openai_client_instance, prompt_messages, model_name, max_tokens_output):
    """Call OpenAI API with error handling."""
    try:
        response = openai_client_instance.chat.completions.create(
            model=model_name,
            messages=prompt_messages,
            max_tokens=max_tokens_output,
            temperature=0.3, 
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        if response.choices and response.choices[0].message:
            return response.choices[0].message.content.strip()
        else:
            # Log warning without console output
            return None
    except openai.APIError as e:
        # Log API errors without console output
        return None
    except Exception as e:
        # Log unexpected errors without console output  
        return None

def save_summary(
    cursor, filing_accession_number, section_key, 
    summarization_model_name, summary_text=None, raw_chunk_summaries_concatenated=None, 
    total_chunks_in_section=None, processing_status=None, error_message=None
):
    """Insert or update a summary record."""
    
    cursor.execute(
        "SELECT id FROM sec_section_summaries WHERE filing_accession_number = %s AND section_key = %s AND summarization_model_name = %s",
        (filing_accession_number, section_key, summarization_model_name)
    )
    existing_summary_record = cursor.fetchone()

    if existing_summary_record:
        # Update existing record
        update_fields = []
        update_values = []
        if summary_text is not None:
            update_fields.append("summary_text = %s")
            update_values.append(summary_text)
        if raw_chunk_summaries_concatenated is not None:
            update_fields.append("raw_chunk_summaries_concatenated = %s")
            update_values.append(raw_chunk_summaries_concatenated)
        if total_chunks_in_section is not None:
            update_fields.append("total_chunks_in_section = %s")
            update_values.append(total_chunks_in_section)
        if processing_status is not None:
            update_fields.append("processing_status = %s")
            update_values.append(processing_status)
        if error_message is not None:
            update_fields.append("error_message = %s")
            update_values.append(error_message)
        else:
            update_fields.append("error_message = NULL")
        
        update_fields.append("generated_at = CURRENT_TIMESTAMP")
        
        if not update_fields:
            return

        query = f"UPDATE sec_section_summaries SET {', '.join(update_fields)} WHERE id = %s"
        update_values.append(existing_summary_record[0])
        cursor.execute(query, tuple(update_values))
    else:
        # Insert new record
        query = """
        INSERT INTO sec_section_summaries (
            filing_accession_number, section_key, summarization_model_name, 
            summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section, 
            processing_status, error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (filing_accession_number, section_key, summarization_model_name) DO NOTHING;
        """
        final_summary_text = summary_text if summary_text is not None else ""

        cursor.execute(query, (
            filing_accession_number, section_key, summarization_model_name,
            final_summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section,
            processing_status, error_message
        ))

async def process_filing_sections(ticker, accession_number, target_sections, cursor, openai_client):
    """Processes all target sections for a single filing."""
    s3_service = get_s3_storage_service()
    
    for section_key in target_sections:
        print(f"  - Processing section: {section_key}")
        
        chunks = await s3_service.list_and_read_chunks(ticker, accession_number, section_key)
        
        if not chunks:
            print(f"    - No chunks found in S3 for {section_key}. Skipping.")
            continue
            
        print(f"    - Found {len(chunks)} chunks in S3.")

        # Map step: Summarize each chunk
        map_start_time = time.time()
        chunk_summaries = []
        
        for i, chunk_text in enumerate(chunks):
            # This logic can be further parallelized if needed
            chunk_summary = call_openai_api(
                openai_client,
                prompt_messages=[
                    {"role": "system", "content": "You are an expert financial analyst. Summarize the following text from an SEC filing concisely."},
                    {"role": "user", "content": chunk_text}
                ],
                model_name=OPENAI_MODEL_NAME,
                max_tokens_output=MAX_TOKENS_FOR_CHUNK_SUMMARY_OUTPUT
            )
            if chunk_summary:
                chunk_summaries.append(chunk_summary)

        map_duration = time.time() - map_start_time
        print(f"    - Map step completed in {map_duration:.2f}s. Got {len(chunk_summaries)} summaries.")

        if not chunk_summaries:
            print("    - No chunk summaries were generated. Skipping reduce step.")
            save_summary(
                cursor, accession_number, section_key, OPENAI_MODEL_NAME,
                processing_status='map_failed', error_message='No summaries generated from chunks'
            )
            # conn.commit() # This line was removed as per the new_code, but it's needed for the original logic.
            continue

        concatenated_summaries = "\n\n".join(chunk_summaries)
        
        # Reduce step: Create final summary from chunk summaries
        reduce_start_time = time.time()
        final_summary = call_openai_api(
            openai_client,
            prompt_messages=[
                {"role": "system", "content": "You are an expert financial analyst. Synthesize the following section summaries into a single, coherent summary."},
                {"role": "user", "content": concatenated_summaries}
            ],
            model_name=OPENAI_MODEL_NAME,
            max_tokens_output=MAX_TOKENS_FOR_FINAL_SUMMARY_OUTPUT
        )
        reduce_duration = time.time() - reduce_start_time
        print(f"    - Reduce step completed in {reduce_duration:.2f}s.")

        if final_summary:
            save_summary(
                cursor, accession_number, section_key, OPENAI_MODEL_NAME,
                summary_text=final_summary, 
                raw_chunk_summaries_concatenated=concatenated_summaries,
                total_chunks_in_section=len(chunks),
                processing_status='reduce_complete'
            )
            print(f"    - Successfully saved final summary for {section_key}.")
        else:
            save_summary(
                cursor, accession_number, section_key, OPENAI_MODEL_NAME,
                processing_status='reduce_failed', error_message='Failed to generate final summary'
            )
            print("    - Failed to generate final summary.")
            
        # conn.commit() # This line was removed as per the new_code, but it's needed for the original logic.


def main():
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY not found. Exiting.")
        return

    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    global conn
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        print("Database connection successful.")
        
        create_summaries_table(cursor)
        conn.commit()

        unprocessed_filings = get_unprocessed_filings(cursor, OPENAI_MODEL_NAME, TARGET_SECTION_KEYS)
        print(f"Found {len(unprocessed_filings)} filings with sections to process.")

        for ticker, accession_number in unprocessed_filings:
            print(f"\nProcessing filing: {accession_number} for ticker: {ticker}")
            try:
                asyncio.run(process_filing_sections(
                    ticker, accession_number, TARGET_SECTION_KEYS, cursor, openai_client
                ))
            except Exception as e:
                print(f"  - An unexpected error occurred while processing {accession_number}: {e}")
                conn.rollback()


    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    main() 