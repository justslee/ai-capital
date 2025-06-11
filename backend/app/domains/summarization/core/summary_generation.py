import psycopg2
import sys
import traceback
from app.domains.summarization.core.config import (
    TOP_LEVEL_SUMMARY_MODEL,
    MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY,
    SOURCE_SECTION_KEYS_FOR_TOP_LEVEL,
    SECTION_SUMMARY_MODEL # Used to identify which source summaries to fetch
)
from app.db.database_utils import db_cursor
from app.domains.summarization.core.llm_services import call_openai_api

# This is the detailed prompt for hedge fund managers, as defined previously.
HEDGE_FUND_SYSTEM_PROMPT = "You are an expert financial analyst AI. Your task is to synthesize information from provided SEC 10-K section summaries into a comprehensive analysis tailored for hedge fund managers to aid in their investment decisions."

HEDGE_FUND_USER_PROMPT_TEMPLATE = f"""From the following section summaries of an SEC 10-K filing, provide a comprehensive analysis for a hedge fund manager. Focus on aspects critical for investment decisions.

Your analysis should cover:
1.  **Overall Sentiment and Key Takeaways:** What is the general outlook (positive, negative, neutral)? What are the 2-3 most critical takeaways a hedge fund manager should know immediately?
2.  **Significant Performance Highlights & Lowlights:** Based on the MD&A, what were notable financial or operational achievements or shortcomings?
3.  **Major Risks & Mitigations (if mentioned):** From Risk Factors, what are the 2-3 most significant risks that could materially impact the company? Are any mitigations discussed?
4.  **Strategic Direction & Business Outlook:** Insights from the Business section regarding strategy, competitive positioning, and future growth drivers or concerns.
5.  **Red Flags or Green Flags:** Identify any specific points that stand out as particularly concerning (red flags) or exceptionally positive (green flags) from an investment perspective.

Present your analysis in clear, concise language. Use bullet points within each numbered section for readability. Ensure your analysis is strictly derived from the provided text and avoids speculation. Cite the source section (e.g., '[Business]', '[Risk Factors]', '[MD&A]') for key pieces of information where appropriate.

Section Summaries:
{{concatenated_section_summaries}}"""

def generate_and_store_top_level_summary(filing_accession_number: str):
    """Generates a top-level summary for a given filing if it doesn't exist.
    
    Args:
        filing_accession_number (str): The accession number of the filing.
        
    Returns:
        str: The generated (or existing) top-level summary text, or None if an error occurs
             or if prerequisite section summaries are missing.
    Raises:
        ValueError: If prerequisite section summaries are not found or not complete.
        Exception: For OpenAI API errors or other unexpected issues.
    """
    print(f"Attempting to generate/retrieve top-level summary for: {filing_accession_number}")

    target_model_for_this_summary = TOP_LEVEL_SUMMARY_MODEL
    source_sections = SOURCE_SECTION_KEYS_FOR_TOP_LEVEL
    source_model_for_sections = SECTION_SUMMARY_MODEL # Model that generated the input summaries

    try:
        with db_cursor() as cursor: # Autocommit/rollback handled by context manager
            # 1. Check for existing top-level summary for this filing, model, and source keys
            cursor.execute(
                """SELECT top_level_summary_text FROM sec_filing_top_level_summaries 
                   WHERE filing_accession_number = %s 
                     AND summarization_model_name = %s 
                     AND source_section_keys = %s""",
                (filing_accession_number, target_model_for_this_summary, source_sections)
            )
            existing_summary = cursor.fetchone()
            if existing_summary:
                print(f"Found existing top-level summary for {filing_accession_number}, model {target_model_for_this_summary}.")
                return existing_summary[0]

            # 2. Fetch individual section summaries (prerequisites)
            print(f"No existing top-level summary found. Fetching source section summaries for {filing_accession_number} (model: {source_model_for_sections})...")
            fetched_section_summaries_content = []
            all_source_summaries_found = True
            for section_key in source_sections:
                cursor.execute(
                    """SELECT summary_text FROM sec_section_summaries
                       WHERE filing_accession_number = %s AND section_key = %s 
                         AND summarization_model_name = %s AND processing_status = 'reduce_complete'""",
                    (filing_accession_number, section_key, source_model_for_sections)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    fetched_section_summaries_content.append({"key": section_key, "summary": row[0]})
                    print(f"  Successfully fetched source summary for section: {section_key}")
                else:
                    print(f"  ERROR: Could not find a 'reduce_complete' source summary for section: {section_key} (Filing: {filing_accession_number}, Model: {source_model_for_sections})")
                    all_source_summaries_found = False
                    break
            
            if not all_source_summaries_found or not fetched_section_summaries_content:
                # This is a critical issue, the API cannot proceed without these inputs.
                raise ValueError(f"Could not fetch all required source section summaries for {filing_accession_number}. Summary generation aborted.")
            
            # 3. Format input for LLM
            concatenated_input_str = ""
            for item in fetched_section_summaries_content:
                concatenated_input_str += f"Section: {item['key']}\nSummary:\n{item['summary']}\n\n---\n\n"
            
            # 4. Call LLM using the imported service
            user_prompt = HEDGE_FUND_USER_PROMPT_TEMPLATE.format(concatenated_section_summaries=concatenated_input_str)
            prompt_messages = [
                {"role": "system", "content": HEDGE_FUND_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            print(f"Calling LLM ({target_model_for_this_summary}) to generate top-level summary for {filing_accession_number}...")
            new_top_level_summary = call_openai_api(
                prompt_messages,
                model_name=target_model_for_this_summary, # Explicitly pass model from config
                max_tokens_output=MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY # Explicitly pass token limit
            )

            if not new_top_level_summary:
                # call_openai_api logs errors internally, so we just need to handle the None case.
                raise Exception(f"Failed to generate top-level summary from LLM for {filing_accession_number}.")
            
            print(f"Successfully generated new top-level summary for {filing_accession_number}.")

            # 5. Save the new result
            print(f"Saving new top-level summary to database for {filing_accession_number}...")
            cursor.execute(
                """INSERT INTO sec_filing_top_level_summaries 
                   (filing_accession_number, summarization_model_name, source_section_keys, source_summaries_concatenated, top_level_summary_text)
                   VALUES (%s, %s, %s, %s, %s) RETURNING top_level_summary_text""",
                (filing_accession_number, target_model_for_this_summary, source_sections, concatenated_input_str, new_top_level_summary)
            )
            # The context manager `db_cursor` will handle commit if no exceptions.
            saved_summary_text = cursor.fetchone()[0] # Get the text from RETURNING clause
            print("New top-level summary saved successfully.")
            return saved_summary_text

    except ValueError as ve:
        print(f"ValueError in summary generation for {filing_accession_number}: {ve}", file=sys.stderr)
        raise # Re-raise to be handled by API endpoint if necessary
    except psycopg2.Error as db_err:
        print(f"Database error during top-level summary generation/storage for {filing_accession_number}: {db_err}", file=sys.stderr)
        # db_cursor context manager handles rollback.
        raise # Re-raise for API to handle
    except Exception as e:
        print(f"An unexpected error occurred during top-level summary generation for {filing_accession_number}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise # Re-raise for API to handle

# Example for testing this module (adjust accession_number if needed):
# if __name__ == '__main__':
#     print("Testing generate_and_store_top_level_summary...")
#     # Ensure your .env is loaded and config is correct.
#     # You might need to delete an existing summary from the DB for this test to generate a new one.
#     # Example: DELETE FROM sec_filing_top_level_summaries WHERE filing_accession_number = '0000320193-24-000123';
#     test_accession_number = "0000320193-24-000123" 
#     try:
#         summary = generate_and_store_top_level_summary(test_accession_number)
#         if summary:
#             print("\n--- TEST SUMMARY ---")
#             print(summary)
#             print("\nTest completed.")
#         else:
#             print("Test failed to produce summary or found existing.")
#     except Exception as e:
#         print(f"Test execution failed: {e}") 