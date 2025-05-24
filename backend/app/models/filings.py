from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from backend.app.db.base_class import Base

class SECFilingDB(Base):
    __tablename__ = "sec_filings"

    accession_number = Column(String, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    ticker = Column(String, nullable=False, index=True)
    cik = Column(String, nullable=False, index=True)
    filing_type = Column(String, nullable=False, index=True)
    filing_date = Column(DateTime, nullable=False, index=True)
    form_url = Column(String, nullable=False)
    raw_html = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<SECFiling(accession_number='{self.accession_number}', company_name='{self.company_name}', filing_type='{self.filing_type}')>" 