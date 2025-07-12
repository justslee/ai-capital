"""
Section Summary Repository

Repository for managing section summary data access operations.
Separates database operations from business logic in the summarization service.
"""

# Standard library imports
from typing import List, Optional, Dict, Any, NamedTuple
from dataclasses import dataclass

# Third-party imports
import psycopg2
from psycopg2.extras import DictCursor

# App imports
from app.db.database_utils import db_cursor


@dataclass
class SectionData:
    """Data class for section information."""
    id: int
    filing_accession_number: str
    section_key: str


class SectionSummaryRepository:
    """Repository for section summary database operations."""
    
    def __init__(self):
        """Initialize the repository."""
        pass
    
    def create_summaries_table(self) -> None:
        """Create the section summaries table if it doesn't exist."""
        table_creation_query = """
        CREATE TABLE IF NOT EXISTS sec_section_summaries (
            id SERIAL PRIMARY KEY,
            section_db_id INTEGER NOT NULL UNIQUE REFERENCES sec_filing_sections(id) ON DELETE CASCADE,
            filing_accession_number TEXT NOT NULL,
            section_key TEXT NOT NULL,
            summarization_model_name TEXT NOT NULL,
            summary_text TEXT NOT NULL,
            raw_chunk_summaries_concatenated TEXT,
            total_chunks_in_section INTEGER,
            processing_status TEXT,
            error_message TEXT,
            generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_section_model UNIQUE (section_db_id, summarization_model_name)
        );
        CREATE INDEX IF NOT EXISTS idx_sss_section_db_id ON sec_section_summaries(section_db_id);
        CREATE INDEX IF NOT EXISTS idx_sss_accession_number ON sec_section_summaries(filing_accession_number);
        CREATE INDEX IF NOT EXISTS idx_sss_section_key ON sec_section_summaries(section_key);
        CREATE INDEX IF NOT EXISTS idx_sss_model_name ON sec_section_summaries(summarization_model_name);
        """
        
        with db_cursor() as cursor:
            cursor.execute(table_creation_query)
    
    def get_unprocessed_sections(
        self, 
        model_name: str, 
        target_section_keys: List[str]
    ) -> List[SectionData]:
        """
        Get sections that need summarization or re-processing.
        
        Args:
            model_name: Name of the summarization model
            target_section_keys: List of section keys to process
            
        Returns:
            List of section data that needs processing
        """
        target_keys_tuple = tuple(target_section_keys)
        
        query = """
        SELECT fs.id, fs.filing_accession_number, fs.section_key
        FROM sec_filing_sections fs
        LEFT JOIN sec_section_summaries sss ON fs.id = sss.section_db_id AND sss.summarization_model_name = %s
        WHERE fs.section_key IN %s 
          AND (sss.id IS NULL OR sss.processing_status IS NULL OR sss.processing_status NOT IN ('reduce_complete'))
        ORDER BY fs.filing_accession_number, fs.id;
        """
        
        with db_cursor() as cursor:
            cursor.execute(query, (model_name, target_keys_tuple))
            rows = cursor.fetchall()
            
            return [
                SectionData(
                    id=row[0],
                    filing_accession_number=row[1],
                    section_key=row[2]
                )
                for row in rows
            ]
    
    def get_chunks_for_section(self, section_db_id: int) -> List[str]:
        """
        Get all text chunks for a section, ordered by sequence.
        
        Args:
            section_db_id: Database ID of the section
            
        Returns:
            List of chunk texts
        """
        query = """
        SELECT chunk_text 
        FROM sec_filing_section_chunks
        WHERE section_db_id = %s
        ORDER BY chunk_order_in_section ASC;
        """
        
        with db_cursor() as cursor:
            cursor.execute(query, (section_db_id,))
            return [row[0] for row in cursor.fetchall()]
    
    def save_summary(
        self,
        section_db_id: int,
        filing_accession_number: str,
        section_key: str,
        summarization_model_name: str,
        summary_text: Optional[str] = None,
        raw_chunk_summaries_concatenated: Optional[str] = None,
        total_chunks_in_section: Optional[int] = None,
        processing_status: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Insert or update a summary record.
        
        Args:
            section_db_id: Database ID of the section
            filing_accession_number: SEC filing accession number
            section_key: Section key (e.g., 'Business', 'Risk Factors')
            summarization_model_name: Name of the model used
            summary_text: Generated summary text
            raw_chunk_summaries_concatenated: Raw chunk summaries
            total_chunks_in_section: Total number of chunks processed
            processing_status: Current processing status
            error_message: Error message if processing failed
        """
        with db_cursor() as cursor:
            # Check if record exists
            cursor.execute(
                "SELECT id FROM sec_section_summaries WHERE section_db_id = %s AND summarization_model_name = %s",
                (section_db_id, summarization_model_name)
            )
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update existing record
                update_fields = []
                update_values = []
                
                if summary_text is not None:
                    update_fields.append("summary_text = %s")
                    update_values.append(summary_text)
                if raw_chunk_summaries_concatenated is not None:
                    update_fields.append("raw_chunk_summaries_concatenated = %s")
                    update_values.append(raw_chunk_summaries_concatenated)
                if total_chunks_in_section is not None:
                    update_fields.append("total_chunks_in_section = %s")
                    update_values.append(total_chunks_in_section)
                if processing_status is not None:
                    update_fields.append("processing_status = %s")
                    update_values.append(processing_status)
                if error_message is not None:
                    update_fields.append("error_message = %s")
                    update_values.append(error_message)
                else:
                    update_fields.append("error_message = NULL")
                
                update_fields.append("generated_at = CURRENT_TIMESTAMP")
                
                if update_fields:
                    query = f"UPDATE sec_section_summaries SET {', '.join(update_fields)} WHERE id = %s"
                    update_values.append(existing_record[0])
                    cursor.execute(query, tuple(update_values))
            else:
                # Insert new record
                query = """
                INSERT INTO sec_section_summaries (
                    section_db_id, filing_accession_number, section_key, summarization_model_name, 
                    summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section, 
                    processing_status, error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (section_db_id, summarization_model_name) DO NOTHING;
                """
                final_summary_text = summary_text if summary_text is not None else ""
                
                cursor.execute(query, (
                    section_db_id, filing_accession_number, section_key, summarization_model_name,
                    final_summary_text, raw_chunk_summaries_concatenated, total_chunks_in_section,
                    processing_status, error_message
                ))
    
    def get_summary_by_section(
        self, 
        section_db_id: int, 
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get an existing summary for a section.
        
        Args:
            section_db_id: Database ID of the section
            model_name: Name of the summarization model
            
        Returns:
            Summary data dictionary or None if not found
        """
        query = """
        SELECT summary_text, processing_status, generated_at, error_message
        FROM sec_section_summaries
        WHERE section_db_id = %s AND summarization_model_name = %s
        """
        
        with db_cursor() as cursor:
            cursor.execute(query, (section_db_id, model_name))
            row = cursor.fetchone()
            
            if row:
                return {
                    'summary_text': row[0],
                    'processing_status': row[1],
                    'generated_at': row[2],
                    'error_message': row[3]
                }
            return None
    
    def get_summaries_by_accession(
        self, 
        accession_number: str, 
        model_name: str,
        section_keys: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all summaries for a filing accession number.
        
        Args:
            accession_number: SEC filing accession number
            model_name: Name of the summarization model
            section_keys: Optional filter for specific section keys
            
        Returns:
            List of summary data dictionaries
        """
        base_query = """
        SELECT section_key, summary_text, processing_status, generated_at, error_message
        FROM sec_section_summaries
        WHERE filing_accession_number = %s AND summarization_model_name = %s
        """
        
        params = [accession_number, model_name]
        
        if section_keys:
            base_query += " AND section_key IN %s"
            params.append(tuple(section_keys))
        
        base_query += " ORDER BY section_key"
        
        with db_cursor() as cursor:
            cursor.execute(base_query, tuple(params))
            rows = cursor.fetchall()
            
            return [
                {
                    'section_key': row[0],
                    'summary_text': row[1],
                    'processing_status': row[2],
                    'generated_at': row[3],
                    'error_message': row[4]
                }
                for row in rows
            ] 