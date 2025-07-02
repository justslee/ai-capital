"""
Summarization Repositories

Repository pattern implementations for data access in the summarization domain.
Separates database operations from business logic.
"""

from .section_summary_repository import SectionSummaryRepository, SectionData

__all__ = [
    "SectionSummaryRepository",
    "SectionData",
] 