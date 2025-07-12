"""
Summarization Domain Configuration

Configuration settings for SEC filing summarization including
model settings, token limits, and summarization parameters.
"""

# Standard library imports
from typing import Dict, List, Optional, Any

# Third-party imports
from pydantic import Field

# App imports
from app.shared.config_helpers import BaseDomainConfig, create_domain_config


class SummarizationConfig(BaseDomainConfig):
    """Configuration for the summarization domain."""
    
    # OpenAI API Configuration
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(None, env="OPENAI_ORGANIZATION")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    
    # Model Settings
    section_summary_model: str = Field(default="gpt-4-turbo", env="SECTION_SUMMARY_MODEL")
    top_level_summary_model: str = Field(default="gpt-4-turbo", env="TOP_LEVEL_SUMMARY_MODEL")
    
    # Token Limits
    max_tokens_section_summary: int = Field(default=150, env="MAX_TOKENS_SECTION_SUMMARY")
    max_tokens_top_level_summary: int = Field(default=700, env="MAX_TOKENS_TOP_LEVEL_SUMMARY")
    max_tokens_chunk_summary: int = Field(default=150, env="MAX_TOKENS_CHUNK_SUMMARY")
    max_tokens_final_summary: int = Field(default=500, env="MAX_TOKENS_FINAL_SUMMARY")
    
    # Summarization Settings
    chunk_size: int = Field(default=4000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    enable_section_filtering: bool = Field(default=True, env="ENABLE_SECTION_FILTERING")
    
    # Section Configuration
    source_section_keys: List[str] = Field(
        default=["Business", "MD&A", "Risk Factors"],
        env="SOURCE_SECTION_KEYS"
    )
    target_section_keys: List[str] = Field(
        default=["Business", "Risk Factors", "MD&A"],
        env="TARGET_SECTION_KEYS"
    )
    
    # Processing Settings
    enable_parallel_processing: bool = Field(default=True, env="ENABLE_PARALLEL_PROCESSING")
    max_concurrent_summarizations: int = Field(default=3, env="MAX_CONCURRENT_SUMMARIZATIONS")
    summarization_timeout: int = Field(default=300, env="SUMMARIZATION_TIMEOUT")  # 5 minutes
    
    # Pinecone Configuration (for embeddings)
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="sec-filings", env="PINECONE_INDEX_NAME")
    
    def validate_required_fields(self) -> Dict[str, bool]:
        """
        Validate that all required fields are present.
        
        Returns:
            Dictionary mapping field names to validation status
        """
        results = super().validate_required_fields()
        
        # Check OpenAI API key
        results["openai_api_key"] = bool(self.openai_api_key)
        
        # Optional: Check Pinecone keys if embedding features are enabled
        results["pinecone_api_key"] = bool(self.pinecone_api_key)
        results["pinecone_environment"] = bool(self.pinecone_environment)
        
        return results
    
    def get_model_params(self) -> Dict[str, Any]:
        """
        Get model configuration parameters.
        
        Returns:
            Dictionary of model parameters
        """
        return {
            "section_summary_model": self.section_summary_model,
            "top_level_summary_model": self.top_level_summary_model,
            "max_tokens_section_summary": self.max_tokens_section_summary,
            "max_tokens_top_level_summary": self.max_tokens_top_level_summary,
        }
    
    def get_processing_params(self) -> Dict[str, Any]:
        """
        Get processing configuration parameters.
        
        Returns:
            Dictionary of processing parameters
        """
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "max_concurrent_summarizations": self.max_concurrent_summarizations,
            "summarization_timeout": self.summarization_timeout,
        }


# Global configuration instance
_summarization_config = None


def get_summarization_config() -> SummarizationConfig:
    """Get the global summarization configuration."""
    global _summarization_config
    if _summarization_config is None:
        _summarization_config = create_domain_config(SummarizationConfig)
    return _summarization_config


# Constants for summarization
FILING_TYPES = {
    "10-K": "10-K",
    "10-Q": "10-Q", 
    "8-K": "8-K",
    "DEF 14A": "DEF 14A",
}

SECTION_MAPPINGS = {
    "Business": ["business", "item 1", "item1"],
    "Risk Factors": ["risk factors", "item 1a", "item1a"],
    "MD&A": ["md&a", "management's discussion", "item 2", "item2"],
    "Financial Statements": ["financial statements", "item 8", "item8"],
    "Controls": ["controls", "item 9a", "item9a"],
}

SUMMARIZATION_PROMPTS = {
    "section_summary": """
    Please provide a concise summary of the following SEC filing section in 2-3 sentences.
    Focus on the most important business information that would be relevant to investors.
    
    Section: {section_name}
    Content: {content}
    """,
    
    "top_level_summary": """
    Based on the following section summaries from a company's SEC filing, provide a comprehensive
    summary in 5-7 sentences that captures the key business insights, risks, and opportunities.
    
    Business Summary: {business_summary}
    Risk Factors: {risk_summary}
    MD&A: {mdna_summary}
    """,
}


# Legacy compatibility - re-export from core config
# These will be deprecated in favor of the new configuration system
DATABASE_URL = None
OPENAI_API_KEY = None
SECTION_SUMMARY_MODEL = "gpt-4-turbo"
TOP_LEVEL_SUMMARY_MODEL = "gpt-4-turbo"
MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY = 700
SOURCE_SECTION_KEYS_FOR_TOP_LEVEL = ["Business", "MD&A", "Risk Factors"]


def _load_legacy_config():
    """Load legacy configuration for backward compatibility."""
    global DATABASE_URL, OPENAI_API_KEY
    
    try:
        config = get_summarization_config()
        DATABASE_URL = config.database_url
        OPENAI_API_KEY = config.openai_api_key
    except Exception:
        # Silent fallback - configuration will be handled by new system
        pass


# Initialize legacy configuration
_load_legacy_config()


__all__ = [
    "SummarizationConfig",
    "get_summarization_config",
    "FILING_TYPES",
    "SECTION_MAPPINGS", 
    "SUMMARIZATION_PROMPTS",
    # Legacy exports for compatibility
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "SECTION_SUMMARY_MODEL",
    "TOP_LEVEL_SUMMARY_MODEL",
    "MAX_TOKENS_HEDGE_FUND_TOP_LEVEL_SUMMARY",
    "SOURCE_SECTION_KEYS_FOR_TOP_LEVEL",
] 