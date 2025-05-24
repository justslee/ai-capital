import psycopg2
import sys
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlparse
import openai # Added for OpenAI API
import time # For potential delays or retries

# --- Configuration ---
OPENAI_MODEL_NAME = "gpt-4-turbo" # Updated to GPT-4 for higher quality summaries
# For token counting and managing context length - rough estimate, can be refined
# Typical average token length is ~4 chars. Max context for gpt-4-turbo is 128k tokens.
# Max output is 4096 tokens.
MAX_TOKENS_FOR_CHUNK_SUMMARY_OUTPUT = 150 # Target length for individual chunk summaries
MAX_TOKENS_FOR_FINAL_SUMMARY_OUTPUT = 500  # Target length for the final section summary

TARGET_SECTION_KEYS = [
    "Business", 
    "Risk Factors", 
    "MD&A" 
    # "Item 8. Financial Statements and Supplementary Data" # Can add later if needed, ensure key matches DB
]

# --- Load .env and set API Keys & DB URL ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    print(f"Loading .env file from: {DOTENV_PATH}")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}. Ensure environment variables are set.")

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "aws-us-east-1")

# Critical checks
if not DATABASE_URL:
    print("Error: DATABASE_URL not found. Please set it in .env or as an environment variable.")
    sys.exit(1)
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found. Please set it in .env or as an environment variable.")
    sys.exit(1)

# Note: Global openai.api_key = OPENAI_API_KEY is not needed for new client versions if key is passed to constructor

# --- Database Connection Parameters ---
parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))
conn_params = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require' # Assuming SSL is required as per previous setups
}

# --- Database Helper Functions ---
def create_summaries_table(cursor):
    table_creation_query = """
    CREATE TABLE IF NOT EXISTS sec_section_summaries (
        id SERIAL PRIMARY KEY,
        section_db_id INTEGER NOT NULL UNIQUE REFERENCES sec_filing_sections(id) ON DELETE CASCADE,
        filing_accession_number TEXT NOT NULL,
        section_key TEXT NOT NULL,
        summarization_model_name TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        raw_chunk_summaries_concatenated TEXT,
        total_chunks_in_section INTEGER,
        processing_status TEXT, -- e.g., pending_map, map_complete, reduce_complete, error
        error_message TEXT,
        generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_section_model UNIQUE (section_db_id, summarization_model_name)
    );
    CREATE INDEX IF NOT EXISTS idx_sss_section_db_id ON sec_section_summaries(section_db_id);
    CREATE INDEX IF NOT EXISTS idx_sss_accession_number ON sec_section_summaries(filing_accession_number);
    CREATE INDEX IF NOT EXISTS idx_sss_section_key ON sec_section_summaries(section_key);
    CREATE INDEX IF NOT EXISTS idx_sss_model_name ON sec_section_summaries(summarization_model_name);
    """
    cursor.execute(table_creation_query)
    print("'sec_section_summaries' table checked/created successfully.")

def get_unprocessed_sections(cursor, model_name, target_section_keys):
    """Fetches sections that have not yet been successfully summarized (reduce_complete)
       or have encountered an error, or are in an intermediate state.
    """
    target_keys_tuple = tuple(target_section_keys)
    
    query = """
    SELECT fs.id, fs.filing_accession_number, fs.section_key
    FROM sec_filing_sections fs
    LEFT JOIN sec_section_summaries sss ON fs.id = sss.section_db_id AND sss.summarization_model_name = %s
    WHERE fs.section_key IN %s 
      AND (sss.id IS NULL OR sss.processing_status IS NULL OR sss.processing_status NOT IN ('reduce_complete'))
    ORDER BY fs.filing_accession_number, fs.id; -- Process systematically
    """
    cursor.execute(query, (model_name, target_keys_tuple))
    sections = cursor.fetchall()
    print(f"Found {len(sections)} sections to process/re-process for model '{model_name}' matching target keys.")
    return sections

def get_chunks_for_section(cursor, section_db_id):
    """Fetches all text chunks for a given section_db_id, ordered correctly."""
    query = """
    SELECT chunk_text 
    FROM sec_filing_section_chunks
    WHERE section_db_id = %s
    ORDER BY chunk_order_in_section ASC;
    """
    cursor.execute(query, (section_db_id,))
    chunks = [row[0] for row in cursor.fetchall()] # Get a list of chunk_text
    print(f"Fetched {len(chunks)} chunks for section_db_id {section_db_id}.")
    return chunks

# --- OpenAI Helper Function ---
def call_openai_api(openai_client_instance, prompt_messages, model_name, max_tokens_output):
    """Calls the OpenAI Chat Completions API using the provided client instance."""
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
            print("Warning: OpenAI API response did not contain expected choices or message content.")
            print(f"Full API Response: {response}")
            return None
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during OpenAI API call: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Database Save Function ---
def save_summary(
    cursor, section_db_id, filing_accession_number, section_key, 
    summarization_model_name, summary_text=None, raw_chunk_summaries_concatenated=None, 
    total_chunks_in_section=None, processing_status=None, error_message=None
):
    """Inserts or updates a summary in the sec_section_summaries table."""
    
    # Check if a record already exists to decide on INSERT or UPDATE for some fields
    # The main path should be INSERT for new summaries due to get_unprocessed_sections logic
    # but this provides robustness for updates of status/errors.
    cursor.execute(
        "SELECT id FROM sec_section_summaries WHERE section_db_id = %s AND summarization_model_name = %s",
        (section_db_id, summarization_model_name)
    )
    existing_summary_record = cursor.fetchone()

    if existing_summary_record:
        # Update existing record (primarily for status, errors, or if reprocessing)
        # Only update fields that are provided (not None)
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
        else: # Clear error message if not provided during a successful update
            update_fields.append("error_message = NULL")
        
        update_fields.append("generated_at = CURRENT_TIMESTAMP") # Always update timestamp
        
        if not update_fields: # Nothing to update besides timestamp, maybe skip
            print(f"No fields to update for section_db_id {section_db_id}, model {summarization_model_name}. Only timestamp would change.")
            return

        query = f"UPDATE sec_section_summaries SET {', '.join(update_fields)} WHERE id = %s"
        update_values.append(existing_summary_record[0])
        cursor.execute(query, tuple(update_values))
        print(f"Updated summary record for section_db_id {section_db_id}, model {summarization_model_name}.")
    else:
        # Insert new record
        # if summary_text is None and processing_status not in ['pending_map', 'error']:
        #      # If it's supposed to be a complete summary, text should be there unless it's an initial status set or error
        #     print(f"Warning: summary_text is None for a new summary record for section {section_db_id} with status {processing_status}. Setting to empty string.")
        #     summary_text = "" # Or handle as error, depending on desired strictness
        
        query = """
        INSERT INTO sec_section_summaries (
            section_db_id, filing_accession_number, section_key, summarization_model_name, 
            summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section, 
            processing_status, error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (section_db_id, summarization_model_name) DO NOTHING; -- Should not hit due to prior check, but as safety
        """
        # Ensure summary_text is always non-null for the INSERT statement
        final_summary_text = summary_text if summary_text is not None else ""

        cursor.execute(query, (
            section_db_id, filing_accession_number, section_key, summarization_model_name,
            final_summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section,
            processing_status, error_message
        ))
        print(f"Inserted new summary record for section_db_id {section_db_id}, model {summarization_model_name} with status '{processing_status}'.")

# --- Main Logic ---
def main():
    print("Starting section summarization process...")
    
    conn = None
    cur = None
    
    # Initialize OpenAI client by passing the API key directly
    if not OPENAI_API_KEY:
        print("CRITICAL: OPENAI_API_KEY is None even after checks. This should not happen.")
        sys.exit(1)
    print("Initializing OpenAI client...")
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    print("OpenAI client initialized.")

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print(f"Connected to PostgreSQL database '{conn_params['dbname']}'.")

        create_summaries_table(cur)
        conn.commit()

        unprocessed_sections = get_unprocessed_sections(cur, OPENAI_MODEL_NAME, TARGET_SECTION_KEYS)

        if not unprocessed_sections:
            print("No new sections to process. Exiting.")
            return

        for sec_id, accession_no, sec_key in unprocessed_sections:
            print(f"\nProcessing section: ID={sec_id}, Accession={accession_no}, Key='{sec_key}'")
            
            save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                         processing_status='pending_map')
            conn.commit()

            chunks = get_chunks_for_section(cur, sec_id)
            if not chunks:
                print(f"No chunks found for section ID {sec_id}. Skipping summarization.")
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             processing_status='error', error_message='No chunks found for section', total_chunks_in_section=0)
                conn.commit()
                continue

            chunk_summaries = []
            map_errors = 0
            print(f"Starting Map step for {len(chunks)} chunks...")
            for i, chunk_text in enumerate(chunks):
                map_prompt_messages = [
                    {"role": "system", "content": "You are an expert at summarizing financial document segments."},
                    {"role": "user", "content": f"The following is a text segment from the '{sec_key}' section of an SEC 10-K filing. Briefly summarize the main points or key information contained *only* in this specific segment in 1-2 sentences: \n\nText Segment:\n{chunk_text}"}
                ]
                print(f"  Summarizing chunk {i+1}/{len(chunks)} (length: {len(chunk_text)} chars)... ") 
                if i > 0 and i % 10 == 0: time.sleep(1) 

                chunk_summary = call_openai_api(openai_client, map_prompt_messages, OPENAI_MODEL_NAME, MAX_TOKENS_FOR_CHUNK_SUMMARY_OUTPUT)
                if chunk_summary:
                    chunk_summaries.append(chunk_summary)
                else:
                    map_errors += 1
                    print(f"    Failed to summarize chunk {i+1}. Skipping.")
            
            print(f"Map step completed. {len(chunk_summaries)} chunks summarized. {map_errors} errors.")
            concatenated_chunk_summaries = "\n\n---\n\n".join(chunk_summaries)
            save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                         raw_chunk_summaries_concatenated=concatenated_chunk_summaries,
                         total_chunks_in_section=len(chunks),
                         processing_status='map_complete')
            conn.commit()

            if not chunk_summaries: 
                print(f"No chunk summaries generated for section ID {sec_id}. Cannot proceed to reduce step.")
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             processing_status='error', error_message='Failed to generate any chunk summaries')
                conn.commit()
                continue
            
            print("Starting Reduce step...")
            reduce_prompt_messages = [
                {"role": "system", "content": "You are an expert at synthesizing information from multiple summaries into a cohesive final summary."},
                {"role": "user", "content": f"Based *only* on the following partial summaries from the '{sec_key}' section of an SEC 10-K filing, provide a concise and comprehensive overall summary of the entire section in 2-3 bullet points. Ensure the summary is factual and directly derived from the provided text. Avoid speculation or information not present in the partial summaries.\n\nPartial Summaries:\n{concatenated_chunk_summaries}"}
            ]
            
            final_summary = call_openai_api(openai_client, reduce_prompt_messages, OPENAI_MODEL_NAME, MAX_TOKENS_FOR_FINAL_SUMMARY_OUTPUT)

            if final_summary:
                print(f"Successfully generated final summary for section ID {sec_id}.")
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             summary_text=final_summary, processing_status='reduce_complete')
            else:
                print(f"Failed to generate final summary for section ID {sec_id}.")
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             processing_status='error', error_message='Failed to generate final summary in reduce step')
            conn.commit()
            print(f"Finished processing section ID {sec_id}.")

        print("\nAll targeted sections processed.")

    except psycopg2.Error as db_err:
        print(f"\nDatabase error occurred: {db_err}")
        if conn: conn.rollback()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        # Consider if conn.rollback() is needed for general errors if DB was involved before error
    finally:
        if cur: cur.close()
        if conn: conn.close()
        print("\nPostgreSQL connection closed.")

if __name__ == "__main__":
    # Create summarization directory if it doesn't exist (script is inside it)
    summarization_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(summarization_dir): # Should always exist as script is in it
        try:
            # This case implies the script is not in the expected summarization/ dir
            # or the pathing is unexpected.
            # For robustness, let's ensure PROJECT_ROOT/summarization exists
            expected_summarization_dir = os.path.join(PROJECT_ROOT, "summarization")
            if not os.path.exists(expected_summarization_dir):
                 os.makedirs(expected_summarization_dir)
                 print(f"Created directory: {expected_summarization_dir}")
        except OSError as e:
            print(f"Error creating directory {expected_summarization_dir}: {e}")
            # Decide if script should exit
    
    main() 