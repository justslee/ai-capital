"""
SEC Parser Service using sec-parser library for semantic HTML parsing.

This service leverages the sec-parser library to parse SEC EDGAR HTML filings
into semantic elements that preserve the document's visual and logical structure.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import sec_parser as sp
    from sec_parser.semantic_elements.semantic_elements import (
        TextElement,
        SupplementaryText,
    )
    from sec_parser.semantic_elements.title_element import TitleElement
    SEC_PARSER_AVAILABLE = True
except ImportError as e:
    SEC_PARSER_AVAILABLE = False
    SEC_PARSER_ERROR = str(e)

logger = logging.getLogger(__name__)


@dataclass
class SemanticSection:
    """Represents a semantic section extracted from an SEC filing."""
    name: str
    content: str
    element_type: str
    metadata: Dict[str, Any]


class SecParserService:
    """
    Service for parsing SEC filings using the sec-parser library.
    Provides semantic parsing that preserves document structure.
    """
    
    def __init__(self):
        """Initialize the SEC parser service."""
        if not SEC_PARSER_AVAILABLE:
            raise ImportError(f"sec-parser library not available: {SEC_PARSER_ERROR}")
        
        self.parsers = {
            '10-Q': sp.Edgar10QParser(),
            '10-K': sp.Edgar10KParser() if hasattr(sp, 'Edgar10KParser') else sp.Edgar10QParser()
        }
        self.tree_builder = sp.TreeBuilder()
    
    def parse_filing_to_sections(self, html_content: str, form_type: str = '10-Q') -> Dict[str, str]:
        """
        Parse SEC filing HTML into semantic sections based on TitleElements.
        
        Args:
            html_content: Raw HTML content of the filing
            form_type: Type of form ('10-Q' or '10-K')
            
        Returns:
            A dictionary where keys are the text of the most granular TitleElement
            and values are the aggregated text of their descendant TextElement and 
            SupplementaryText nodes.
        """
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content provided")
            return {}
        
        try:
            parser = self.parsers.get(form_type, self.parsers['10-Q'])
            
            logger.info(f"Parsing {form_type} filing with sec-parser")
            elements = parser.parse(html_content)
            tree = self.tree_builder.build(elements)
            
            sections = self._extract_sections_from_tree(tree)
            
            logger.info(f"Extracted {len(sections)} sections based on TitleElements")
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing filing with sec-parser: {str(e)}")
            raise

    def _extract_sections_from_tree(self, tree: sp.SemanticTree) -> Dict[str, str]:
        """
        Extract sections from the semantic tree based on TitleElements.

        This method traverses the tree and, for each TitleElement, aggregates
        the content of all its descendant TextElement and SupplementaryText nodes.
        It specifically targets the most granular (leaf) TitleElements.
        
        Args:
            tree: Semantic tree from TreeBuilder
            
        Returns:
            A dictionary of sections.
        """
        sections: Dict[str, str] = {}

        for node in tree.nodes:
            if isinstance(node.semantic_element, TitleElement):
                # We are looking for the most granular titles, which are leaf nodes
                # in terms of other TitleElements.
                is_leaf_title = not any(
                    isinstance(child.semantic_element, TitleElement) 
                    for child in node.children
                )
                
                if is_leaf_title:
                    section_title = node.semantic_element.text
                    section_content = self._get_text_from_descendants(node)
                    
                    if section_title and section_content:
                        # Sanitize title to be used as a directory name
                        sanitized_title = re.sub(r'[^\w\s-]', '', section_title).strip()
                        sanitized_title = re.sub(r'[-\s]+', '_', sanitized_title)
                        sections[sanitized_title] = section_content
        
        return sections

    def _get_text_from_descendants(self, node: sp.TreeNode) -> str:
        """
        Recursively get text from all TextElement and SupplementaryText 
        descendants of a given node.
        """
        content_parts = []
        
        for child in node.children:
            if isinstance(child.semantic_element, (TextElement, SupplementaryText)):
                content_parts.append(child.semantic_element.text)
            
            # Recursively get content from children of children
            content_parts.append(self._get_text_from_descendants(child))
            
        return "\n".join(filter(None, content_parts))


# Singleton instance
_sec_parser_service: Optional[SecParserService] = None


def get_sec_parser_service() -> SecParserService:
    """
    Get or create a singleton instance of the SEC parser service.
    
    Returns:
        SecParserService instance
    """
    global _sec_parser_service
    if _sec_parser_service is None:
        _sec_parser_service = SecParserService()
    return _sec_parser_service