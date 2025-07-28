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
    from sec_parser.semantic_elements.top_section_title import TopSectionTitle
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

@dataclass 
class SectionHierarchy:
    """Represents the hierarchical structure of sections in a filing."""
    sections: Dict[str, str]  # section_title -> content
    hierarchy: Dict[str, List[str]]  # parent -> list of children
    key_items: Dict[str, str]  # key_item_id -> section_title


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
    
    def parse_filing_with_hierarchy(self, html_content: str, form_type: str = '10-Q') -> SectionHierarchy:
        """
        Parse SEC filing HTML into sections with full hierarchy information.
        
        Args:
            html_content: Raw HTML content of the filing
            form_type: Type of form ('10-Q' or '10-K')
            
        Returns:
            SectionHierarchy object containing sections, hierarchy, and key items
        """
        if not html_content or not html_content.strip():
            logger.warning("Empty HTML content provided")
            return SectionHierarchy({}, {}, {})
        
        try:
            parser = self.parsers.get(form_type, self.parsers['10-Q'])
            
            logger.info(f"Parsing {form_type} filing with hierarchy tracking")
            elements = parser.parse(html_content)
            tree = self.tree_builder.build(elements)
            
            return self._extract_hierarchical_sections(tree, form_type)
            
        except Exception as e:
            logger.error(f"Error parsing filing with hierarchy: {str(e)}")
            raise
    
    def _extract_hierarchical_sections(self, tree: sp.SemanticTree, form_type: str) -> SectionHierarchy:
        """
        Extract sections with simplified hierarchy tracking to avoid recursion issues.
        
        Args:
            tree: Semantic tree from TreeBuilder
            form_type: Filing type for context
            
        Returns:
            SectionHierarchy with structure information
        """
        sections = {}
        hierarchy = {}
        key_items = {}
        
        # Simplified approach: just get all leaf sections and identify key items
        section_nodes = {}
        
        for node in tree.nodes:
            if isinstance(node.semantic_element, (TitleElement, TopSectionTitle)):
                section_title = self._clean_section_title(node.semantic_element.text)
                
                if not section_title:
                    continue
                    
                section_nodes[section_title] = node
        
        # Extract content from leaf sections only (sections with no title children)
        for section_title, node in section_nodes.items():
            has_title_children = any(
                isinstance(child.semantic_element, (TitleElement, TopSectionTitle))
                for child in node.children
            )
            
            if not has_title_children:
                content = self._get_text_from_descendants(node)
                if content and content.strip():
                    sections[section_title] = content
        
        # For 10-K filings, identify key items using pattern matching
        if form_type == '10-K':
            key_items = self._identify_key_items_simple(sections.keys())
        
        logger.info(f"Extracted {len(sections)} leaf sections")
        logger.info(f"Identified {len(key_items)} key items for filtering")
        
        return SectionHierarchy(sections, hierarchy, key_items)
    
    def _identify_key_items_simple(self, section_titles: List[str]) -> Dict[str, str]:
        """
        Simplified key item identification using pattern matching only.
        
        Args:
            section_titles: List of all section titles
            
        Returns:
            Dict mapping item_key to section_title
        """
        key_items = {}
        
        for section_title in section_titles:
            item_key = self._determine_item_key(section_title)
            if item_key:
                key_items[item_key] = section_title
        
        return key_items
    
    def _clean_section_title(self, title: str) -> str:
        """Clean and normalize section title."""
        if not title:
            return ""
        
        # Remove excessive whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', title.strip())
        
        # Sanitize for use as keys but preserve readability
        # Remove only problematic characters, keep spaces and basic punctuation
        cleaned = re.sub(r'[^\w\s\-\.\(\)&]', '', cleaned)
        
        return cleaned
    
    def _find_parent_title(self, node: sp.TreeNode, tree: sp.SemanticTree, visited: set = None) -> Optional[str]:
        """Find the parent title element for a given node."""
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion
        if id(node) in visited:
            return None
        visited.add(id(node))
        
        # Traverse up the tree to find the nearest parent TitleElement or TopSectionTitle  
        for parent_node in tree.nodes:
            if node in parent_node.children:
                if isinstance(parent_node.semantic_element, (TitleElement, TopSectionTitle)):
                    return self._clean_section_title(parent_node.semantic_element.text)
                else:
                    # Continue looking up the tree with recursion protection
                    return self._find_parent_title(parent_node, tree, visited)
        
        return None
    
    def _identify_key_items(self, section_nodes: Dict[str, sp.TreeNode]) -> Dict[str, str]:
        """
        Identify key Item sections (1, 1A, 7, 8, 7A, 2, 3, 5) in the document.
        
        Args:
            section_nodes: Map of section titles to their tree nodes
            
        Returns:
            Dict mapping item_key to section_title
        """
        from ..config.section_filter import get_hierarchical_section_filter
        
        key_items = {}
        filter_service = get_hierarchical_section_filter()
        
        for section_title in section_nodes.keys():
            if filter_service._is_key_item_header(section_title):
                # Try to determine which specific item this is
                item_key = self._determine_item_key(section_title)
                if item_key:
                    key_items[item_key] = section_title
        
        return key_items
    
    def _determine_item_key(self, section_title: str) -> Optional[str]:
        """Determine the specific item key (e.g., 'item_1') from section title."""
        title_lower = section_title.lower()
        
        # Define patterns for each item
        item_patterns = {
            'item_1': [r'item\s*1\b(?!\w)', r'item\s*1\.\s*business'],
            'item_1a': [r'item\s*1a\b', r'item\s*1a\.\s*risk'],
            'item_7': [r'item\s*7\b(?!\w)', r'item\s*7\.\s*management'],
            'item_8': [r'item\s*8\b(?!\w)', r'item\s*8\.\s*financial'],
            'item_7a': [r'item\s*7a\b', r'item\s*7a\.\s*.*market'],
            'item_2': [r'item\s*2\b(?!\w)', r'item\s*2\.\s*properties'],
            'item_3': [r'item\s*3\b(?!\w)', r'item\s*3\.\s*legal'],
            'item_5': [r'item\s*5\b(?!\w)', r'item\s*5\.\s*market']
        }
        
        for item_key, patterns in item_patterns.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    return item_key
        
        return None

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