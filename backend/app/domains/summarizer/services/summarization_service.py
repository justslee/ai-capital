import logging
from typing import Optional
from datetime import datetime

# App imports
from ....db.database_utils import db_cursor
from ....models.filings import SECFiling

# Domain imports
from ..models.metadata import FilingMetadata, ChunkMetadata
from .dynamodb_service import DynamoDBMetadataService, get_db_metadata_service
from .parsing_service import DocumentParsingService, get_parsing_service
from .chunking_service import SectionAwareChunkingService, get_chunking_service
from ...data_collection.storage.s3_storage_service import S3StorageService, get_s3_storage_service

logger = logging.getLogger(__name__)

class SummarizationService:
    """
    Orchestrates the entire summarization workflow, from fetching data
    to generating and storing summaries.
    """
    def __init__(self):
        """Initializes the service with its dependencies."""
        self.db_service: DynamoDBMetadataService = get_db_metadata_service()
        self.parsing_service: DocumentParsingService = get_parsing_service()
        self.chunking_service: SectionAwareChunkingService = get_chunking_service()
        self.s3_service: S3StorageService = get_s3_storage_service()
        # self.orchestration_service = get_orchestration_service()

    async def get_summary(self, ticker: str, year: Optional[int] = None, form_type: Optional[str] = None) -> str:
        """
        Main entry point for the summarization workflow.
        """
        logger.info(f"Starting summarization for {ticker} (Year: {year}, Form: {form_type})")

        await self.db_service.create_table_if_not_exists()

        filing_to_process = self._get_filing_to_process(ticker, year, form_type)
        if not filing_to_process:
            raise FileNotFoundError(f"No filing found for {ticker} with specified criteria.")
        
        accession_number = filing_to_process.accession_number

        # Check if metadata (and thus summary) already exists
        existing_metadata = await self.db_service.get_filing_metadata(accession_number)
        if existing_metadata and existing_metadata.processing_status == "completed":
            logger.info(f"Summary for {accession_number} already exists. Returning cached S3 path.")
            return existing_metadata.summary_s3_path or "s3://path-not-found-but-summary-exists"

        # Create new metadata if it doesn't exist
        metadata = existing_metadata or FilingMetadata(
            accession_number=accession_number,
            ticker=filing_to_process.ticker,
            form_type=filing_to_process.filing_type,
            filing_date=filing_to_process.filing_date
        )

        # Start processing
        metadata.processing_status = "chunking"
        await self.db_service.save_filing_metadata(metadata)
        
        sections = await self.parsing_service.get_filing_sections(ticker, accession_number)
        chunks = self.chunking_service.chunk_document(sections)

        chunk_metadata_list = []
        for i, chunk in enumerate(chunks):
            s3_key = f"chunks/{ticker}/{accession_number}/{chunk.section}/{chunk.chunk_index}.txt"
            await self.s3_service.save_text_chunk(chunk.text, s3_key)
            
            chunk_meta = ChunkMetadata(
                chunk_id=f"{accession_number}_{chunk.section}_{i}",
                filing_accession_number=accession_number,
                section=chunk.section,
                chunk_index=i,
                s3_path=s3_key,
                character_count=len(chunk.text)
            )
            chunk_metadata_list.append(chunk_meta)

        # Update metadata with chunk information
        metadata.chunks = chunk_metadata_list
        metadata.processing_status = "chunking_complete"
        await self.db_service.save_filing_metadata(metadata)

        # TODO: Start the summarization orchestration

        return f"s3://placeholder-for-{accession_number}"

    def _get_filing_to_process(self, ticker: str, year: Optional[int], form_type: Optional[str]) -> Optional[SECFiling]:
        """
        Queries the database to find the appropriate filing.
        """
        with db_cursor() as cursor:
            if year and form_type:
                sql = """SELECT * FROM sec_filings WHERE ticker = %s AND filing_type = %s AND EXTRACT(YEAR FROM filing_date) = %s ORDER BY filing_date DESC LIMIT 1"""
                params = (ticker.upper(), form_type.upper(), year)
            else:
                sql = """SELECT * FROM sec_filings WHERE ticker = %s ORDER BY filing_date DESC LIMIT 1"""
                params = (ticker.upper(),)
            
            cursor.execute(sql, params)
            result = cursor.fetchone()
            
            if result:
                # Assuming SECFiling model can be created from the DB row
                # This needs to be adjusted if your model doesn't match the table columns
                # For now, we'll manually map fields
                return SECFiling(
                    id=result['id'],
                    accession_number=result['accession_number'],
                    ticker=result['ticker'],
                    cik=result['cik'],
                    form_type=result['filing_type'],
                    filing_date=result['filing_date'],
                    report_url=result['report_url'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                )
            return None

# Singleton instance
_summarization_service: Optional[SummarizationService] = None

def get_summarization_service() -> "SummarizationService":
    """
    Provides a singleton instance of the SummarizationService.
    """
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService()
    return _summarization_service 