import psycopg2
import sys
import os
import re
from dotenv import load_dotenv
from urllib.parse import urlparse
from bs4 import BeautifulSoup, NavigableString, Tag
from collections import OrderedDict
from datetime import datetime
import asyncio

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from app.domains.data_collection.storage.s3_storage_service import get_s3_storage_service

# Environment setup
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

DATABASE_URL = os.getenv("DATABASE_URL")
TICKERS_TO_PROCESS = ["AAPL", "TSLA"]

# Chunking parameters
MIN_CHARS_PER_CHUNK = 500
TARGET_CHARS_PER_CHUNK = 1500
MAX_CHARS_PER_CHUNK = 2500

# Content markers
TABLE_START_MARKER = "%%%START_TABLE%%%"
TABLE_END_MARKER = "%%%END_TABLE%%%"
FOOTNOTE_START_MARKER = "%%%START_FOOTNOTE%%%"
FOOTNOTE_END_MARKER = "%%%END_FOOTNOTE%%%"

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables.")
    sys.exit(1)

def normalize_text(text):
    # Replace HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    
    # Replace Unicode characters
    text = text.replace('\xa0', ' ')
    text = text.replace('\u2013', '-')
    text = text.replace('\u2014', '--')
    
    lines = text.split('\n')
    normalized_lines = []
    for line in lines:
        line = re.sub(r'^\d+\s+', '', line)
        line = re.sub(r'-{3,}.*?Page \d+.*?-{3,}', '', line)
        line = re.sub(r'-{3,}', '', line)
        
        # Remove headers/footers
        if line.isupper() and len(line) > 10:
            if not re.search(r'(ITEM|PART|SECTION|NOTE|TABLE|INDEX)', line):
                line = ''
        
        line = re.sub(r'[ \t]+', ' ', line).strip()
        if line:
            normalized_lines.append(line)
            
    text = '\n'.join(normalized_lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    return text

def detect_subheading(line_text, lines_around, line_idx):
    """Detect if a line is a subheading using heuristics."""
    line_text = line_text.strip()
    if not line_text or len(line_text) > 150:
        return None

    if line_text.endswith(('.', '?', '!')) and not line_text.endswith('...'):
        return None
    
    if not (line_text.isupper() or line_text.istitle()):
        if ':' not in line_text and not (any(c.isdigit() for c in line_text) and not line_text.islower()):
            return None

    if len(line_text.split()) > 10 and '.' in line_text:
         return None

    prev_line = lines_around[line_idx-1].strip() if line_idx > 0 else ""
    next_line = lines_around[line_idx+1].strip() if line_idx < len(lines_around)-1 else ""

    if prev_line == "" and next_line != "":
        return line_text
    
    if line_text.istitle() and next_line and next_line[0].isupper():
        return line_text

    return None

def _split_text_by_sentences(text, min_chars, target_chars, max_chars):
    if not text.strip(): 
        return []
    
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    chunks = []
    current_chunk_sentences = []
    current_len = 0
    for s in sentences:
        s_len = len(s)
        if current_len + s_len + (len(current_chunk_sentences)) > max_chars and current_len > 0:
            chunks.append(" ".join(current_chunk_sentences))
            current_chunk_sentences = [s]
            current_len = s_len
        elif current_len + s_len + (len(current_chunk_sentences)) > max_chars and current_len == 0:
            # Split very long sentence
            start = 0
            while start < s_len:
                end = min(start + target_chars, s_len)
                if end < s_len and s[end] != ' ':
                    space_idx = s.rfind(' ', start, end)
                    if space_idx != -1 and space_idx > start:
                        end = space_idx
                chunks.append(s[start:end].strip())
                start = end + 1
            current_chunk_sentences = []
            current_len = 0
        else:
            current_chunk_sentences.append(s)
            current_len += s_len
            if current_len >= min_chars:
                 if current_len >= target_chars or len(current_chunk_sentences) > 3:
                    chunks.append(" ".join(current_chunk_sentences))
                    current_chunk_sentences = []
                    current_len = 0

    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))
    return [c for c in chunks if c.strip()]


def _chunk_segment_by_paragraphs_and_sentences(segment_text, current_subheading, min_c, target_c, max_c):
    """Chunk narrative text using paragraphs and sentences."""
    chunks_with_meta = []
    paragraphs = segment_text.split('\n\n')
    
    current_paragraph_group = []
    current_len = 0
    for para_idx, p_text in enumerate(paragraphs):
        p_text = p_text.strip()
        if not p_text: 
            continue
        p_len = len(p_text)

        if current_len + p_len + len(current_paragraph_group) > max_c and current_len > 0:
            grouped_text = "\n\n".join(current_paragraph_group)
            if len(grouped_text) > max_c:
                sentence_chunks = _split_text_by_sentences(grouped_text, min_c, target_c, max_c)
                for sc_idx, sc in enumerate(sentence_chunks):
                    chunks_with_meta.append({'text': sc, 'is_table': False, 'is_footnote': False, 'subheading': current_subheading})
            else:
                 chunks_with_meta.append({'text': grouped_text, 'is_table': False, 'is_footnote': False, 'subheading': current_subheading})
            current_paragraph_group = [p_text]
            current_len = p_len
        elif current_len + p_len + len(current_paragraph_group) > max_c and current_len == 0:
            sentence_chunks = _split_text_by_sentences(p_text, min_c, target_c, max_c)
            for sc_idx, sc in enumerate(sentence_chunks):
                chunks_with_meta.append({'text': sc, 'is_table': False, 'is_footnote': False, 'subheading': current_subheading})
            current_paragraph_group = []
            current_len = 0
        else:
            current_paragraph_group.append(p_text)
            current_len += p_len
            if current_len >= min_c:
                if current_len >= target_c or len(current_paragraph_group) > 2:
                    grouped_text = "\n\n".join(current_paragraph_group)
                    chunks_with_meta.append({'text': grouped_text, 'is_table': False, 'is_footnote': False, 'subheading': current_subheading})
                    current_paragraph_group = []
                    current_len = 0
                    
    if current_paragraph_group:
        grouped_text = "\n\n".join(current_paragraph_group)
        if len(grouped_text) > max_c:
             sentence_chunks = _split_text_by_sentences(grouped_text, min_c, target_c, max_c)
             for sc_idx, sc in enumerate(sentence_chunks):
                chunks_with_meta.append({'text': sc, 'is_table': False, 'is_footnote': False, 'subheading': current_subheading})
        elif grouped_text.strip():
             chunks_with_meta.append({'text': grouped_text, 'is_table': False, 'is_footnote': False, 'subheading': current_subheading})
             
    return chunks_with_meta


def chunk_section_content(section_text):
    """Chunk section content by structure: tables, footnotes, subheadings, paragraphs."""
    final_chunks = []
    
    parts = []
    remaining_text = section_text
    while True:
        start_table_idx = remaining_text.find(TABLE_START_MARKER)
        start_footnote_idx = remaining_text.find(FOOTNOTE_START_MARKER)

        next_marker_pos = float('inf')
        marker_type = None

        if start_table_idx != -1:
            next_marker_pos = start_table_idx
            marker_type = 'table'
        
        if start_footnote_idx != -1 and start_footnote_idx < next_marker_pos:
            next_marker_pos = start_footnote_idx
            marker_type = 'footnote'

        if marker_type:
            if next_marker_pos > 0:
                parts.append({'type': 'narrative', 'content': remaining_text[:next_marker_pos]})
            
            if marker_type == 'table':
                end_marker_idx = remaining_text.find(TABLE_END_MARKER, next_marker_pos)
                start_len = len(TABLE_START_MARKER)
                end_len = len(TABLE_END_MARKER)
            else:
                end_marker_idx = remaining_text.find(FOOTNOTE_END_MARKER, next_marker_pos)
                start_len = len(FOOTNOTE_START_MARKER)
                end_len = len(FOOTNOTE_END_MARKER)

            if end_marker_idx != -1:
                marker_content = remaining_text[next_marker_pos + start_len : end_marker_idx].strip()
                parts.append({'type': marker_type, 'content': marker_content})
                remaining_text = remaining_text[end_marker_idx + end_len:]
            else:
                parts.append({'type': 'narrative', 'content': remaining_text[next_marker_pos:]})
                remaining_text = ""
                break 
        else:
            if remaining_text.strip():
                parts.append({'type': 'narrative', 'content': remaining_text})
            break
            
    for part in parts:
        content = part['content'].strip()
        if not content: continue

        if part['type'] == 'table':
            final_chunks.append({'text': content, 'is_table': True, 'is_footnote': False, 'subheading': None})
        elif part['type'] == 'footnote': 
            final_chunks.append({'text': content, 'is_table': False, 'is_footnote': True, 'subheading': None})
        elif part['type'] == 'narrative':
            lines = content.split('\n')
            current_narrative_segment = []
            current_subheading_title = None
            
            for line_idx, line in enumerate(lines):
                detected_subheading = detect_subheading(line, lines, line_idx)
                if detected_subheading:
                    if current_narrative_segment:
                        segment_text = "\n".join(current_narrative_segment)
                        final_chunks.extend(_chunk_segment_by_paragraphs_and_sentences(
                            segment_text, current_subheading_title, MIN_CHARS_PER_CHUNK, TARGET_CHARS_PER_CHUNK, MAX_CHARS_PER_CHUNK
                        ))
                        current_narrative_segment = []
                    current_subheading_title = detected_subheading
                else:
                    current_narrative_segment.append(line)
            
            if current_narrative_segment:
                segment_text = "\n".join(current_narrative_segment)
                final_chunks.extend(_chunk_segment_by_paragraphs_and_sentences(
                    segment_text, current_subheading_title, MIN_CHARS_PER_CHUNK, TARGET_CHARS_PER_CHUNK, MAX_CHARS_PER_CHUNK
                ))
                
    return final_chunks

def detect_section(line):
    """
    Detect section from a line of text using both canonical and additional patterns.
    Returns (section_name, canonical_name) if found, (None, None) otherwise.
    """
    # Clean the line for better matching
    line = line.strip()
    
    # Skip empty lines or lines that are too short
    if not line or len(line) < 3:
        return None, None
    
    # Skip lines that are clearly XBRL metadata (but be less aggressive)
    if any(x in line.lower() for x in ['fasb.org', 'xbrl.org', 'xmlns:']):
        return None, None
    
    # Check for exact Item patterns first (for actual content sections)
    item_patterns = [
        (r'^Item\s+1\.\s+Business\s*$', 'Item 1. Business', 'Business'),
        (r'^Item\s+1A\.\s+Risk\s+Factors\s*$', 'Item 1A. Risk Factors', 'Risk Factors'),
        (r'^Item\s+1B\.\s+Unresolved\s+Staff\s+Comments\s*$', 'Item 1B. Unresolved Staff Comments', 'Unresolved Staff Comments'),
        (r'^Item\s+1C\.\s+Cybersecurity\s*$', 'Item 1C. Cybersecurity', 'Cybersecurity'),
        (r'^Item\s+2\.\s+Properties\s*$', 'Item 2. Properties', 'Properties'),
        (r'^Item\s+3\.\s+Legal\s+Proceedings\s*$', 'Item 3. Legal Proceedings', 'Legal Proceedings'),
        (r'^Item\s+4\.\s+Mine\s+Safety\s+Disclosures\s*$', 'Item 4. Mine Safety Disclosures', 'Mine Safety Disclosures'),
        (r'^Item\s+5\..*Market.*Common.*Equity.*$', 'Item 5. Market for Common Equity', 'Market for Common Equity'),
        (r'^Item\s+6\.\s+\[?Reserved\]?\s*$', 'Item 6. [Reserved]', 'Reserved'),
        (r'^Item\s+7\..*Management.*Discussion.*Analysis.*$', 'Item 7. MD&A', 'MD&A'),
        (r'^Item\s+7A\..*Quantitative.*Qualitative.*Market.*Risk.*$', 'Item 7A. Market Risk', 'Market Risk'),
        (r'^Item\s+8\..*Financial\s+Statements.*$', 'Item 8. Financial Statements', 'Financial Statements'),
        (r'^Item\s+9\..*Changes.*Disagreements.*Accountants.*$', 'Item 9. Changes in Accountants', 'Changes in Accountants'),
        (r'^Item\s+9A\..*Controls.*Procedures.*$', 'Item 9A. Controls and Procedures', 'Controls and Procedures'),
        (r'^Item\s+9B\.\s+Other\s+Information\s*$', 'Item 9B. Other Information', 'Other Information'),
        (r'^Item\s+9C\..*Disclosure.*Foreign.*Jurisdictions.*$', 'Item 9C. Foreign Jurisdictions', 'Foreign Jurisdictions'),
        (r'^Item\s+10\..*Directors.*Executive.*Officers.*$', 'Item 10. Directors and Officers', 'Directors and Officers'),
        (r'^Item\s+11\..*Executive\s+Compensation.*$', 'Item 11. Executive Compensation', 'Executive Compensation'),
        (r'^Item\s+12\..*Security\s+Ownership.*$', 'Item 12. Security Ownership', 'Security Ownership'),
        (r'^Item\s+13\..*Certain\s+Relationships.*$', 'Item 13. Related Transactions', 'Related Transactions'),
        (r'^Item\s+14\..*Principal\s+Accountant.*$', 'Item 14. Principal Accountant', 'Principal Accountant'),
        (r'^Item\s+15\..*Exhibit.*Financial.*Statement.*$', 'Item 15. Exhibits', 'Exhibits'),
        (r'^Item\s+16\..*Form\s+10-K\s+Summary.*$', 'Item 16. Form 10-K Summary', 'Form 10-K Summary'),
    ]
    
    for pattern, section_name, canonical_name in item_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return section_name, canonical_name
    
    # Check for PART headers
    part_patterns = [
        (r'^PART\s+I\s*$', 'Part I', 'Part I'),
        (r'^PART\s+II\s*$', 'Part II', 'Part II'),
        (r'^PART\s+III\s*$', 'Part III', 'Part III'),
        (r'^PART\s+IV\s*$', 'Part IV', 'Part IV'),
    ]
    
    for pattern, section_name, canonical_name in part_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return section_name, canonical_name
    
    return None, None

def segment_sec_sections(text):
    """
    Segment the text into SEC sections based on Item headers.
    This version properly handles the table of contents vs actual content.
    Returns an OrderedDict where keys are canonical section names and 
    values are tuples: (original_header_text, section_content_text)
    """
    lines = text.split('\n')
    sections = OrderedDict()
    current_section_canonical = None
    current_original_header = None
    current_content = []
    
    content_start_line = 0
    for i in range(len(lines) - 1):
        line = lines[i]
        next_line = lines[i + 1]
        if (line.strip() == "PART I" and next_line.strip() == "Item 1. Business"):
            content_start_line = i
            break
    
    for i in range(content_start_line, len(lines)):
        line_text = lines[i].strip()
        
        original_header, canonical_name = detect_section(line_text)
        
        if original_header: # A new section is detected
            if current_section_canonical and current_content:
                content_text = '\n'.join(current_content).strip()
                if content_text:
                    sections[current_section_canonical] = (current_original_header, content_text)
            
            current_section_canonical = canonical_name or original_header # Use canonical if available
            current_original_header = original_header # Store the originally detected header
            current_content = [] 
            # The header line itself is not added to current_content here,
            # as it's already captured in current_original_header.
            # If the header line should ALSO be part of the content, add: current_content.append(line_text)
        else:
            if line_text:
                current_content.append(line_text)
    
    if current_section_canonical and current_content:
        content_text = '\n'.join(current_content).strip()
        if content_text:
            sections[current_section_canonical] = (current_original_header, content_text)
    
    if not sections and content_start_line == 0: # Only if no sections AND no specific content start found
        all_content = '\n'.join(lines).strip()
        if all_content:
            sections['Preamble'] = ("Preamble", all_content)
    elif not sections: # If no sections but specific content start WAS found
        all_content = '\n'.join(lines[content_start_line:]).strip()
        if all_content:
             sections['Preamble (from content start)'] = ("Preamble (from content start)", all_content)

    return sections

def preprocess_html(html_content):
    """
    Preprocess HTML to remove XBRL metadata and other non-content elements
    while preserving document structure.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Remove XBRL-specific elements but be less aggressive
    for tag in soup.find_all(True):
        # Remove elements with XBRL namespaces
        if tag.name and ':' in tag.name:
            tag.decompose()
            continue
            
        # Remove elements with XBRL-related attributes
        if tag.attrs:
            xbrl_attrs = ['contextref', 'unitref', 'decimals', 'scale', 'format']
            if any(attr in tag.attrs for attr in xbrl_attrs):
                tag.decompose()
                continue
    
    # Add line breaks before certain block elements to preserve structure
    block_elements = ['div', 'p', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                     'table', 'tr', 'td', 'th', 'ul', 'ol', 'li', 'section', 'article']
    
    for tag in soup.find_all(block_elements):
        if tag.string:
            tag.string.replace_with('\n' + tag.string + '\n')
        else:
            # Insert line breaks before and after the tag
            if tag.previous_sibling and not str(tag.previous_sibling).endswith('\n'):
                tag.insert_before('\n')
            if tag.next_sibling and not str(tag.next_sibling).startswith('\n'):
                tag.insert_after('\n')
    
    # Get text and clean it up
    text = soup.get_text()
    
    # Normalize whitespace while preserving line structure
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Clean each line but preserve it as a separate line
        cleaned_line = ' '.join(line.split())  # Normalize internal whitespace
        if cleaned_line:  # Only keep non-empty lines
            cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

async def save_chunks_to_s3(s3_service, chunks, ticker, accession_number, section_key):
    """Saves a list of chunks to S3."""
    tasks = []
    for i, chunk in enumerate(chunks):
        task = s3_service.save_chunk_text(
            chunk_text=chunk['text'],
            ticker=ticker,
            accession_number=accession_number,
            section_key=section_key,
            chunk_index=i
        )
        tasks.append(task)
    await asyncio.gather(*tasks)

def main():
    print("Starting SEC filing processing...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Database connection successful.")
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)

    s3_storage_service = get_s3_storage_service()

    for ticker_to_check in TICKERS_TO_PROCESS:
        print(f"\n--- Processing ticker: {ticker_to_check} ---")
        query = """
        SELECT accession_number, raw_html, ticker, filing_type, filing_date, company_name 
        FROM sec_filings 
        WHERE ticker = %s ORDER BY filing_date DESC LIMIT 1;
        """
        cur.execute(query, (ticker_to_check,))
        record = cur.fetchone()

        if record:
            accession_number, raw_html, db_ticker, db_filing_type, db_filing_date, db_company_name = record
            
            filing_year = db_filing_date.year if db_filing_date else None

            filing_metadata = {
                "accession_number": accession_number,
                "company_name": db_company_name,
                "ticker": db_ticker,
                "form_type": db_filing_type,
                "filing_year": filing_year
            }
            print(f"Processing latest filing - Accession: {accession_number}, Year: {filing_year}, Company: {db_company_name}, DB Filing Type: {db_filing_type}")
            
            if raw_html:
                preprocessed_text = preprocess_html(raw_html)
                normalized_text = normalize_text(preprocessed_text)
                sections_data = segment_sec_sections(normalized_text)
                
                if not sections_data:
                    print(f"No sections extracted for {accession_number}. Skipping S3 storage.")
                    continue

                print(f"\nExtracted {len(sections_data)} sections. Saving chunks to S3...")
                
                total_chunks_saved_for_filing = 0
                for section_key_val, (original_header, section_text_val) in sections_data.items():
                    section_key = section_key_val
                    section_content = section_text_val
                    
                    if not section_content.strip():
                        print(f"Section {section_key} is empty. Skipping.")
                        continue

                    chunks = chunk_section_content(section_content)
                    
                    if chunks:
                        print(f"  - Section '{section_key}': Found {len(chunks)} chunks. Saving to S3...")
                        try:
                            asyncio.run(save_chunks_to_s3(
                                s3_storage_service, chunks, db_ticker, accession_number, section_key
                            ))
                            total_chunks_saved_for_filing += len(chunks)
                        except Exception as e:
                            print(f"    ERROR: Failed to save chunks for section {section_key} to S3: {e}")
                    else:
                        print(f"  - Section '{section_key}': No chunks were generated.")

                print(f"\nFinished processing for {accession_number}. Total chunks saved to S3: {total_chunks_saved_for_filing}")

            else:
                print(f"No raw_html content for {accession_number}. Skipping.")
        else:
            print(f"No filings found for ticker: {ticker_to_check}")

    cur.close()
    conn.close()
    print("\nProcessing complete. Database connection closed.")

if __name__ == "__main__":
    main() 