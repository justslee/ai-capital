import openai
from app.domains.summarization.core.config import OPENAI_API_KEY, TOP_LEVEL_SUMMARY_MODEL, MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY
import sys
import traceback

if not OPENAI_API_KEY:
    print("CRITICAL_ERROR: app.core.llm_services cannot function without OPENAI_API_KEY set in app.core.config.", file=sys.stderr)
    # Depending on app structure, this might prevent module import or cause runtime errors.

# Initialize the OpenAI client once when the module is loaded.
# This is generally recommended over creating a new client for each call.
_openai_client = None
if OPENAI_API_KEY:
    try:
        _openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client initialized successfully in app.core.llm_services.")
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
        _openai_client = None
else:
    print("OpenAI client not initialized due to missing API key.", file=sys.stderr)

def call_openai_api(prompt_messages, model_name=None, max_tokens_output=None):
    """Calls the OpenAI Chat Completions API using the globally initialized client.
    Args:
        prompt_messages (list): List of message objects for the prompt.
        model_name (str, optional): The model to use. Defaults to TOP_LEVEL_SUMMARY_MODEL from config.
        max_tokens_output (int, optional): Max tokens for output. Defaults to MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY.
    Returns:
        str: The content of the message from the OpenAI API response, or None if an error occurs.
    """
    if not _openai_client:
        print("Error: OpenAI client is not initialized. Cannot make API call.", file=sys.stderr)
        return None

    current_model = model_name or TOP_LEVEL_SUMMARY_MODEL
    current_max_tokens = max_tokens_output or MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY

    try:
        # print(f"Sending prompt to OpenAI model: {current_model}, max_tokens: {current_max_tokens}") # For debugging
        response = _openai_client.chat.completions.create(
            model=current_model,
            messages=prompt_messages,
            max_tokens=current_max_tokens,
            temperature=0.3,  # Lower temperature for more factual/deterministic summaries
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        else:
            print(f"Warning: OpenAI API response did not contain expected content. Response: {response}", file=sys.stderr)
            return None
    except openai.APIError as e:
        print(f"OpenAI API Error (model: {current_model}): {e}", file=sys.stderr)
        # Specific error handling can be added here, e.g., for rate limits, auth errors, etc.
        return None
    except Exception as e:
        print(f"An unexpected error occurred during OpenAI API call (model: {current_model}): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
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