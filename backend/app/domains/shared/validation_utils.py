"""
Shared Validation Utilities

Common validation functions used across domains.
"""

# Standard library imports
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal

# Third-party imports
from pydantic import ValidationError


def validate_price_data(
    price: Optional[Union[float, Decimal]], 
    volume: Optional[int] = None,
    min_price: float = 0.01,
    max_price: float = 100000.0,
    min_volume: int = 0,
    max_volume: int = 10_000_000_000
) -> Dict[str, Any]:
    """
    Validate price and volume data according to standard rules.
    
    Args:
        price: Price value to validate
        volume: Volume value to validate (optional)
        min_price: Minimum valid price
        max_price: Maximum valid price
        min_volume: Minimum valid volume
        max_volume: Maximum valid volume
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Price validation
    if price is not None:
        if price <= 0:
            results["is_valid"] = False
            results["errors"].append(f"Price must be positive, got {price}")
        elif price < min_price:
            results["warnings"].append(f"Price {price} is below minimum threshold {min_price}")
        elif price > max_price:
            results["is_valid"] = False
            results["errors"].append(f"Price {price} exceeds maximum threshold {max_price}")
    
    # Volume validation
    if volume is not None:
        if volume < 0:
            results["is_valid"] = False
            results["errors"].append(f"Volume must be non-negative, got {volume}")
        elif volume > max_volume:
            results["warnings"].append(f"Volume {volume} exceeds typical maximum {max_volume}")
    
    return results


def validate_ohlc_consistency(
    open_price: Optional[Union[float, Decimal]],
    high_price: Optional[Union[float, Decimal]], 
    low_price: Optional[Union[float, Decimal]],
    close_price: Optional[Union[float, Decimal]]
) -> Dict[str, Any]:
    """
    Validate OHLC (Open, High, Low, Close) price consistency.
    
    Args:
        open_price: Opening price
        high_price: High price
        low_price: Low price
        close_price: Closing price
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "is_valid": True,
        "errors": []
    }
    
    # Only validate if all values are present
    if all(x is not None for x in [open_price, high_price, low_price, close_price]):
        # Convert to float for comparison
        o, h, l, c = map(float, [open_price, high_price, low_price, close_price])
        
        if not (l <= o <= h):
            results["is_valid"] = False
            results["errors"].append(f"Open price {o} not between low {l} and high {h}")
        
        if not (l <= c <= h):
            results["is_valid"] = False
            results["errors"].append(f"Close price {c} not between low {l} and high {h}")
        
        if not (l <= h):
            results["is_valid"] = False
            results["errors"].append(f"Low price {l} greater than high price {h}")
    
    return results


def validate_date_range(
    start_date: Optional[Union[str, date]], 
    end_date: Optional[Union[str, date]]
) -> Dict[str, Any]:
    """
    Validate date range parameters.
    
    Args:
        start_date: Start date (string or date object)
        end_date: End date (string or date object)
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "is_valid": True,
        "errors": [],
        "parsed_start": None,
        "parsed_end": None
    }
    
    try:
        # Parse start date
        if start_date:
            if isinstance(start_date, str):
                results["parsed_start"] = datetime.strptime(start_date, "%Y-%m-%d").date()
            else:
                results["parsed_start"] = start_date
        
        # Parse end date
        if end_date:
            if isinstance(end_date, str):
                results["parsed_end"] = datetime.strptime(end_date, "%Y-%m-%d").date()
            else:
                results["parsed_end"] = end_date
        
        # Validate range
        if results["parsed_start"] and results["parsed_end"]:
            if results["parsed_start"] > results["parsed_end"]:
                results["is_valid"] = False
                results["errors"].append("Start date must be before or equal to end date")
        
        # Check for future dates
        today = date.today()
        if results["parsed_end"] and results["parsed_end"] > today:
            results["errors"].append("End date cannot be in the future")
            
    except ValueError as e:
        results["is_valid"] = False
        results["errors"].append(f"Invalid date format: {e}")
    
    return results


def validate_ticker_symbol(ticker: str) -> Dict[str, Any]:
    """
    Validate ticker symbol format.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "is_valid": True,
        "errors": [],
        "normalized_ticker": ticker.upper().strip() if ticker else ""
    }
    
    if not ticker:
        results["is_valid"] = False
        results["errors"].append("Ticker symbol is required")
        return results
    
    normalized = results["normalized_ticker"]
    
    # Basic format validation
    if len(normalized) < 1 or len(normalized) > 10:
        results["is_valid"] = False
        results["errors"].append("Ticker symbol must be 1-10 characters")
    
    if not normalized.replace("^", "").replace(".", "").replace("-", "").isalnum():
        results["errors"].append("Ticker contains invalid characters")
    
    return results 