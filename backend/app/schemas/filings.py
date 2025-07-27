from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SECFiling(BaseModel):
    """
    Pydantic model for representing an SEC filing's metadata.
    This is used for data transfer within the application.
    """
    id: Optional[int] = None # This might not be in every DB result
    accession_number: str
    ticker: str
    cik: str
    form_type: str
    filing_date: datetime
    report_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 