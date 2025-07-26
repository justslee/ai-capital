"""
HTML Parsing Service for SEC Filings

This service is responsible for parsing the HTML content of SEC filings
to extract the text of specific sections, such as 'Business', 'MD&A',
and 'Risk Factors'. It uses BeautifulSoup for robust HTML parsing.
"""
import logging
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

# Add the project root to the Python path if necessary
# import sys, os
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from ...data_collection.storage.s3_storage_service import S3StorageService, get_s3_storage_service

logger = logging.getLogger(__name__)

# Constants for section identification
# These can be expanded and made more robust over time
SECTION_MAPPINGS = {
    "business": ["business", "item 1", "item1"],
    "risk_factors": ["risk factors", "item 1a", "item1a"],
    "mdna": ["management's discussion and analysis", "md&a", "item 7", "item7"],
}

# Common section headers in SEC filings (case-insensitive regex)
# This list can be expanded and refined
SECTION_PATTERNS = {
    "Business": re.compile(r"(?i)(item\s+1\.\s+business)"),
    "Risk Factors": re.compile(r"(?i)(item\s+1a\.\s+risk\s+factors)"),
    "MD&A": re.compile(r"(?i)(item\s+7\.\s+management\'s\s+discussion\s+and\s+analysis)"),
    # Add other relevant sections like Financial Statements, etc.
}


class SECFilingParsingService:
    """A service for parsing HTML SEC filings."""

    def extract_sections(self, html_content: str, sections_to_extract: List[str]) -> Dict[str, str]:
        """
        Extracts the text content of specified sections from the HTML of an SEC filing.

        Args:
            html_content: The raw HTML content of the filing.
            sections_to_extract: A list of section keys to extract (e.g., ['business', 'mdna']).

        Returns:
            A dictionary where keys are the requested section keys and values
            are the extracted text content of those sections.
        """
        if not html_content:
            logger.warning("HTML content is empty. Cannot extract sections.")
            return {}

        soup = BeautifulSoup(html_content, 'lxml')
        extracted_sections = {}

        for section_key in sections_to_extract:
            section_text = self._find_section_text(soup, section_key)
            if section_text:
                extracted_sections[section_key] = section_text
            else:
                logger.warning(f"Could not find or extract section: {section_key}")

        return extracted_sections

    def _find_section_text(self, soup: BeautifulSoup, section_key: str) -> Optional[str]:
        """
        Finds the text for a given section by searching for common header patterns.
        This is a simplified implementation and can be made more sophisticated.
        """
        search_terms = SECTION_MAPPINGS.get(section_key.lower(), [])
        
        for term in search_terms:
            # A common pattern is a header (h2, h3, etc.) or a bold tag containing the section title
            # This is a very basic search and would need to be improved for production use
            header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'strong', 'b'] and term in tag.get_text().lower())
            
            if header:
                # Once the header is found, we can try to extract the content that follows it
                # This is a naive implementation that just takes the text of the next few paragraphs
                content = []
                for sibling in header.find_next_siblings():
                    if sibling.name in ['h2', 'h3', 'h4']: # Stop at the next header
                        break
                    if sibling.name == 'p':
                        content.append(sibling.get_text(strip=True))
                
                if content:
                    return " ".join(content)

        return None

class DocumentParsingService:
    """
    Service responsible for fetching raw documents and parsing them into clean, section-aware text.
    """
    def __init__(self, s3_storage_service: S3StorageService):
        """Initializes the service with a dependency on the S3 storage service."""
        self.s3_service = s3_storage_service

    async def get_filing_sections(self, ticker: str, accession_number: str) -> Dict[str, str]:
        """
        Fetches a filing's HTML, parses it, and splits it into sections.

        :param ticker: The stock ticker.
        :param accession_number: The filing's accession number.
        :return: A dictionary where keys are section names and values are the text content.
        """
        logger.info(f"Fetching filing HTML for {ticker} ({accession_number}) from S3.")
        html_content = await self.s3_service.get_filing_html(ticker, accession_number)
        
        if not html_content:
            raise ValueError(f"Could not retrieve HTML for {accession_number} from S3.")

        logger.info("Parsing HTML and splitting into sections.")
        text = self._extract_text_from_html(html_content)
        return self._split_text_into_sections(text)

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Uses BeautifulSoup to parse HTML and extract all text.

        :param html_content: The HTML content as a string.
        :return: The extracted text.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text

    def _split_text_into_sections(self, text: str) -> Dict[str, str]:
        """
        Splits a large text into a dictionary of sections based on predefined patterns.
        """
        sections = {}
        # Use a placeholder for text before the first identified section if needed
        last_match_end = 0
        
        # Find all matches for all patterns to order them correctly
        all_matches = []
        for name, pattern in SECTION_PATTERNS.items():
            for match in pattern.finditer(text):
                all_matches.append((match.start(), match.end(), name))
        
        all_matches.sort()

        if not all_matches:
            logger.warning("No section headers found in the document. Returning as a single 'Unknown' section.")
            return {"Unknown": text}
            
        # Add a placeholder for text before the first section header
        if all_matches[0][0] > 0:
            sections["Preamble"] = text[:all_matches[0][0]].strip()

        for i in range(len(all_matches)):
            start, end, name = all_matches[i]
            
            # The content of this section is from its header to the start of the next one
            next_section_start = all_matches[i+1][0] if i + 1 < len(all_matches) else len(text)
            section_content = text[end:next_section_start].strip()
            
            sections[name] = section_content
            
        logger.info(f"Successfully identified {len(sections)} sections.")
        return sections

# Singleton instance
_parsing_service: Optional[DocumentParsingService] = None

def get_parsing_service() -> "DocumentParsingService":
    """
    Provides a singleton instance of the DocumentParsingService.
    """
    global _parsing_service
    if _parsing_service is None:
        s3_service = get_s3_storage_service()
        _parsing_service = DocumentParsingService(s3_service)
    return _parsing_service 