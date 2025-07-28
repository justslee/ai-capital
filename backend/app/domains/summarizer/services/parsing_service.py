"""
HTML Parsing Service for SEC Filings

This service is responsible for parsing the HTML content of SEC filings
to extract sections based on their semantic structure.
"""
import logging
from typing import Dict, Optional, List

from ...data_collection.storage.s3_storage_service import S3StorageService, get_s3_storage_service
from .sec_parser_service import SecParserService, get_sec_parser_service

logger = logging.getLogger(__name__)


class DocumentParsingService:
    """
    Service responsible for fetching raw documents and parsing them into clean, section-aware text.
    """
    def __init__(self, s3_storage_service: S3StorageService):
        """Initializes the service with a dependency on the S3 storage service."""
        self.s3_service = s3_storage_service
        self.sec_parser_service = get_sec_parser_service()

    async def get_filing_sections(self, ticker: str, accession_number: str, form_type: str = '10-Q', 
                                filter_for_summarization: bool = False) -> Dict[str, str]:
        """
        Fetches a filing's HTML, parses it, and splits it into sections using semantic parsing.
        Downloads from SEC if not in S3.

        :param ticker: The stock ticker.
        :param accession_number: The filing's accession number.
        :param form_type: The type of filing (10-Q, 10-K, etc.)
        :param filter_for_summarization: If True, only return sections under key Items for 10-K
        :return: A dictionary where keys are section titles and values are the aggregated text content.
        """
        logger.info(f"Fetching filing HTML for {ticker} ({accession_number}) from S3.")
        html_content = await self.s3_service.get_filing_html(ticker, accession_number)
        
        if not html_content:
            logger.info(f"HTML not found in S3, downloading from SEC for {accession_number}")
            html_content = await self._download_filing_from_sec(ticker, accession_number, form_type)
            
            if not html_content:
                raise ValueError(f"Could not retrieve HTML for {accession_number} from SEC or S3.")
            
            logger.info(f"Storing downloaded HTML in S3 for {accession_number}")
            await self.s3_service.save_filing_html(html_content, ticker, accession_number)

        # Use hierarchical parsing for 10-K filings when filtering is needed
        if filter_for_summarization and form_type == '10-K':
            logger.info("Parsing HTML with hierarchical filtering for key sections.")
            hierarchy = self.sec_parser_service.parse_filing_with_hierarchy(html_content, form_type)
            return self._filter_sections_for_key_items(hierarchy)
        else:
            logger.info("Parsing HTML using standard semantic sec-parser approach.")
            return self.sec_parser_service.parse_filing_to_sections(html_content, form_type)
    
    def _filter_sections_for_key_items(self, hierarchy) -> Dict[str, str]:
        """
        Filter sections to only include those under key Items.
        
        :param hierarchy: SectionHierarchy object from SEC parser
        :return: Filtered sections dictionary
        """
        filtered_sections = {}
        
        # For now, with simplified hierarchy, just include sections that contain key item patterns
        # or are likely children of key items (more sophisticated hierarchy matching can be added later)
        
        from ..config.section_filter import get_hierarchical_section_filter
        filter_service = get_hierarchical_section_filter()
        
        # Include identified key item sections
        for item_key, section_title in hierarchy.key_items.items():
            if section_title in hierarchy.sections:
                filtered_sections[section_title] = hierarchy.sections[section_title]
        
        # Also include sections that appear to be related to key items
        # (This is a heuristic approach until we have better hierarchy tracking)
        for section_title, content in hierarchy.sections.items():
            if section_title not in filtered_sections:
                # Check if this section seems related to business, risks, financials, etc.
                if self._is_likely_key_section(section_title):
                    filtered_sections[section_title] = content
        
        logger.info(f"Filtered {len(hierarchy.sections)} sections down to {len(filtered_sections)} key sections")
        return filtered_sections
    
    def _is_likely_key_section(self, section_title: str) -> bool:
        """
        Heuristic to determine if a section is likely under a key Item.
        This is a simplified approach until we have full hierarchy tracking.
        """
        title_lower = section_title.lower()
        
        # Keywords that suggest the section is under key Items
        key_keywords = [
            'business', 'products', 'services', 'operations', 'strategy',
            'risk', 'factor', 'uncertainty', 'competition',
            'financial', 'revenue', 'income', 'cash', 'liquidity', 'capital',
            'management', 'discussion', 'analysis', 'results', 'condition',
            'market', 'segment', 'geographic', 'customer',
            'properties', 'facility', 'location',
            'legal', 'litigation', 'proceeding',
            'equity', 'shareholder', 'dividend'
        ]
        
        return any(keyword in title_lower for keyword in key_keywords)
    
    def _get_all_descendants(self, parent: str, hierarchy: Dict[str, List[str]]) -> List[str]:
        """
        Recursively get all descendant sections of a parent section.
        
        :param parent: Parent section title
        :param hierarchy: Hierarchy mapping
        :return: List of all descendant section titles
        """
        descendants = []
        
        if parent in hierarchy:
            for child in hierarchy[parent]:
                descendants.append(child)
                # Recursively get descendants of this child
                descendants.extend(self._get_all_descendants(child, hierarchy))
        
        return descendants
    
    async def _download_filing_from_sec(self, ticker: str, accession_number: str, form_type: str) -> Optional[str]:
        """
        Downloads filing HTML directly from SEC Edgar.
        """
        import asyncio
        from ...data_collection.clients.sec_client import get_sec_client

        sec_client = get_sec_client()
        logger.info(f"Attempting to download filing {accession_number} for {ticker}")

        try:
            html_content = await asyncio.to_thread(
                sec_client.download_filing_html_by_ticker, ticker, accession_number, primary_doc=None, form_type=form_type
            )
            if html_content and len(html_content) > 1000:
                logger.info(f"Successfully downloaded HTML for {accession_number} using sec-downloader.")
                return html_content
            else:
                logger.warning(f"Downloaded HTML for {accession_number} is empty or too small (<1000 chars).")
                return None
        except Exception as e:
            logger.error(f"Failed to download filing {accession_number} for {ticker} using sec-downloader: {e}")
            return None


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