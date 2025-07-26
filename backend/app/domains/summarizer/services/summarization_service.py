import logging
from typing import Optional, Dict
from datetime import datetime
from collections import defaultdict

# App imports
from ....db.database_utils import db_cursor
from ....models.filings import SECFiling

# Domain imports
from ..models.metadata import FilingMetadata, ChunkMetadata
from .dynamodb_service import DynamoDBMetadataService, get_db_metadata_service
from .parsing_service import DocumentParsingService, get_parsing_service
from .chunking_service import SectionAwareChunkingService, get_chunking_service
from .llm_orchestration_service import LLMOrchestrationService, get_llm_orchestration_service
from .embedding_service import EmbeddingService, get_embedding_service
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
        self.llm_orchestration_service: LLMOrchestrationService = get_llm_orchestration_service()
        self.embedding_service: EmbeddingService = get_embedding_service()

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

        existing_metadata = await self.db_service.get_filing_metadata(accession_number)
        if existing_metadata and existing_metadata.processing_status == "completed":
            logger.info(f"Summary for {accession_number} already exists. Returning cached S3 path.")
            return existing_metadata.summary_s3_path or "s3://path-not-found-but-summary-exists"

        metadata = existing_metadata or FilingMetadata(
            accession_number=accession_number,
            ticker=filing_to_process.ticker,
            form_type=filing_to_process.filing_type,
            filing_date=filing_to_process.filing_date
        )
        
        # --- Chunking and Storage ---
        if not metadata.chunks:
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

            metadata.chunks = chunk_metadata_list
            metadata.processing_status = "chunking_complete"
            await self.db_service.save_filing_metadata(metadata)
        
        # --- Summarization Orchestration ---
        metadata.processing_status = "summarizing"
        await self.db_service.save_filing_metadata(metadata)

        # Group chunks by section for map-reduce
        chunks_by_section = defaultdict(list)
        for chunk_meta in metadata.chunks:
            chunks_by_section[chunk_meta.section].append(chunk_meta)

        section_summaries = {}
        for section, chunks_in_section in chunks_by_section.items():
            # MAP: Summarize each chunk
            chunk_summaries = []
            for chunk_meta in chunks_in_section:
                # In a real scenario, you'd read the text from S3. For now, this is a placeholder.
                chunk_text = f"Text from {chunk_meta.s3_path}" 
                summary = await self.llm_orchestration_service.summarize_chunk(chunk_text)
                chunk_summaries.append(summary)
            
            # REDUCE: Synthesize section summary
            section_summary = await self.llm_orchestration_service.synthesize_section_summary(chunk_summaries)
            section_summaries[section] = section_summary

        comprehensive_summary = await self.llm_orchestration_service.generate_comprehensive_summary(section_summaries)
        
        metadata.processing_status = "summarization_complete"
        await self.db_service.save_filing_metadata(metadata)

        # --- Embedding Generation (Fire and Forget) ---
        logger.info("Initiating embedding generation in the background.")
        metadata.processing_status = "embedding"
        await self.db_service.save_filing_metadata(metadata)
        
        await self.embedding_service.generate_and_store_embeddings(metadata.chunks)
        
        # This status update might happen in a separate callback/worker in a real system
        metadata.processing_status = "embedding_complete"
        await self.db_service.save_filing_metadata(metadata)

        # Step 4.1: Store comprehensive_summary in S3
        summary_s3_key = f"summaries/{ticker}/{accession_number}.md"
        await self.s3_service.save_summary_document(comprehensive_summary, summary_s3_key)

        # Step 4.2: Final Metadata Update
        metadata.summary_s3_path = summary_s3_key
        metadata.processing_status = "completed"
        await self.db_service.save_filing_metadata(metadata)

        # Step 4.3: Return a presigned URL
        presigned_url = await self.s3_service.generate_presigned_url(summary_s3_key)
        if not presigned_url:
            raise Exception("Failed to generate presigned URL for the summary document.")

        return presigned_url

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