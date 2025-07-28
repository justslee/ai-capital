import logging
import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import uuid # Import uuid module
import re # For sanitizing titles

# App imports  
from ....schemas.filings import SECFiling

# Domain imports
from ..models.metadata import FilingMetadata, ChunkMetadata
from .dynamodb_service import DynamoDBMetadataService, get_db_metadata_service
from .parsing_service import DocumentParsingService, get_parsing_service
from .chunking_service import ChunkingService, get_chunking_service
from .summarization_chunking_service import SummarizationChunkingService, get_summarization_chunking_service
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
        self.chunking_service: ChunkingService = get_chunking_service()  # For embeddings
        self.summarization_chunking_service: SummarizationChunkingService = get_summarization_chunking_service()  # For summarization
        self.s3_service: S3StorageService = get_s3_storage_service()
        self.llm_orchestration_service: LLMOrchestrationService = get_llm_orchestration_service()
        self.embedding_service: EmbeddingService = get_embedding_service()

    def _sanitize_title_for_path(self, title: str, max_length: int = 15) -> str:
        """Sanitizes a section title for use in a file path."""
        if not title:
            return "untitled"
        # Replace spaces and common separators with underscores
        title = re.sub(r'[\\s/\\:]+', '_', title)
        # Remove any characters that are not alphanumeric, underscore, or hyphen
        sanitized_title = re.sub(r'[^\w\\-_]', '', title)
        # Truncate to max_length
        return sanitized_title[:max_length]

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

        # --- Dual Chunking and Storage ---
        if not metadata.chunks:
            metadata.processing_status = "chunking"
            await self.db_service.save_filing_metadata(metadata)
            
            # Get ALL sections for embeddings (complete text for Q&A)
            all_sections = await self.parsing_service.get_filing_sections(
                ticker, accession_number, filing_to_process.form_type, 
                filter_for_summarization=False
            )
            
            # Get FILTERED sections for summarization (only key Items for 10-K)
            summarization_sections = await self.parsing_service.get_filing_sections(
                ticker, accession_number, filing_to_process.form_type, 
                filter_for_summarization=(filing_to_process.form_type == '10-K')
            )
            
            logger.info(f"Total sections for embeddings: {len(all_sections)}")
            logger.info(f"Filtered sections for summarization: {len(summarization_sections)}")
            
            # Create chunks from filtered sections for summarization
            summarization_chunks = self.summarization_chunking_service.chunk_for_summarization(
                summarization_sections
            )
            
            # Create chunks from ALL sections for embeddings
            embedding_chunks = self.summarization_chunking_service.chunk_for_embeddings(
                all_sections
            )
            
            # Store summarization chunks (large chunks) with metadata for processing
            summarization_metadata_list = []
            embedding_metadata_list = []
            
            # Process summarization chunks (used for the LLM summarization pipeline)
            for section_title, section_chunks in summarization_chunks.items():
                sanitized_section_title = self._sanitize_title_for_path(section_title)
                for chunk_doc in section_chunks:
                    chunk_text = chunk_doc.page_content
                    chunk_index = chunk_doc.metadata.get("chunk_index", 0)
                    
                    # Create S3 key for summarization chunk
                    s3_key = f"chunks/summarization/{ticker}/{accession_number}/{sanitized_section_title}_{chunk_index}.txt"
                    await self.s3_service.save_text_chunk(chunk_text, s3_key)
                    
                    # Create metadata for summarization chunk
                    chunk_meta = ChunkMetadata(
                        chunk_id=f"{accession_number}_{sanitized_section_title}_{chunk_index}_summarization",
                        filing_accession_number=accession_number,
                        ticker=ticker,
                        section=section_title,
                        chunk_index=chunk_index,
                        s3_path=s3_key,
                        character_count=len(chunk_text)
                    )
                    summarization_metadata_list.append(chunk_meta)

            # Process embedding chunks (used for RAG/Q&A)
            for section_title, section_chunks in embedding_chunks.items():
                sanitized_section_title = self._sanitize_title_for_path(section_title)
                for chunk_doc in section_chunks:
                    chunk_text = chunk_doc.page_content
                    chunk_index = chunk_doc.metadata.get("chunk_index", 0)
                    
                    # Create S3 key for embedding chunk
                    s3_key = f"chunks/embedding/{ticker}/{accession_number}/{sanitized_section_title}_{chunk_index}.txt"
                    await self.s3_service.save_text_chunk(chunk_text, s3_key)
                    
                    # Create metadata for embedding chunk
                    chunk_meta = ChunkMetadata(
                        chunk_id=f"{accession_number}_{sanitized_section_title}_{chunk_index}_embedding",
                        filing_accession_number=accession_number,
                        ticker=ticker,
                        section=section_title,
                        chunk_index=chunk_index,
                        s3_path=s3_key,
                        character_count=len(chunk_text)
                    )
                    embedding_metadata_list.append(chunk_meta)

            # Store summarization chunks in metadata for the summarization pipeline
            metadata.chunks = summarization_metadata_list
            # Store embedding chunks separately for the embedding pipeline
            metadata.embedding_chunks = embedding_metadata_list
            metadata.processing_status = "chunking_complete"
            await self.db_service.save_filing_metadata(metadata)
        
        # --- Summarization Orchestration ---
        metadata.processing_status = "summarizing"
        await self.db_service.save_filing_metadata(metadata)

        # Group chunks by section for map-reduce
        chunks_by_section = defaultdict(list)
        for chunk_meta in metadata.chunks:
            chunks_by_section[chunk_meta.section].append(chunk_meta)

        # Process sections concurrently with rate limiting
        section_summaries = await self._process_sections_concurrently(chunks_by_section)

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
        
        # Use embedding chunks (smaller, more precise) for better RAG performance
        await self.embedding_service.generate_and_store_embeddings(metadata.embedding_chunks)
        
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

    async def _process_sections_concurrently(self, chunks_by_section: Dict) -> Dict[str, str]:
        """
        Process all sections concurrently with rate limiting for optimal performance.
        
        :param chunks_by_section: Dictionary mapping section names to chunk metadata
        :return: Dictionary mapping section names to their summaries
        """
        logger.info(f"Processing {len(chunks_by_section)} sections concurrently")
        
        # Create semaphore for rate limiting (max 2 concurrent LLM calls)
        semaphore = asyncio.Semaphore(2)
        
        # Process all sections concurrently
        section_tasks = []
        for section, chunks_in_section in chunks_by_section.items():
            task = self._process_section_with_rate_limit(section, chunks_in_section, semaphore)
            section_tasks.append((section, task))
        
        # Wait for all sections to complete
        section_summaries = {}
        for section, task in section_tasks:
            try:
                section_summary = await task
                section_summaries[section] = section_summary
                logger.info(f"Completed processing section: {section}")
            except Exception as e:
                logger.error(f"Error processing section {section}: {e}")
                section_summaries[section] = f"Error processing section: {str(e)}"
        
        logger.info(f"Completed processing all {len(section_summaries)} sections")
        return section_summaries

    async def _process_section_with_rate_limit(self, section: str, chunks_in_section: list, semaphore: asyncio.Semaphore) -> str:
        """
        Process a single section's chunks concurrently with rate limiting.
        
        :param section: Section name
        :param chunks_in_section: List of chunk metadata for this section
        :param semaphore: Semaphore for rate limiting
        :return: Section summary
        """
        logger.info(f"Processing section '{section}' with {len(chunks_in_section)} chunks")
        
        # Process all chunks in this section concurrently
        chunk_tasks = []
        for chunk_meta in chunks_in_section:
            task = self._process_chunk_with_rate_limit(chunk_meta, section, semaphore)
            chunk_tasks.append(task)
        
        # Wait for all chunks in this section to complete
        chunk_summaries = await asyncio.gather(*chunk_tasks, return_exceptions=True)
        
        # Filter out exceptions and None values
        valid_summaries = []
        for i, summary in enumerate(chunk_summaries):
            if isinstance(summary, Exception):
                logger.error(f"Error processing chunk {i} in section {section}: {summary}")
            elif summary and summary.strip():
                valid_summaries.append(summary)
        
        if not valid_summaries:
            logger.warning(f"No valid chunk summaries for section '{section}'")
            return f"No content available for section: {section}"
        
        # REDUCE: Synthesize section summary from chunk summaries
        logger.info(f"Synthesizing {len(valid_summaries)} chunk summaries for section '{section}'")
        section_summary = await self.llm_orchestration_service.synthesize_section_summary(valid_summaries, section)
        
        return section_summary

    async def _process_chunk_with_rate_limit(self, chunk_meta, section: str, semaphore: asyncio.Semaphore) -> Optional[str]:
        """
        Process a single chunk with rate limiting and error handling.
        
        :param chunk_meta: Chunk metadata containing S3 path
        :param section: Section name for context
        :param semaphore: Semaphore for rate limiting
        :return: Chunk summary or None if failed
        """
        async with semaphore:
            try:
                # Add small delay to avoid overwhelming the API
                await asyncio.sleep(0.1)
                
                # Read the actual chunk text from S3
                chunk_text = await self.s3_service._get_object_content(chunk_meta.s3_path)
                if not chunk_text:
                    logger.warning(f"Could not read chunk text from {chunk_meta.s3_path}")
                    return None
                
                # Summarize the chunk
                summary = await self.llm_orchestration_service.summarize_chunk(chunk_text, section)
                
                if summary and summary.strip():
                    return summary
                else:
                    logger.warning(f"Empty summary returned for chunk in section {section}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error processing chunk in section {section}: {e}")
                # Implement exponential backoff for rate limit errors
                if "rate limit" in str(e).lower():
                    backoff_time = 2 ** (3)  # Start with 8 seconds
                    logger.info(f"Rate limit hit, backing off for {backoff_time} seconds")
                    await asyncio.sleep(backoff_time)
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