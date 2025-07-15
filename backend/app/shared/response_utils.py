"""Utility functions for creating standardized response patterns."""
from typing import Dict, Any, Optional

def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Create a success response with optional data and message."""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    return response

def error_response(error: str, data: Any = None) -> Dict[str, Any]:
    """Create an error response with error message and optional data."""
    response = {"success": False, "error": error}
    if data is not None:
        response["data"] = data
    return response

def prediction_response(
    predictions: list,
    confidence_intervals: Optional[dict] = None,
    model_info: Optional[dict] = None
) -> Dict[str, Any]:
    """Create a standardized prediction response."""
    response = {
        "success": True,
        "predictions": predictions
    }
    if confidence_intervals:
        response["confidence_intervals"] = confidence_intervals
    if model_info:
        response["model_info"] = model_info
    return response