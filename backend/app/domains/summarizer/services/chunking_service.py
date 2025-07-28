"""
Service for chunking HTML content using semantic-preserving splitting.
Enhanced to handle sec-parser semantic elements.
"""

import logging
from typing import Dict, List, Optional, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    Service responsible for splitting text from SEC filings into manageable chunks.
    """
    def __init__(self, max_chunk_size: int = 2000):
        """
        Initializes the service with a text splitter optimized for RAG and Q&A.
        
        :param max_chunk_size: The maximum number of characters in a chunk.
        """
        self.max_chunk_size = max_chunk_size
        
        chunk_overlap = max(150, int(max_chunk_size * 0.125))
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk_document(self, sections: Dict[str, str]) -> Dict[str, List[Document]]:
        """
        Chunks each section of the document into smaller, manageable pieces.
        
        :param sections: Dictionary mapping section titles to their aggregated text content.
        :return: Dictionary mapping section titles to lists of chunked Document objects.
        """
        logger.info(f"Starting chunking for {len(sections)} sections")
        
        chunked_sections = {}
        
        for section_title, section_content in sections.items():
            if not section_content or not section_content.strip():
                logger.warning(f"Section '{section_title}' is empty, skipping")
                continue

            chunks = self.text_splitter.split_text(section_content)
            
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "section": section_title,
                        "chunk_index": i
                    }
                )
                documents.append(doc)
            
            chunked_sections[section_title] = documents
            logger.info(f"Section '{section_title}' split into {len(documents)} chunks")

        total_chunks = sum(len(chunks) for chunks in chunked_sections.values())
        logger.info(f"Total chunks created: {total_chunks}")
        
        return chunked_sections


# Global instance for dependency injection
_chunking_service_instance: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    """
    Get or create a singleton instance of the chunking service.
    
    :return: ChunkingService instance.
    """
    global _chunking_service_instance
    if _chunking_service_instance is None:
        _chunking_service_instance = ChunkingService()
    return _chunking_service_instance 