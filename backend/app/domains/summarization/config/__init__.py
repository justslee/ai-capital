"""
Summarization Domain Configuration

Configuration settings for SEC filing summarization including
model settings, token limits, and summarization parameters.
"""

# Re-export from core.config for backward compatibility
from ..core.config import (
    DATABASE_URL,
    OPENAI_API_KEY,
    SECTION_SUMMARY_MODEL,
    TOP_LEVEL_SUMMARY_MODEL,
    MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY,
    SOURCE_SECTION_KEYS_FOR_TOP_LEVEL
)

__all__ = [
    "DATABASE_URL",
    "OPENAI_API_KEY", 
    "SECTION_SUMMARY_MODEL",
    "TOP_LEVEL_SUMMARY_MODEL",
    "MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY",
    "SOURCE_SECTION_KEYS_FOR_TOP_LEVEL"
] 