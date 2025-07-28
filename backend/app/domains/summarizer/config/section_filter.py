"""
Hierarchical section filtering for 10-K filings summarization.

This module defines which Item sections should be included in summarization
by tracking the document tree hierarchy rather than keyword matching.
"""

import re
from typing import Dict, List, Set, Optional
from enum import Enum


class SectionPriority(Enum):
    """Priority tiers for section inclusion in summarization."""
    TIER_1_MUST_INCLUDE = 1
    TIER_2_ADD_FOR_DEPTH = 2


# Configuration for which 10-K Item sections to include
KEY_ITEMS_CONFIG = {
    # Tier 1 - Must Include (Core business information)
    "item_1": {
        "priority": SectionPriority.TIER_1_MUST_INCLUDE,
        "patterns": [
            r"item\s*1\b(?!\w)",  # Item 1 (not 1A, 10, etc.)
            r"item\s*1\.\s*business",
            r"item\s*1\s*-\s*business"
        ],
        "description": "Business overview and operations"
    },
    
    "item_1a": {
        "priority": SectionPriority.TIER_1_MUST_INCLUDE,  
        "patterns": [
            r"item\s*1a\b",
            r"item\s*1a\.\s*risk\s*factors",
            r"item\s*1a\s*-\s*risk\s*factors"
        ],
        "description": "Risk factors"
    },
    
    "item_7": {
        "priority": SectionPriority.TIER_1_MUST_INCLUDE,
        "patterns": [
            r"item\s*7\b(?!\w)",  # Item 7 (not 7A)
            r"item\s*7\.\s*management",
            r"item\s*7\s*-\s*management",
            r"item\s*7.*md&a",
            r"item\s*7.*discussion.*analysis"
        ],
        "description": "Management's Discussion and Analysis"
    },
    
    "item_8": {
        "priority": SectionPriority.TIER_1_MUST_INCLUDE,
        "patterns": [
            r"item\s*8\b(?!\w)",
            r"item\s*8\.\s*financial\s*statements",
            r"item\s*8\s*-\s*financial\s*statements"
        ],
        "description": "Financial Statements and Supplementary Data"
    },
    
    "item_7a": {
        "priority": SectionPriority.TIER_1_MUST_INCLUDE,
        "patterns": [
            r"item\s*7a\b",
            r"item\s*7a\.\s*.*market\s*risk",
            r"item\s*7a\s*-\s*.*market\s*risk"
        ],
        "description": "Quantitative and Qualitative Disclosures About Market Risk"
    },
    
    # Tier 2 - Add for Depth
    "item_2": {
        "priority": SectionPriority.TIER_2_ADD_FOR_DEPTH,
        "patterns": [
            r"item\s*2\b(?!\w)",
            r"item\s*2\.\s*properties",
            r"item\s*2\s*-\s*properties"
        ],
        "description": "Properties"
    },
    
    "item_3": {
        "priority": SectionPriority.TIER_2_ADD_FOR_DEPTH,
        "patterns": [
            r"item\s*3\b(?!\w)",
            r"item\s*3\.\s*legal\s*proceedings",
            r"item\s*3\s*-\s*legal\s*proceedings"
        ],  
        "description": "Legal Proceedings"
    },
    
    "item_5": {
        "priority": SectionPriority.TIER_2_ADD_FOR_DEPTH,
        "patterns": [
            r"item\s*5\b(?!\w)",
            r"item\s*5\.\s*market",
            r"item\s*5\s*-\s*market"
        ],
        "description": "Market for Registrant's Common Equity"
    }
}


class HierarchicalSectionFilter:
    """
    Hierarchical section filter that identifies key Items and includes
    all their descendant sections in the document tree.
    """
    
    def __init__(self, include_tier_2: bool = True):
        """
        Initialize the hierarchical section filter.
        
        :param include_tier_2: Whether to include Tier 2 items
        """
        self.include_tier_2 = include_tier_2
        self._compiled_patterns = self._compile_patterns()
        self._key_item_sections: Set[str] = set()
        self._section_hierarchy: Dict[str, List[str]] = {}
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for identifying key Item sections."""
        compiled = {}
        
        for item_key, config in KEY_ITEMS_CONFIG.items():
            # Skip Tier 2 if not included
            if not self.include_tier_2 and config["priority"] == SectionPriority.TIER_2_ADD_FOR_DEPTH:
                continue
                
            compiled[item_key] = []
            for pattern in config["patterns"]:
                compiled[item_key].append(
                    re.compile(pattern, re.IGNORECASE)
                )
        
        return compiled
    
    def identify_key_item_sections(self, section_titles: List[str]) -> Set[str]:
        """
        Identify which section titles are key Item headers.
        
        :param section_titles: List of all section titles in the document
        :return: Set of section titles that are key Item headers
        """
        key_items = set()
        
        for section_title in section_titles:
            if self._is_key_item_header(section_title):
                key_items.add(section_title)
        
        self._key_item_sections = key_items
        return key_items
    
    def _is_key_item_header(self, section_title: str) -> bool:
        """Check if a section title is a key Item header."""
        if not section_title:
            return False
            
        section_lower = section_title.lower().strip()
        
        for item_key, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(section_lower):
                    return True
        
        return False
    
    def build_section_hierarchy(self, sections_with_hierarchy: Dict[str, Dict]) -> Dict[str, List[str]]:
        """
        Build hierarchy mapping from sections data that includes parent-child relationships.
        
        :param sections_with_hierarchy: Dict with section titles as keys and metadata as values
                                      Metadata should include 'parent' or 'level' information
        :return: Dict mapping parent sections to their children
        """
        hierarchy = {}
        
        # First pass: identify key item sections
        section_titles = list(sections_with_hierarchy.keys())
        key_items = self.identify_key_item_sections(section_titles)
        
        # Second pass: map children to key item parents
        for section_title, metadata in sections_with_hierarchy.items():
            parent_item = self._find_parent_key_item(section_title, key_items, metadata)
            
            if parent_item:
                if parent_item not in hierarchy:
                    hierarchy[parent_item] = []
                
                # Don't add the parent to its own children list
                if section_title != parent_item:
                    hierarchy[parent_item].append(section_title)
        
        self._section_hierarchy = hierarchy
        return hierarchy
    
    def _find_parent_key_item(self, section_title: str, key_items: Set[str], metadata: Dict) -> Optional[str]:
        """
        Find which key Item section is the parent of the given section.
        
        :param section_title: The section to find parent for
        :param key_items: Set of identified key Item section titles
        :param metadata: Section metadata that may contain hierarchy info
        :return: Parent key Item section title or None
        """
        # If this section is itself a key item, return it
        if section_title in key_items:
            return section_title
        
        # If metadata contains explicit parent information, use it
        if 'parent' in metadata:
            parent = metadata['parent']
            if parent in key_items:
                return parent
            # Recursively check if parent has a key item ancestor
            return self._find_parent_key_item(parent, key_items, {})
        
        # Fallback: try to infer from section ordering/naming
        # This is a simple heuristic that can be improved
        for key_item in sorted(key_items):
            if self._is_likely_child_of(section_title, key_item):
                return key_item
        
        return None
    
    def _is_likely_child_of(self, section_title: str, parent_title: str) -> bool:
        """
        Heuristic to determine if a section is likely a child of a parent section.
        This is a fallback when explicit hierarchy isn't available.
        """
        # Simple heuristic: if section appears after parent in document order
        # and doesn't match any other key item patterns, it's likely a child
        return not self._is_key_item_header(section_title)
    
    def filter_sections_hierarchically(self, sections: Dict[str, str], 
                                     sections_metadata: Optional[Dict[str, Dict]] = None) -> Dict[str, str]:
        """
        Filter sections to only include key Items and their descendants.
        
        :param sections: Dict of section_title -> content
        :param sections_metadata: Optional metadata with hierarchy information
        :return: Filtered sections dict
        """
        if sections_metadata:
            # Use hierarchy information if available
            self.build_section_hierarchy(sections_metadata)
            
            filtered_sections = {}
            
            # Include all sections that are under key Items
            for parent_item, children in self._section_hierarchy.items():
                # Include the parent Item itself
                if parent_item in sections:
                    filtered_sections[parent_item] = sections[parent_item]
                
                # Include all children
                for child in children:
                    if child in sections:
                        filtered_sections[child] = sections[child]
            
            return filtered_sections
        
        else:
            # Fallback: identify key items and include nearby sections
            section_titles = list(sections.keys())
            key_items = self.identify_key_item_sections(section_titles)
            
            filtered_sections = {}
            current_key_item = None
            
            for section_title in section_titles:
                if section_title in key_items:
                    # This is a key Item - include it and update current context
                    current_key_item = section_title
                    filtered_sections[section_title] = sections[section_title]
                
                elif current_key_item and not self._is_key_item_header(section_title):
                    # This appears to be under a key Item - include it
                    filtered_sections[section_title] = sections[section_title]
                
                else:
                    # This section is either not under a key Item or is another key Item
                    # Reset current context if it's another key Item
                    if self._is_key_item_header(section_title):
                        current_key_item = None
            
            return filtered_sections
    
    def get_included_items(self) -> Set[str]:
        """Get set of key Item identifiers that are included."""
        return set(self._compiled_patterns.keys())
    
    def get_filter_summary(self) -> Dict[str, str]:
        """Get summary of what's included in filtering."""
        summary = {}
        
        for item_key, config in KEY_ITEMS_CONFIG.items():
            if item_key in self._compiled_patterns:
                summary[item_key] = config["description"]
        
        return summary


# Default instances
default_hierarchical_filter = HierarchicalSectionFilter(include_tier_2=True)
strict_hierarchical_filter = HierarchicalSectionFilter(include_tier_2=False)


def get_hierarchical_section_filter(strict_mode: bool = False) -> HierarchicalSectionFilter:
    """
    Get a hierarchical section filter instance.
    
    :param strict_mode: If True, only include Tier 1 items
    :return: HierarchicalSectionFilter instance
    """
    return strict_hierarchical_filter if strict_mode else default_hierarchical_filter