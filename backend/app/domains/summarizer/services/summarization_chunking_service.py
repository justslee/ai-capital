"""
Service for dual chunking strategy: larger chunks for summarization, smaller chunks for embeddings.
"""

import logging
from typing import Dict, List, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger(__name__)


class SummarizationChunkingService:
    """
    Service responsible for creating two types of chunks:
    - Large chunks (8000 chars) optimized for LLM summarization
    - Small chunks (800 chars) optimized for embedding/RAG
    """
    
    def __init__(self, 
                 summarization_chunk_size: int = 8000,
                 embedding_chunk_size: int = 800):
        """
        Initialize dual chunking service.
        
        :param summarization_chunk_size: Size for summarization chunks (default 8000)
        :param embedding_chunk_size: Size for embedding chunks (default 800)
        """
        self.summarization_chunk_size = summarization_chunk_size
        self.embedding_chunk_size = embedding_chunk_size
        
        # Splitter for large chunks (summarization)
        summarization_overlap = max(400, int(summarization_chunk_size * 0.1))
        self.summarization_splitter = RecursiveCharacterTextSplitter(
            chunk_size=summarization_chunk_size,
            chunk_overlap=summarization_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Splitter for small chunks (embeddings/RAG)
        embedding_overlap = max(100, int(embedding_chunk_size * 0.125))
        self.embedding_splitter = RecursiveCharacterTextSplitter(
            chunk_size=embedding_chunk_size,
            chunk_overlap=embedding_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk_for_summarization(self, sections: Dict[str, str]) -> Dict[str, List[Document]]:
        """
        Create large chunks optimized for LLM summarization.
        
        :param sections: Dictionary mapping section titles to their content
        :return: Dictionary mapping section titles to lists of large Document chunks
        """
        logger.info(f"Creating summarization chunks (size: {self.summarization_chunk_size}) for {len(sections)} sections")
        
        chunked_sections = {}
        
        for section_title, section_content in sections.items():
            if not section_content or not section_content.strip():
                logger.warning(f"Section '{section_title}' is empty, skipping")
                continue

            chunks = self.summarization_splitter.split_text(section_content)
            
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "section": section_title,
                        "chunk_index": i,
                        "chunk_type": "summarization",
                        "character_count": len(chunk)
                    }
                )
                documents.append(doc)
            
            chunked_sections[section_title] = documents
            logger.info(f"Section '{section_title}' split into {len(documents)} summarization chunks")

        total_chunks = sum(len(chunks) for chunks in chunked_sections.values())
        logger.info(f"Total summarization chunks created: {total_chunks}")
        
        return chunked_sections

    def chunk_for_embeddings(self, sections: Dict[str, str]) -> Dict[str, List[Document]]:
        """
        Create small chunks optimized for embedding generation and RAG.
        
        :param sections: Dictionary mapping section titles to their content
        :return: Dictionary mapping section titles to lists of small Document chunks
        """
        logger.info(f"Creating embedding chunks (size: {self.embedding_chunk_size}) for {len(sections)} sections")
        
        chunked_sections = {}
        
        for section_title, section_content in sections.items():
            if not section_content or not section_content.strip():
                logger.warning(f"Section '{section_title}' is empty, skipping")
                continue

            chunks = self.embedding_splitter.split_text(section_content)
            
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "section": section_title,
                        "chunk_index": i,
                        "chunk_type": "embedding",
                        "character_count": len(chunk)
                    }
                )
                documents.append(doc)
            
            chunked_sections[section_title] = documents
            logger.info(f"Section '{section_title}' split into {len(documents)} embedding chunks")

        total_chunks = sum(len(chunks) for chunks in chunked_sections.values())
        logger.info(f"Total embedding chunks created: {total_chunks}")
        
        return chunked_sections

    def create_chunk_mapping(self, 
                           summarization_chunks: Dict[str, List[Document]], 
                           embedding_chunks: Dict[str, List[Document]]) -> Dict[str, List[str]]:
        """
        Create a mapping between summarization chunks and their corresponding embedding chunks.
        This helps track which small chunks contributed to each large chunk summary.
        
        :param summarization_chunks: Large chunks used for summarization
        :param embedding_chunks: Small chunks used for embeddings
        :return: Dictionary mapping summarization chunk IDs to lists of embedding chunk IDs
        """
        logger.info("Creating chunk mapping between summarization and embedding chunks")
        
        mapping = {}
        
        for section_title in summarization_chunks.keys():
            if section_title not in embedding_chunks:
                continue
                
            sum_chunks = summarization_chunks[section_title]
            emb_chunks = embedding_chunks[section_title]
            
            for sum_idx, sum_chunk in enumerate(sum_chunks):
                sum_chunk_id = f"{section_title}_{sum_idx}_summarization"
                mapping[sum_chunk_id] = []
                
                sum_start = sum_chunk.page_content[:100]  # First 100 chars
                sum_end = sum_chunk.page_content[-100:]   # Last 100 chars
                
                # Find embedding chunks that overlap with this summarization chunk
                for emb_idx, emb_chunk in enumerate(emb_chunks):
                    emb_content = emb_chunk.page_content
                    
                    # Simple overlap detection - check if embedding chunk content
                    # appears in the summarization chunk
                    if (sum_start in emb_content or 
                        sum_end in emb_content or 
                        emb_content[:50] in sum_chunk.page_content or
                        emb_content[-50:] in sum_chunk.page_content):
                        
                        emb_chunk_id = f"{section_title}_{emb_idx}_embedding"
                        mapping[sum_chunk_id].append(emb_chunk_id)
        
        total_mappings = sum(len(emb_list) for emb_list in mapping.values())
        logger.info(f"Created {len(mapping)} summarization chunks mapped to {total_mappings} embedding chunks")
        
        return mapping


# Global instance for dependency injection
_summarization_chunking_service_instance: Optional[SummarizationChunkingService] = None


def get_summarization_chunking_service() -> SummarizationChunkingService:
    """
    Get or create a singleton instance of the summarization chunking service.
    
    :return: SummarizationChunkingService instance
    """
    global _summarization_chunking_service_instance
    if _summarization_chunking_service_instance is None:
        _summarization_chunking_service_instance = SummarizationChunkingService()
    return _summarization_chunking_service_instance