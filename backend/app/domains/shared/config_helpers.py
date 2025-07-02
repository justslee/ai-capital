"""
Shared Configuration Helpers

Common configuration utilities used across domains.
"""

# Standard library imports
import os
from typing import Dict, Optional, Any

# Third-party imports
from pydantic_settings import BaseSettings

# App imports
from app.config import settings


def get_domain_config(domain_name: str) -> Dict[str, Any]:
    """
    Get standardized configuration for a domain.
    
    Args:
        domain_name: Name of the domain (summarization, valuation, modeling)
        
    Returns:
        Dictionary of configuration values
    """
    base_config = {
        "database_url": settings.database_url,
        "redis_host": getattr(settings, 'redis_host', 'localhost'),
        "redis_port": getattr(settings, 'redis_port', 6379),
        "cache_ttl_seconds": getattr(settings, 'cache_ttl_seconds', 3600),
    }
    
    # Domain-specific configurations
    if domain_name == "summarization":
        base_config.update({
            "openai_api_key": settings.openai_api_key,
            "section_summary_model": "gpt-4-turbo",
            "top_level_summary_model": "gpt-4-turbo",
            "max_tokens_summary": 700,
        })
    elif domain_name == "valuation":
        base_config.update({
            "fmp_api_key": settings.fmp_api_key,
            "financial_cache_ttl": 86400,  # 24 hours
        })
    elif domain_name == "modeling":
        base_config.update({
            "tiingo_api_key": getattr(settings, 'tiingo_api_key', None),
            "alphavantage_api_key": getattr(settings, 'alphavantage_api_key', None),
            "max_concurrent_requests": 5,
            "request_delay_seconds": 0.1,
        })
    
    return base_config


def validate_api_keys(domain_name: str) -> Dict[str, bool]:
    """
    Validate that required API keys are available for a domain.
    
    Args:
        domain_name: Name of the domain
        
    Returns:
        Dictionary mapping API key names to availability status
    """
    results = {}
    
    if domain_name == "summarization":
        results["openai_api_key"] = bool(settings.openai_api_key)
    elif domain_name == "valuation":
        results["fmp_api_key"] = bool(settings.fmp_api_key)
    elif domain_name == "modeling":
        results["tiingo_api_key"] = bool(getattr(settings, 'tiingo_api_key', None))
        results["alphavantage_api_key"] = bool(getattr(settings, 'alphavantage_api_key', None))
    
    return results


def get_environment_variable(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Safely get environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        Environment variable value or default
        
    Raises:
        ValueError: If required variable is missing
    """
    value = os.getenv(key, default)
    
    if required and not value:
        raise ValueError(f"Required environment variable '{key}' is not set")
    
    return value 