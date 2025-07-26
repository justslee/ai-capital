from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ChunkMetadata(BaseModel):
    """
    Represents metadata for a single chunk of a document.
    """
    chunk_id: str = Field(..., description="Unique identifier for the chunk (e.g., {accession_number}_{section}_{index})")
    filing_accession_number: str = Field(..., description="The accession number of the parent filing.")
    section: str = Field(..., description="The section of the filing this chunk belongs to (e.g., 'Business', 'Risk Factors').")
    chunk_index: int = Field(..., description="The zero-based index of the chunk within its section.")
    s3_path: str = Field(..., description="The S3 path where the raw text of the chunk is stored.")
    character_count: int = Field(..., description="Number of characters in the chunk.")
    token_count: Optional[int] = Field(None, description="Estimated number of tokens in the chunk.")
    embedding_status: str = Field(default="pending", description="Status of the embedding generation (e.g., 'pending', 'completed', 'failed').")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FilingMetadata(BaseModel):
    """
    Represents metadata for a single SEC filing and its summarization status.
    This will be the primary item in our DynamoDB table.
    """
    accession_number: str = Field(..., description="Primary key. The unique identifier for the filing.")
    ticker: str = Field(..., description="The stock ticker symbol.")
    form_type: str = Field(..., description="The SEC form type (e.g., '10-K', '10-Q').")
    filing_date: datetime = Field(..., description="The date the filing was published.")
    
    # Summarization status
    processing_status: str = Field(default="pending", description="Overall status of the summarization process (e.g., 'pending', 'chunking', 'summarizing', 'embedding', 'completed', 'failed').")
    summary_s3_path: Optional[str] = Field(None, description="The S3 path to the final comprehensive summary document.")
    
    # List of chunks associated with this filing
    chunks: List[ChunkMetadata] = Field(default=[], description="A list of metadata for all chunks derived from this filing.")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        # Pydantic configuration to allow creating models from dictionary
        from_attributes = True 