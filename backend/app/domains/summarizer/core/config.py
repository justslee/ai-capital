from app.config import get_settings

def get_openai_api_key() -> str:
    """Get fresh OpenAI API key from settings - no caching."""
    return get_settings().openai_api_key

# --- Model Configurations (Centralized) ---
# Model used for generating individual section summaries (map-reduce step, if needed by API)
SECTION_SUMMARY_MODEL = "gpt-4-turbo"  # Default value

# Model used for generating the detailed top-level summary for hedge fund managers
TOP_LEVEL_SUMMARY_MODEL = "gpt-4-turbo"  # Default value

# --- Token Limits (Centralized) ---
MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY = 700  # Default value

# --- Source Section Keys for Top-Level Summary (Centralized) ---
# These are the section_key values from sec_section_summaries to use as input for top-level summary
SOURCE_SECTION_KEYS_FOR_TOP_LEVEL = ["Business", "MD&A", "Risk Factors"]  # Default sorted list 