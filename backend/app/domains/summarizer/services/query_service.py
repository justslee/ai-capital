"""
Service for handling user queries using a RAG pipeline.
"""
import logging
from typing import Dict, List, Optional

from ...data_collection.storage.s3_storage_service import S3StorageService, get_s3_storage_service
from .embedding_service import EmbeddingService, get_embedding_service
from .llm_orchestration_service import LLMOrchestrationService, get_llm_orchestration_service

logger = logging.getLogger(__name__)

class QueryService:
    """
    Service to handle user queries by retrieving relevant text chunks
    and generating an answer using an LLM.
    """
    def __init__(self):
        """Initializes the service with its dependencies."""
        self.embedding_service: EmbeddingService = get_embedding_service()
        self.s3_service: S3StorageService = get_s3_storage_service()
        self.llm_orchestration_service: LLMOrchestrationService = get_llm_orchestration_service()

    async def answer_question(self, ticker: str, query: str, top_k: int = 5) -> Dict:
        """
        Answers a user's question based on the indexed SEC filings.
        
        :param ticker: The stock ticker to focus the search on.
        :param query: The user's question.
        :param top_k: The number of top chunks to retrieve.
        :return: A dictionary containing the answer and the sources.
        """
        logger.info(f"Answering question for {ticker}: '{query}'")

        # 1. Embed the user's query
        query_embedding = self.embedding_service.model.encode(query, show_progress_bar=False).tolist()

        # 2. Query Pinecone for relevant chunks
        retrieved_chunks = await self.embedding_service.query_pinecone(
            embedding=query_embedding,
            ticker=ticker,
            top_k=top_k
        )

        if not retrieved_chunks:
            return {"answer": "Could not find any relevant information in the filings.", "sources": []}

        # 3. Fetch the text of the chunks from S3
        context_parts = []
        sources = []
        for chunk_id, score in retrieved_chunks:
            # The chunk_id is the s3_key, which is how we stored it
            s3_path = chunk_id
            chunk_text = await self.s3_service._get_object_content(s3_path)
            if chunk_text:
                context_parts.append(chunk_text)
                sources.append({"s3_path": s3_path, "score": score})

        context = "\n\n---\n\n".join(context_parts)

        # 4. Generate an answer using the LLM
        answer = await self.llm_orchestration_service.answer_question_with_context(query, context)

        return {"answer": answer, "sources": sources}

# Singleton instance
_query_service: Optional[QueryService] = None

def get_query_service() -> "QueryService":
    """
    Provides a singleton instance of the QueryService.
    """
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service 