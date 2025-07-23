"""
HTML Parsing Service for SEC Filings

This service is responsible for parsing the HTML content of SEC filings
to extract the text of specific sections, such as 'Business', 'MD&A',
and 'Risk Factors'. It uses BeautifulSoup for robust HTML parsing.
"""
import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Constants for section identification
# These can be expanded and made more robust over time
SECTION_MAPPINGS = {
    "business": ["business", "item 1", "item1"],
    "risk_factors": ["risk factors", "item 1a", "item1a"],
    "mdna": ["management's discussion and analysis", "md&a", "item 7", "item7"],
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

def get_parsing_service() -> SECFilingParsingService:
    """Provides a singleton instance of the SECFilingParsingService."""
    return SECFilingParsingService() 