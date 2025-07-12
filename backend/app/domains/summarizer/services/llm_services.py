# Standard library imports
import os
import sys
import traceback

# Third-party imports
from openai import OpenAI
from typing import Optional

# App imports
from app.domains.summarization.core.config import (
    OPENAI_API_KEY, 
    TOP_LEVEL_SUMMARY_MODEL, 
    MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY
)

# Check for OpenAI API key on module import
if not os.getenv("OPENAI_API_KEY"):
    # Silent initialization - let calling code handle missing key
    client = None
else:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Silent success - client initialized
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
        client = None

def call_openai_api(prompt_messages, model_name=None, max_tokens_output=None):
    """Calls the OpenAI Chat Completions API using the globally initialized client.
    Args:
        prompt_messages (list): List of message objects for the prompt.
        model_name (str, optional): The model to use. Defaults to TOP_LEVEL_SUMMARY_MODEL from config.
        max_tokens_output (int, optional): Max tokens for output. Defaults to MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY.
    Returns:
        str: The content of the message from the OpenAI API response, or None if an error occurs.
    """
    if not client:
        print("Error: OpenAI client is not initialized. Cannot make API call.", file=sys.stderr)
        return None

    current_model = model_name or TOP_LEVEL_SUMMARY_MODEL
    current_max_tokens = max_tokens_output or MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY

    try:
        
        response = client.chat.completions.create(
            model=current_model,
            messages=prompt_messages,
            max_tokens=current_max_tokens,
            temperature=0.3,  # Lower temperature for more factual/deterministic summaries
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
            else:
                print(f"Warning: OpenAI API response did not contain expected content. Response: {response}", file=sys.stderr)
                return None
    except Exception as e:
        if "openai" in str(type(e)).lower():
            print(f"OpenAI API Error (model: {current_model}): {e}", file=sys.stderr)
        else:
            print(f"An unexpected error occurred during OpenAI API call (model: {current_model}): {e}", file=sys.stderr)
        return None

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