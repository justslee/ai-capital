import os
from dotenv import load_dotenv
import sys

# Assuming this script (config.py) is in app/core/
# Project root is two levels up from app/core/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Attempt to load .env file
if os.path.exists(DOTENV_PATH):
    print(f"Loading .env file from: {DOTENV_PATH} (called from app/core/config.py)")
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}. Ensure environment variables are set manually or the .env file exists at the project root.", file=sys.stderr)

# --- Essential API Keys and URLs ---
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Model Configurations (Centralized) ---
# Model used for generating individual section summaries (map-reduce step, if needed by API)
SECTION_SUMMARY_MODEL = os.getenv("SECTION_SUMMARY_MODEL", "gpt-4-turbo")

# Model used for generating the detailed top-level summary for hedge fund managers
TOP_LEVEL_SUMMARY_MODEL = os.getenv("TOP_LEVEL_SUMMARY_MODEL", "gpt-4-turbo")

# --- Token Limits (Centralized) ---
# MAX_TOKENS_CHUNK_SUMMARY = int(os.getenv("MAX_TOKENS_CHUNK_SUMMARY", 150))
# MAX_TOKENS_FINAL_SECTION_SUMMARY = int(os.getenv("MAX_TOKENS_FINAL_SECTION_SUMMARY", 500))
MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY = int(os.getenv("MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY", 700))

# --- Source Section Keys for Top-Level Summary (Centralized) ---
# These are the section_key values from sec_section_summaries to use as input for top-level summary
# Default to a common set if not specified in .env, ensure they are sorted.
_source_keys_str = os.getenv("SOURCE_SECTION_KEYS_FOR_TOP_LEVEL", "Business,Risk Factors,MD&A")
SOURCE_SECTION_KEYS_FOR_TOP_LEVEL = sorted([key.strip() for key in _source_keys_str.split(',')])

# --- Critical Variable Checks (essential for app startup) ---
missing_critical_vars = False
if not DATABASE_URL:
    print("CRITICAL_ERROR: DATABASE_URL not found in environment. Service cannot connect to DB.", file=sys.stderr)
    missing_critical_vars = True

if not OPENAI_API_KEY:
    print("CRITICAL_ERROR: OPENAI_API_KEY not found in environment. LLM services will fail.", file=sys.stderr)
    missing_critical_vars = True

if missing_critical_vars:
    # In a real application, this might prevent the app from starting or cause a health check to fail.
    print("CRITICAL_ERROR: One or more essential environment variables are missing. Application may not function correctly.", file=sys.stderr)
    # sys.exit(1) # Uncomment to force exit if critical vars are missing

print(f"app/core/config.py loaded successfully.")
print(f"  DATABASE_URL: {'Set' if DATABASE_URL else 'NOT SET'}")
print(f"  OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'NOT SET'}")
print(f"  TOP_LEVEL_SUMMARY_MODEL: {TOP_LEVEL_SUMMARY_MODEL}")
print(f"  SOURCE_SECTION_KEYS_FOR_TOP_LEVEL: {SOURCE_SECTION_KEYS_FOR_TOP_LEVEL}") 