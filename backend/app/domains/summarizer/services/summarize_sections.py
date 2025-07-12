import psycopg2
import sys
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlparse
import openai
import time
from typing import Dict, List, Optional

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
        section_db_id INTEGER NOT NULL UNIQUE REFERENCES sec_filing_sections(id) ON DELETE CASCADE,
        filing_accession_number TEXT NOT NULL,
        section_key TEXT NOT NULL,
        summarization_model_name TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        raw_chunk_summaries_concatenated TEXT,
        total_chunks_in_section INTEGER,
        processing_status TEXT,
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

def get_unprocessed_sections(cursor, model_name, target_section_keys):
    """Get sections that need summarization or re-processing."""
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
    return sections

def get_chunks_for_section(cursor, section_db_id):
    """Get all text chunks for a section, ordered by sequence."""
    query = """
    SELECT chunk_text 
    FROM sec_filing_section_chunks
    WHERE section_db_id = %s
    ORDER BY chunk_order_in_section ASC;
    """
    cursor.execute(query, (section_db_id,))
    chunks = [row[0] for row in cursor.fetchall()]
    return chunks

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
    cursor, section_db_id, filing_accession_number, section_key, 
    summarization_model_name, summary_text=None, raw_chunk_summaries_concatenated=None, 
    total_chunks_in_section=None, processing_status=None, error_message=None
):
    """Insert or update a summary record."""
    
    cursor.execute(
        "SELECT id FROM sec_section_summaries WHERE section_db_id = %s AND summarization_model_name = %s",
        (section_db_id, summarization_model_name)
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
            section_db_id, filing_accession_number, section_key, summarization_model_name, 
            summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section, 
            processing_status, error_message
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (section_db_id, summarization_model_name) DO NOTHING;
        """
        final_summary_text = summary_text if summary_text is not None else ""

        cursor.execute(query, (
            section_db_id, filing_accession_number, section_key, summarization_model_name,
            final_summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section,
            processing_status, error_message
        ))

def summarize_sections_for_accession(accession_no: str, section_keys_list: List[str]) -> None:
    """Main function to summarize sections for a specific accession number."""
    
    if not OPENAI_API_KEY:
        # Silent exit - missing API key
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        if not section_keys_list:
            # Silent return - no sections to process
            return

        for sec_key in section_keys_list:
            # Get section ID
            cursor.execute(
                "SELECT id FROM sec_filing_sections WHERE accession_number = %s AND section_key = %s",
                (accession_no, sec_key)
            )
            section_result = cursor.fetchone()
            
            if not section_result:
                continue
                
            sec_id = section_result[0]
            
            # Get chunks for this section
            cursor.execute(
                "SELECT id, chunk_text FROM sec_filing_section_chunks WHERE section_id = %s ORDER BY chunk_order",
                (sec_id,)
            )
            chunks = cursor.fetchall()
            
            if not chunks:
                # Silent skip - no chunks found
                continue

            # Map step: Summarize each chunk
            chunk_summaries = []
            map_errors = 0
            
            for i, (chunk_id, chunk_text) in enumerate(chunks):
                chunk_summary = call_openai_api(
                    prompt_messages=[
                        {"role": "system", "content": SECTION_SUMMARY_SYSTEM_MESSAGE},
                        {"role": "user", "content": chunk_text}
                    ],
                    model_name=SECTION_SUMMARY_MODEL,
                    max_tokens_output=MAX_TOKENS_SECTION_SUMMARY
                )
                
                if chunk_summary:
                    chunk_summaries.append((chunk_id, chunk_summary))
                else:
                    map_errors += 1

            if not chunk_summaries:
                # Silent skip - no summaries generated
                continue

            # Reduce step: Generate final summary
            combined_text = "\n\n".join([summary for _, summary in chunk_summaries])
            
            final_summary = call_openai_api(
                prompt_messages=[
                    {"role": "system", "content": SECTION_SUMMARY_SYSTEM_MESSAGE},
                    {"role": "user", "content": combined_text}
                ],
                model_name=SECTION_SUMMARY_MODEL,
                max_tokens_output=MAX_TOKENS_SECTION_SUMMARY
            )
            
            if final_summary:
                # Store the final summary
                cursor.execute(
                    """INSERT INTO sec_filing_section_summaries 
                       (accession_number, section_key, summary_text, model_name, created_at) 
                       VALUES (%s, %s, %s, %s, NOW())""",
                    (accession_no, sec_key, final_summary, SECTION_SUMMARY_MODEL)
                )
                conn.commit()
            else:
                # Silent continue - failed to generate summary
                continue
        
    except psycopg2.Error as db_err:
        # Log database errors without console output
        pass
    except Exception as e:
        # Log unexpected errors without console output
        pass
    finally:
        if conn:
            conn.close()

def main():
    conn = None
    cur = None
    
    if not OPENAI_API_KEY:
        # Silent exit - missing API key
        sys.exit(1)
    
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()

        create_summaries_table(cur)
        conn.commit()

        unprocessed_sections = get_unprocessed_sections(cur, OPENAI_MODEL_NAME, TARGET_SECTION_KEYS)

        if not unprocessed_sections:
            # Silent return - no sections to process
            return

        for sec_id, accession_no, sec_key in unprocessed_sections:
            # Process section without debug output
            
            save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                         processing_status='pending_map')
            conn.commit()

            chunks = get_chunks_for_section(cur, sec_id)
            if not chunks:
                # Silent error - no chunks found
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             processing_status='error', error_message='No chunks found for section', total_chunks_in_section=0)
                conn.commit()
                continue

            chunk_summaries = []
            map_errors = 0
            # Process chunks silently
            for i, chunk_text in enumerate(chunks):
                map_prompt_messages = [
                    {"role": "system", "content": "You are an expert at summarizing financial document segments."},
                    {"role": "user", "content": f"The following is a text segment from the '{sec_key}' section of an SEC 10-K filing. Briefly summarize the main points or key information contained *only* in this specific segment in 1-2 sentences: \n\nText Segment:\n{chunk_text}"}
                ]
                # Rate limiting without console output
                if i > 0 and i % 10 == 0: time.sleep(1) 

                chunk_summary = call_openai_api(openai_client, map_prompt_messages, OPENAI_MODEL_NAME, MAX_TOKENS_FOR_CHUNK_SUMMARY_OUTPUT)
                if chunk_summary:
                    chunk_summaries.append(chunk_summary)
                else:
                    map_errors += 1
            
            # Save intermediate results
            concatenated_chunk_summaries = "\n\n---\n\n".join(chunk_summaries)
            save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                         raw_chunk_summaries_concatenated=concatenated_chunk_summaries,
                         total_chunks_in_section=len(chunks),
                         processing_status='map_complete')
            conn.commit()

            if not chunk_summaries: 
                # Silent error - no chunk summaries generated
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             processing_status='error', error_message='Failed to generate any chunk summaries')
                conn.commit()
                continue
            
            # Generate final summary
            reduce_prompt_messages = [
                {"role": "system", "content": "You are an expert at synthesizing information from multiple summaries into a cohesive final summary."},
                {"role": "user", "content": f"Based *only* on the following partial summaries from the '{sec_key}' section of an SEC 10-K filing, provide a concise and comprehensive overall summary of the entire section in 2-3 bullet points. Ensure the summary is factual and directly derived from the provided text. Avoid speculation or information not present in the partial summaries.\n\nPartial Summaries:\n{concatenated_chunk_summaries}"}
            ]
            
            final_summary = call_openai_api(openai_client, reduce_prompt_messages, OPENAI_MODEL_NAME, MAX_TOKENS_FOR_FINAL_SUMMARY_OUTPUT)

            if final_summary:
                # Silent success - final summary generated
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             summary_text=final_summary, processing_status='reduce_complete')
            else:
                # Silent error - failed to generate final summary
                save_summary(cur, sec_id, accession_no, sec_key, OPENAI_MODEL_NAME, 
                             processing_status='error', error_message='Failed to generate final summary in reduce step')
            conn.commit()

        # Processing complete - silent finish

    except psycopg2.Error as db_err:
        # Log database errors without console output
        if conn: conn.rollback()
    except Exception as e:
        # Log unexpected errors without console output
        # Consider if conn.rollback() is needed for general errors if DB was involved before error
        pass
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    main() 