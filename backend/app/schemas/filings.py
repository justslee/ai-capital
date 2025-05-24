from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class SECFiling(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "accession_number": "0001193125-23-000001",
                "company_name": "Apple Inc.",
                "ticker": "AAPL",
                "cik": "0000320193",
                "filing_type": "10-K",
                "filing_date": "2023-11-03T00:00:00",
                "form_url": "https://www.sec.gov/Archives/edgar/data/320193/000119312523000001/aapl-20230930.htm",
                "raw_html": "<html>...</html>"
            }
        }
    )

    accession_number: str  # Primary key
    company_name: str
    ticker: str
    cik: str
    filing_type: str  # e.g., '10-K', '10-Q', '8-K'
    filing_date: datetime
    form_url: str
    raw_html: Optional[str] = None  # Optional as we might not want to store the full HTML in memory
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow) 