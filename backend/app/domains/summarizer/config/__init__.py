"""
Summarization Domain Configuration

Configuration settings for SEC filing summarization including
model settings, token limits, and summarization parameters.
"""

from functools import lru_cache
from typing import List, Dict, Any

from pydantic import Field
from pydantic_settings import BaseSettings

from app.shared.config_helpers import BaseDomainConfig, create_domain_config


# Pydantic model for summarizer-specific settings
class SummarizerSettings(BaseSettings):
    """Configuration settings for the Summarizer domain."""
    # LLM Configuration
    default_model: str = Field(default="gpt-4-turbo-preview", env="SUMMARIZER_DEFAULT_MODEL")
    temperature: float = Field(default=0.3, env="SUMMARIZER_TEMPERATURE")
    max_tokens: int = Field(default=2048, env="SUMMARIZER_MAX_TOKENS")

    # Section Configuration
    source_section_keys: List[str] = Field(
        default=["Business", "MD&A", "Risk Factors"],
        env="SOURCE_SECTION_KEYS"
    )

    class Config:
        env_file = ".env"
        env_prefix = "SUMMARIZER_"
        extra = "ignore"


# --- Section Mappings ---
# Maps user-friendly names to keywords for parsing
SECTION_MAPPINGS = {
    "Business": ["business", "item 1", "item1"],
    "Risk Factors": ["risk factors", "item 1a", "item1a"],
    "MD&A": ["management's discussion and analysis", "md&a", "item 7", "item7"],
}

# --- Prompt Templates ---
SUMMARIZATION_PROMPTS = {
    "chunk_summary": """
        Concisely summarize the following text from the '{section}' section of an SEC filing. 
        Focus on the key facts, figures, and material information.
        TEXT:
        ---
        {text}
        ---
        SUMMARY:
    """,

    "section_synthesis": """
        Synthesize the following summaries from the '{section}' section of an SEC filing into a single, coherent summary.
        Combine related points and present the information in a clear, logical narrative.
        SUMMARIES:
        ---
        {chunk_summaries}
        ---
        SYNTHESIZED SUMMARY:
    """,

    "top_level_summary": """
        Generate a comprehensive report for the {ticker} {form_type} filing based on the following section summaries.

        **Comprehensive Report for {ticker} ({form_type})**

        **1. Business Overview:**
        {Business_summary}

        **2. Management's Discussion & Analysis (MD&A):**
        {MD&A_summary}

        **3. Risk Factors:**
        {Risk_Factors_summary}

        **4. Overall Synthesis & Key Insights:**
        Provide a concise, synthesized summary of the key findings from the sections above. Highlight the most critical insights a potential investor should know.
    """
}

# Singleton instance of the configuration
_summarization_config: BaseDomainConfig | None = None


def get_summarization_config() -> BaseDomainConfig:
    """Provides a singleton instance of the Summarizer configuration."""
    global _summarization_config
    if _summarization_config is None:
        _summarization_config = create_domain_config(
            "summarizer",
            SummarizerSettings,
            {"SECTION_MAPPINGS": SECTION_MAPPINGS, "SUMMARIZATION_PROMPTS": SUMMARIZATION_PROMPTS}
        )
    return _summarization_config 