"""
Summarization Parsing Utilities

Text processing and parsing utilities for SEC filings.
Handles HTML extraction, section detection, and text cleaning.
"""

from .extract_text_from_html import detect_section

__all__ = [
    "detect_section",
]
