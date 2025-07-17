# Standard library imports
import os
import sys
import traceback

# Third-party imports
from openai import OpenAI
from typing import List, Dict, Any, Optional
import logging
import openai

from app.domains.summarizer.core.config import (
    OPENAI_API_KEY, 
    TOP_LEVEL_SUMMARY_MODEL, 
    MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY
)
from app.shared.exceptions import DataSourceException

# Check for OpenAI API key on module import
if not OPENAI_API_KEY:
    # Silent initialization - let calling code handle missing key
    client = None
else:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        # Silent success - client initialized
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
        client = None


def call_openai_api(
    prompt_messages: List[Dict[str, str]],
    max_tokens_output: int,
    model_name: str = TOP_LEVEL_SUMMARY_MODEL
) -> Optional[str]:
    """
    Calls the OpenAI ChatCompletion API with specified parameters.

    Args:
        prompt_messages: A list of message dictionaries (e.g., [{"role": "user", "content": "Hello"}]).
        max_tokens_output: The maximum number of tokens to generate in the response.
        model_name: The name of the OpenAI model to use.

    Returns:
        The content of the API response, or None if the API call fails.
        
    Raises:
        DataSourceException: If the OpenAI API call fails.
    """
    if not client:
        raise DataSourceException(source="openai", reason="API client is not initialized. Check API key.")

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=prompt_messages,
            max_tokens=max_tokens_output,
            temperature=0.3,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            raise DataSourceException(source="openai", reason="API response was empty or malformed.")
            
    except openai.APIError as e:
        logging.error(f"OpenAI API error: {e}")
        raise DataSourceException(source="openai", reason=str(e)) from e
    except Exception as e:
        logging.error(f"An unexpected error occurred during OpenAI API call: {e}")
        raise DataSourceException(source="openai", reason=f"An unexpected error occurred: {e}") from e

# Example usage (for testing this module directly, if needed):
# if __name__ == '__main__':
#     if OPENAI_API_KEY:
#         test_messages = [
#             {"role": "system", "content": "You are a helpful assistant."},
#             {"role": "user", "content": "What is the capital of France?"}
#         ]
#         summary = call_openai_api(test_messages, model_name="gpt-3.5-turbo", max_tokens_output=50)
#         if summary:
#             print("Test API Call Successful:")
#             print(summary)
#         else:
#             print("Test API Call Failed.")
#     else:
#         print("Skipping test API call as OPENAI_API_KEY is not set.") 