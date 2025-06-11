from app.config import settings

# Use the main app config settings
DATABASE_URL = settings.database_url
OPENAI_API_KEY = settings.openai_api_key

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

print(f"Summarization domain config loaded successfully.")
print(f"  DATABASE_URL: {'Set' if DATABASE_URL else 'NOT SET'}")
print(f"  OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'NOT SET'}")
print(f"  TOP_LEVEL_SUMMARY_MODEL: {TOP_LEVEL_SUMMARY_MODEL}")
print(f"  SOURCE_SECTION_KEYS_FOR_TOP_LEVEL: {SOURCE_SECTION_KEYS_FOR_TOP_LEVEL}") 