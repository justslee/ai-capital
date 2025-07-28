"""
Shared Exception Classes

Domain-specific exception classes for consistent error handling across all domains.
Provides structured error reporting with appropriate HTTP status codes.
"""

# Standard library imports
from typing import Optional, Dict, Any

# Third-party imports
from fastapi import HTTPException


class DomainException(Exception):
    """
    Base exception class for all domain-specific errors.
    
    Provides common functionality for error reporting and logging.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class SummarizationException(DomainException):
    """Base exception for summarization domain errors."""
    pass


class FilingNotFoundException(SummarizationException):
    """Raised when a requested SEC filing is not found."""
    
    def __init__(self, ticker: str, year: int, form_type: str):
        message = f"No {form_type} filing found for ticker '{ticker}' in year {year}"
        super().__init__(
            message=message,
            error_code="FILING_NOT_FOUND",
            details={"ticker": ticker, "year": year, "form_type": form_type}
        )


class SummaryGenerationException(SummarizationException):
    """Raised when summary generation fails."""
    
    def __init__(self, accession_number: str, reason: str):
        message = f"Failed to generate summary for filing {accession_number}: {reason}"
        super().__init__(
            message=message,
            error_code="SUMMARY_GENERATION_FAILED",
            details={"accession_number": accession_number, "reason": reason}
        )


class PrerequisiteDataMissingException(SummarizationException):
    """Raised when required section summaries are missing."""
    
    def __init__(self, accession_number: str, missing_sections: list):
        message = f"Missing required section summaries for filing {accession_number}: {', '.join(missing_sections)}"
        super().__init__(
            message=message,
            error_code="PREREQUISITE_DATA_MISSING", 
            details={"accession_number": accession_number, "missing_sections": missing_sections}
        )


class ModelingException(DomainException):
    """Base exception for modeling domain errors."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, details=details)


class DataIngestionException(ModelingException):
    """Raised when data ingestion fails."""
    
    def __init__(self, ticker: str, source: str, reason: str):
        message = f"Failed to ingest data for {ticker} from {source}: {reason}"
        super().__init__(
            message=message,
            error_code="DATA_INGESTION_FAILED",
            details={"ticker": ticker, "source": source, "reason": reason}
        )


class InvalidTickerException(ModelingException):
    """Raised when an invalid ticker symbol is provided."""
    
    def __init__(self, ticker: str):
        message = f"Invalid ticker symbol: '{ticker}'"
        super().__init__(
            message=message,
            error_code="INVALID_TICKER",
            details={"ticker": ticker}
        )


class DataSourceException(ModelingException):
    """Raised when external data source is unavailable or returns errors."""
    
    def __init__(self, source: str, reason: str):
        message = f"Data source '{source}' error: {reason}"
        super().__init__(
            message=message,
            error_code="DATA_SOURCE_ERROR",
            details={"source": source, "reason": reason}
        )


class APIKeyMissingException(DomainException):
    """Raised when required API keys are missing."""
    
    def __init__(self, service: str, key_name: str):
        message = f"API key missing for {service}: {key_name}"
        super().__init__(
            message=message,
            error_code="API_KEY_MISSING",
            details={"service": service, "key_name": key_name}
        )


class ConfigurationException(DomainException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, config_item: str, reason: str):
        message = f"Configuration error for {config_item}: {reason}"
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details={"config_item": config_item, "reason": reason}
        )


def domain_exception_to_http_exception(exception: DomainException) -> HTTPException:
    """
    Convert domain exceptions to FastAPI HTTPException with appropriate status codes.
    
    Args:
        exception: Domain-specific exception
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    # Map exception types to HTTP status codes
    status_code_map = {
        FilingNotFoundException: 404,
        InvalidTickerException: 400,
        PrerequisiteDataMissingException: 409,  # Conflict - prerequisite data missing
        SummaryGenerationException: 500,
        DataIngestionException: 500,
        DataSourceException: 502,  # Bad Gateway - external service issue
        APIKeyMissingException: 401,  # Unauthorized - missing credentials
        ConfigurationException: 500,
    }
    
    status_code = status_code_map.get(type(exception), 500)
    
    detail = {
        "error": exception.message,
        "error_code": exception.error_code,
        "details": exception.details
    }
    
    return HTTPException(status_code=status_code, detail=detail)


def handle_domain_exception(exception: Exception) -> HTTPException:
    """
    Handle domain exceptions and convert them to appropriate HTTP responses.
    
    Args:
        exception: Any exception that occurred
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    if isinstance(exception, DomainException):
        return domain_exception_to_http_exception(exception)
    else:
        # Handle generic exceptions
        return HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "details": {"message": str(exception)}
            }
        ) 