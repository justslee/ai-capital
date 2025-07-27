import logging
import os
from typing import List, Optional

from ..models.metadata import ChunkMetadata
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

# Local imports
from ...data_collection.storage.s3_storage_service import S3StorageService, get_s3_storage_service
from app.shared.exceptions import APIKeyMissingException

logger = logging.getLogger(__name__)

# --- Configuration ---
MODEL_NAME = 'all-MiniLM-L6-v2'
VECTOR_DIMENSION = 384
BATCH_SIZE = 32
PINECONE_INDEX_NAME = "ai-capital-sec-filings"

class EmbeddingService:
    """
    Service responsible for generating and storing text embeddings.
    """
    def __init__(self):
        """
        Initializes the EmbeddingService with the model and Pinecone client.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Loading SentenceTransformer model: {MODEL_NAME}...")
        
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if not pinecone_api_key:
            raise APIKeyMissingException(service="Pinecone", key_name="PINECONE_API_KEY")
            
        self.model = SentenceTransformer(MODEL_NAME)
        self.pinecone = Pinecone(api_key=pinecone_api_key)
        self.s3_service: S3StorageService = get_s3_storage_service()
        self._init_pinecone_index()

    def _init_pinecone_index(self):
        """Creates the Pinecone index if it doesn't exist."""
        existing_indexes = [index.name for index in self.pinecone.list_indexes()]
        if PINECONE_INDEX_NAME not in existing_indexes:
            logger.info(f"Pinecone index '{PINECONE_INDEX_NAME}' not found. Creating...")
            self.pinecone.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=VECTOR_DIMENSION,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            logger.info(f"Pinecone index '{PINECONE_INDEX_NAME}' created.")
        else:
            logger.info(f"Found existing Pinecone index: '{PINECONE_INDEX_NAME}'.")
        self.index = self.pinecone.Index(PINECONE_INDEX_NAME)

    async def generate_and_store_embeddings(self, chunks: List[ChunkMetadata]):
        """
        Generates embeddings for a list of text chunks and stores them in Pinecone.
        """
        if not chunks:
            logger.warning("No chunks provided to generate embeddings for.")
            return

        logger.info(f"Generating and storing embeddings for {len(chunks)} chunks.")
        
        vectors_to_upsert = []
        for i in range(0, len(chunks), BATCH_SIZE):
            batch_chunks = chunks[i:i + BATCH_SIZE]
            
            # 1. Fetch chunk texts from S3
            chunk_texts = [await self.s3_service._get_object_content(chunk.s3_path) for chunk in batch_chunks]
            
            # Filter out any chunks that failed to download
            valid_texts = [text for text in chunk_texts if text is not None]
            if not valid_texts:
                continue

            # 2. Generate embeddings
            embeddings = self.model.encode(valid_texts, show_progress_bar=False)
            
            # 3. Prepare vectors for upsert
            for chunk, embedding in zip(batch_chunks, embeddings):
                vectors_to_upsert.append({
                    "id": chunk.chunk_id,
                    "values": embedding.tolist(),
                    "metadata": {
                        "ticker": chunk.ticker,
                        "accession_number": chunk.filing_accession_number,
                        "section": chunk.section,
                        "chunk_index": chunk.chunk_index,
                        "s3_path": chunk.s3_path,
                        "character_count": chunk.character_count
                    }
                })
        
        # 4. Upsert to Pinecone
        if vectors_to_upsert:
            logger.info(f"Upserting {len(vectors_to_upsert)} vectors to Pinecone.")
            self.index.upsert(vectors=vectors_to_upsert, namespace="sec-filings")
            logger.info("Upsert to Pinecone complete.")

# Singleton instance
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> "EmbeddingService":
    """
    Provides a singleton instance of the EmbeddingService.
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service 