"""
Shared Response Models

Standardized response models and error handling patterns used across all domains.
Ensures consistent API response formats throughout the application.
"""

# Standard library imports
from datetime import datetime
from typing import Optional, Any, Dict, List, Union
from enum import Enum

# Third-party imports
from pydantic import BaseModel, Field


class StatusEnum(str, Enum):
    """Standard status values for API responses."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class APIResponse(BaseModel):
    """
    Standard API response wrapper.
    
    Provides consistent structure for all API responses across domains.
    """
    status: StatusEnum = Field(..., description="Response status")
    message: Optional[str] = Field(None, description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response payload")
    errors: Optional[List[str]] = Field(None, description="List of error messages")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Unique request identifier")


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    
    Used for consistent error reporting across all domains.
    """
    status: StatusEnum = Field(StatusEnum.ERROR, description="Error status")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    error_code: Optional[str] = Field(None, description="Application-specific error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class PaginatedResponse(BaseModel):
    """
    Standard pagination wrapper for list responses.
    
    Provides consistent pagination metadata across domains.
    """
    items: List[Any] = Field(..., description="List of items")
    total_count: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class HealthCheckResponse(BaseModel):
    """
    Standard health check response format.
    
    Used for monitoring and service discovery across domains.
    """
    status: StatusEnum = Field(..., description="Service health status")
    service_name: str = Field(..., description="Name of the service")
    version: str = Field(..., description="Service version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Status of service dependencies")
    timestamp: datetime = Field(default_factory=datetime.now, description="Health check timestamp")


# Domain-specific response models that extend the base patterns
class SummarizationResponse(APIResponse):
    """Response model for summarization endpoints."""
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    year: Optional[int] = Field(None, description="Filing year")
    form_type: Optional[str] = Field(None, description="SEC form type")
    accession_number: Optional[str] = Field(None, description="SEC accession number")


class ValuationResponse(APIResponse):
    """Response model for valuation endpoints."""
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    valuation_type: Optional[str] = Field(None, description="Type of valuation calculation")
    period: Optional[str] = Field(None, description="Financial data period")


class IngestionResponse(APIResponse):
    """Response model for data ingestion endpoints."""
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    records_processed: Optional[int] = Field(None, description="Number of records processed")
    records_inserted: Optional[int] = Field(None, description="Number of records inserted")
    records_updated: Optional[int] = Field(None, description="Number of records updated")
    start_date: Optional[str] = Field(None, description="Data start date")
    end_date: Optional[str] = Field(None, description="Data end date")
    source: Optional[str] = Field(None, description="Data source")


class BulkIngestionResponse(APIResponse):
    """Response model for bulk ingestion operations."""
    total_tickers: int = Field(..., description="Total number of tickers processed")
    successful: int = Field(..., description="Number of successful ingestions")
    failed: int = Field(..., description="Number of failed ingestions")
    total_records: int = Field(..., description="Total number of records processed")
    started_at: datetime = Field(..., description="Ingestion start time")


def create_success_response(
    data: Any = None,
    message: str = "Operation completed successfully",
    **kwargs
) -> APIResponse:
    """
    Helper function to create standardized success responses.
    
    Args:
        data: Response payload
        message: Success message
        **kwargs: Additional fields for the response
        
    Returns:
        Standardized success response
    """
    return APIResponse(
        status=StatusEnum.SUCCESS,
        message=message,
        data=data,
        **kwargs
    )


def create_error_response(
    error: str,
    detail: Optional[str] = None,
    error_code: Optional[str] = None,
    **kwargs
) -> ErrorResponse:
    """
    Helper function to create standardized error responses.
    
    Args:
        error: Error message
        detail: Detailed error information
        error_code: Application-specific error code
        **kwargs: Additional fields for the response
        
    Returns:
        Standardized error response
    """
    return ErrorResponse(
        error=error,
        detail=detail,
        error_code=error_code,
        **kwargs
    )


def create_paginated_response(
    items: List[Any],
    total_count: int,
    page: int,
    page_size: int
) -> PaginatedResponse:
    """
    Helper function to create standardized paginated responses.
    
    Args:
        items: List of items for current page
        total_count: Total number of items available
        page: Current page number (1-based)
        page_size: Number of items per page
        
    Returns:
        Standardized paginated response
    """
    total_pages = (total_count + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    ) 