from pydantic import BaseModel
from typing import Optional

class ValuationResponse(BaseModel):
    ticker: str
    total_intrinsic_value: Optional[float] = None # Renamed for clarity
    shares_outstanding: Optional[float] = None # Added shares count used
    intrinsic_value_per_share: Optional[float] = None # Added per-share value
    message: Optional[str] = None # Optional message for errors or context 