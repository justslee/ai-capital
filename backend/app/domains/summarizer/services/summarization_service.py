import logging
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import uuid # Import uuid module

# App imports  
from ....schemas.filings import SECFiling

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
        await self.db_service.create_table_if_not_exists()

        filing_to_process = self._get_filing_to_process(ticker, year, form_type)
        if not filing_to_process:
            raise FileNotFoundError(f"No filing found for {ticker} with specified criteria.")
        
        accession_number = filing_to_process.accession_number

        existing_metadata = await self.db_service.get_filing_metadata(accession_number)
        if existing_metadata and existing_metadata.processing_status == "completed":
            logger.info(f"Summary for {accession_number} already exists. Attempting to return public URL.")
            
            # If we have a stored public URL, use it. Otherwise, generate one.
            if existing_metadata.summary_presigned_url and existing_metadata.url_expiration and existing_metadata.url_expiration > datetime.now(timezone.utc):
                logger.info(f"Returning cached public URL for {accession_number}")
                return existing_metadata.summary_presigned_url

            # If no valid URL, generate and save it
            logger.info(f"Generating new public URL for {accession_number}")
            
            # Construct the S3 key from the file ID
            if not existing_metadata.summary_file_id:
                 # This can happen for older filings before the UUID change.
                 # To prevent errors, we can force re-processing or handle it gracefully.
                 # For now, we log an error and continue, which might cause a failure downstream.
                logger.error(f"Cannot generate URL for {accession_number} because summary_file_id is missing.")
                # Fallback to force re-processing could be an option.
                # Forcing reprocessing by clearing metadata could be an option:
                # existing_metadata = None 
                # Or we can just raise an error.
                raise ValueError(f"summary_file_id is missing for {accession_number}. Cannot generate URL.")

            s3_key = f"summaries/{existing_metadata.summary_file_id}.md"
            public_url = await self.s3_service.generate_presigned_url(s3_key)
            
            # Update metadata with the new permanent public URL
            existing_metadata.summary_presigned_url = public_url
            existing_metadata.url_expiration = datetime.now(timezone.utc) + timedelta(days=365 * 100) # Effectively permanent
            await self.db_service.save_filing_metadata(existing_metadata)
            
            return public_url

        # If metadata exists but is not complete, or doesn't exist, proceed with summarization.
        metadata = existing_metadata or FilingMetadata(
            accession_number=accession_number,
            ticker=filing_to_process.ticker,
            form_type=filing_to_process.form_type,
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
                    ticker=ticker,
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
                # Read the actual chunk text from S3
                chunk_text = await self.s3_service._get_object_content(chunk_meta.s3_path)
                if not chunk_text:
                    logger.warning(f"Could not read chunk text from {chunk_meta.s3_path}. Skipping.")
                    continue
                
                summary = await self.llm_orchestration_service.summarize_chunk(chunk_text, chunk_meta.section)
                chunk_summaries.append(summary)
            
            # REDUCE: Synthesize section summary
            section_summary = await self.llm_orchestration_service.synthesize_section_summary(chunk_summaries, section)
            section_summaries[section] = section_summary

        comprehensive_summary = await self.llm_orchestration_service.generate_comprehensive_summary(
            section_summaries, 
            ticker=metadata.ticker, 
            form_type=metadata.form_type
        )
        
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
        # Use a UUID for the S3 key to make it unguessable
        summary_file_id = str(uuid.uuid4())
        await self.s3_service.save_summary_document(comprehensive_summary, summary_file_id)

        # Step 4.2: Final Metadata Update
        metadata.summary_s3_path = await self.s3_service.generate_presigned_url(f"summaries/{summary_file_id}.md") # Now generates public URL
        metadata.summary_file_id = summary_file_id
        metadata.summary_presigned_url = metadata.summary_s3_path # Store the public URL here
        metadata.url_expiration = datetime.now(timezone.utc) + timedelta(days=365 * 100) # Set expiration far in the future
        metadata.processing_status = "completed"
        await self.db_service.save_filing_metadata(metadata)

        # Step 4.3: Return the public URL
        if metadata.summary_presigned_url:
            return metadata.summary_presigned_url
        else:
            raise Exception("Failed to generate public URL for the summary document.")

    def _get_filing_to_process(self, ticker: str, year: Optional[int], form_type: Optional[str]) -> Optional[SECFiling]:
        """
        Fetches real SEC filing data for the requested ticker using the SEC client.
        """
        from ...data_collection.clients.sec_client import get_sec_client
        
        sec_client = get_sec_client()

        # Determine which form types to search for - prioritize 10-K
        if form_type:
            form_types = [form_type]
        else:
            # Default to 10-K only for more comprehensive analysis
            form_types = ["10-K"]
        
        try:
            # Get filings from SEC
            filings = sec_client.get_company_filings_by_ticker(ticker, filing_types=form_types, count=20)
            
            if not filings:
                logger.warning(f"No filings found for ticker {ticker}")
                return None

            # Filter by year if specified
            if year:
                filings = [f for f in filings if str(year) in f["filing_date"]]
                if not filings:
                    logger.warning(f"No filings found for ticker {ticker} in year {year}")
                    return None
            
            # Get the most recent filing
            filing = filings[0]
            
            # Get CIK for the ticker
            from ....sec_utils import ticker_to_cik
            cik = ticker_to_cik(ticker)
            
            return SECFiling(
                id=1,  # Not used anymore
                accession_number=filing["accession_number"],
                ticker=ticker.upper(),
                cik=cik,
                form_type=filing["form_type"],
                filing_date=datetime.strptime(filing["filing_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc),
                report_url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{filing['accession_number'].replace('-', '')}/{filing['primary_doc']}",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Error fetching filing data for {ticker}: {e}")
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