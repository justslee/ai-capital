"""
Shared Domain Utilities

Common utilities and helpers used across multiple domains.
Provides configuration helpers, validation utilities, and database connection patterns.
"""

from .config_helpers import get_domain_config, validate_api_keys
from .validation_utils import validate_price_data, validate_date_range
from .database_helpers import get_db_connection_params, safe_db_operation
from .response_models import (
    APIResponse, ErrorResponse, PaginatedResponse, HealthCheckResponse,
    SummarizationResponse, ValuationResponse, IngestionResponse, BulkIngestionResponse,
    StatusEnum, create_success_response, create_error_response, create_paginated_response
)
from .exceptions import (
    DomainException, SummarizationException, ValuationException, ModelingException,
    FilingNotFoundException, SummaryGenerationException, PrerequisiteDataMissingException,
    FinancialDataNotFoundException, ValuationCalculationException,
    DataIngestionException, InvalidTickerException, DataSourceException,
    APIKeyMissingException, ConfigurationException,
    handle_domain_exception, domain_exception_to_http_exception
)

__all__ = [
    # Configuration helpers
    "get_domain_config",
    "validate_api_keys",
    
    # Validation utilities
    "validate_price_data", 
    "validate_date_range",
    
    # Database helpers
    "get_db_connection_params",
    "safe_db_operation",
    
    # Response models and helpers
    "APIResponse", "ErrorResponse", "PaginatedResponse", "HealthCheckResponse",
    "SummarizationResponse", "ValuationResponse", "IngestionResponse", "BulkIngestionResponse",
    "StatusEnum", "create_success_response", "create_error_response", "create_paginated_response",
    
    # Exception classes and handlers
    "DomainException", "SummarizationException", "ValuationException", "ModelingException",
    "FilingNotFoundException", "SummaryGenerationException", "PrerequisiteDataMissingException",
    "FinancialDataNotFoundException", "ValuationCalculationException",
    "DataIngestionException", "InvalidTickerException", "DataSourceException",
    "APIKeyMissingException", "ConfigurationException",
    "handle_domain_exception", "domain_exception_to_http_exception",
] 