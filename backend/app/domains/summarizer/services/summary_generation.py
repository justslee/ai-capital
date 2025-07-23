# Standard library imports
import logging
import traceback
from typing import Dict, List, Optional

# App imports
from app.domains.data_collection.services import get_data_collection_service
from app.domains.data_collection.storage.s3_storage_service import get_s3_storage_service

# Domain imports (relative)
from ..core.config import (
    SOURCE_SECTION_KEYS_FOR_TOP_LEVEL,
    TOP_LEVEL_SUMMARY_MODEL,
    MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY,
)
from .llm_services import call_openai_api
from .parsing_service import get_parsing_service

logger = logging.getLogger(__name__)

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

async def generate_and_store_top_level_summary(ticker: str, accession_number: str) -> Optional[str]:
    """
    Generates a top-level summary for a given filing by fetching it, parsing it,
    and summarizing its key sections.
    """

    data_collection_service = get_data_collection_service()
    s3_storage_service = get_s3_storage_service()
    parsing_service = get_parsing_service()

    try:
        # 1. Ensure the filing is collected and stored in S3
        await data_collection_service.collect_sec_filings(ticker)
        
        # 2. Retrieve the HTML content from S3
        html_content = await s3_storage_service.get_filing_html(ticker, accession_number)
        if not html_content:
            raise ValueError(f"Could not retrieve HTML for {accession_number} from S3.")

        # 3. Parse the HTML to extract key sections
        sections_to_extract = SOURCE_SECTION_KEYS_FOR_TOP_LEVEL
        extracted_sections = parsing_service.extract_sections(html_content, sections_to_extract)
        if not extracted_sections:
            raise ValueError(f"Could not extract any key sections from the filing.")

        # 4. Summarize each extracted section
        section_summaries = {}
        for section_key, section_text in extracted_sections.items():
            # This is a simplified summarization; in a real app, you'd have chunking logic here
            prompt = f"Summarize the following '{section_key}' section of an SEC filing:\n\n{section_text[:4000]}" # Truncate for now
            summary = call_openai_api([{"role": "user", "content": prompt}], max_tokens_output=150)
            if summary:
                section_summaries[section_key] = summary

        if not section_summaries:
            raise ValueError("Failed to generate summaries for any section.")

        # 5. Synthesize the top-level summary
        concatenated_input = "\n\n".join([f"Section: {k}\nSummary:\n{v}" for k, v in section_summaries.items()])
        user_prompt = HEDGE_FUND_USER_PROMPT_TEMPLATE.format(concatenated_section_summaries=concatenated_input)
        prompt_messages = [{"role": "system", "content": HEDGE_FUND_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
        
        top_level_summary = call_openai_api(
            prompt_messages,
            model_name=TOP_LEVEL_SUMMARY_MODEL,
            max_tokens_output=MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY
        )

        if not top_level_summary:
            raise Exception("Failed to generate the final top-level summary.")

        # 6. Store the final summary (database logic can be re-introduced here if needed)
        # For now, just returning the summary without DB storage to simplify the refactoring
        return top_level_summary

    except Exception as e:
        logger.error(f"Error generating summary for {ticker} - {accession_number}: {e}")
        traceback.print_exc()
        return None

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