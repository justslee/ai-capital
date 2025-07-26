import logging
from typing import List, Optional, Dict, NamedTuple
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class Chunk(NamedTuple):
    """
    A structured representation of a text chunk.
    """
    text: str
    section: str
    chunk_index: int

class SectionAwareChunkingService:
    """
    Service responsible for splitting a dictionary of text sections into smaller chunks.
    """
    def __init__(self, chunk_size: int = 4000, chunk_overlap: int = 200):
        """
        Initializes the service with a text splitter.

        :param chunk_size: The maximum number of characters in a chunk.
        :param chunk_overlap: The number of characters to overlap between chunks.
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def chunk_document(self, sections: Dict[str, str]) -> List[Chunk]:
        """
        Splits a document (represented as a dictionary of sections) into a list of chunks.

        :param sections: A dictionary where keys are section names and values are their text content.
        :return: A list of structured Chunk objects.
        """
        all_chunks = []
        for section_name, section_text in sections.items():
            if not section_text:
                logger.warning(f"Section '{section_name}' is empty, skipping chunking.")
                continue

            logger.info(f"Chunking section '{section_name}' of length {len(section_text)}.")
            
            text_chunks = self.text_splitter.split_text(section_text)
            
            for i, chunk_text in enumerate(text_chunks):
                all_chunks.append(Chunk(
                    text=chunk_text,
                    section=section_name,
                    chunk_index=i
                ))
        
        logger.info(f"Successfully created {len(all_chunks)} chunks from {len(sections)} sections.")
        return all_chunks

# Singleton instance
_chunking_service: Optional[SectionAwareChunkingService] = None

def get_chunking_service() -> "SectionAwareChunkingService":
    """
    Provides a singleton instance of the SectionAwareChunkingService.
    """
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = SectionAwareChunkingService()
    return _chunking_service 