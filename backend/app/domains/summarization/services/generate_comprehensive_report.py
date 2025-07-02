"""Comprehensive SEC filing report generator for institutional investors."""

import psycopg2
import sys
import os
import json
from dotenv import load_dotenv
from urllib.parse import urlparse
import openai
import time
from typing import Dict, List, Optional

# Configuration
COMPREHENSIVE_REPORT_MODEL = "gpt-4-turbo"
MAX_TOKENS_FOR_COMPREHENSIVE_REPORT = 4000
SOURCE_SUMMARIES_MODEL_NAME = "gpt-4-turbo"
SOURCE_SECTION_KEYS = sorted([
    "Business", 
    "Risk Factors", 
    "MD&A",
    "Financial Statements"
])

# Environment setup
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found")
    sys.exit(1)
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found")
    sys.exit(1)

# Database connection
parsed_url = urlparse(DATABASE_URL.replace("+asyncpg", ""))
conn_params = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port,
    'sslmode': 'require'
}

def create_comprehensive_reports_table(cursor):
    """Create table for comprehensive reports."""
    table_creation_query = """
    CREATE TABLE IF NOT EXISTS sec_comprehensive_reports (
        id SERIAL PRIMARY KEY,
        filing_accession_number TEXT NOT NULL REFERENCES sec_filings(accession_number) ON DELETE CASCADE,
        report_model_name TEXT NOT NULL,
        source_section_keys TEXT[] NOT NULL,
        comprehensive_report_text TEXT NOT NULL,
        report_metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_filing_comprehensive_report UNIQUE (filing_accession_number, report_model_name, source_section_keys)
    );
    CREATE INDEX IF NOT EXISTS idx_comprehensive_accession ON sec_comprehensive_reports(filing_accession_number);
    CREATE INDEX IF NOT EXISTS idx_comprehensive_model ON sec_comprehensive_reports(report_model_name);
    """
    cursor.execute(table_creation_query)

def call_openai_api(openai_client_instance, prompt_messages, model_name, max_tokens_output):
    """Call OpenAI API with error handling."""
    try:
        response = openai_client_instance.chat.completions.create(
            model=model_name,
            messages=prompt_messages,
            max_tokens=max_tokens_output,
            temperature=0.2,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        if response.choices and response.choices[0].message:
            return response.choices[0].message.content.strip()
        else:
            print("Warning: Invalid OpenAI API response")
            return None
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        return None
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return None

def get_filing_metadata(cursor, accession_number: str) -> Dict:
    """Get filing metadata."""
    cursor.execute(
        """SELECT ticker, filing_type, filing_date
           FROM sec_filings WHERE accession_number = %s""",
        (accession_number,)
    )
    result = cursor.fetchone()
    if result:
        return {
            "ticker": result[0],
            "form_type": result[1],
            "filing_date": result[2]
        }
    return {}

def create_comprehensive_report_prompt(filing_metadata: Dict, section_summaries: List[Dict]) -> str:
    """Create comprehensive analysis prompt."""
    
    ticker = filing_metadata.get("ticker", "COMPANY")
    form_type = filing_metadata.get("form_type", "10-K")
    filing_date = filing_metadata.get("filing_date", "2024")
    
    # Format section summaries
    sections_text = ""
    for section in section_summaries:
        sections_text += f"\n\n=== {section['key']} Section ===\n{section['summary']}\n"
    
    system_prompt = """You are an expert financial analyst specializing in comprehensive SEC filing analysis for institutional investors and hedge funds. You have deep expertise in financial statement analysis, industry trends, risk assessment, and investment decision-making."""
    
    user_prompt = f"""
Create a comprehensive financial analysis report for {ticker}'s {form_type} filing. This report should be suitable for institutional investors and hedge funds making investment decisions.

Structure your analysis as follows:

**{ticker} {form_type} Summary – Key Financial & Operational Highlights**

## Revenue Breakdown and Margins
- Detailed revenue analysis by segment, geography, and product lines
- Year-over-year growth rates and trends
- Margin analysis (gross, operating, net) with explanations for changes
- Average selling price trends and volume analysis
- Key revenue drivers and headwinds

## Geographic Mix and Market Performance
- Revenue breakdown by major geographic regions
- Market share trends in key regions
- Regional growth rates and market dynamics
- Currency impact and local market conditions

## Production, Deliveries and Unit Economics
- Production and delivery volumes with year-over-year comparisons
- Unit economics and cost per unit trends
- Capacity utilization and expansion plans
- Supply chain efficiency and optimization efforts

## Operating Costs and Leverage
- Operating expense breakdown (R&D, SG&A, etc.)
- Cost structure analysis and efficiency initiatives
- Operating leverage and scalability
- One-time charges or restructuring costs

## Balance Sheet and Cash Flow
- Cash position and liquidity analysis
- Working capital management
- Debt levels and capital structure
- Free cash flow generation and uses
- Return on invested capital trends

## Capital Expenditures and R&D Investments
- Capex allocation and strategic priorities
- R&D spending focus areas and innovation pipeline
- Expected returns on current investments
- Future investment requirements

## Outlook and Strategy
- Management guidance and expectations
- Strategic initiatives and competitive positioning
- Growth drivers and market opportunities
- New product launches or market expansions

## Risk Factors and Regulatory Environment
- Material business risks and potential impact
- Regulatory challenges or opportunities
- Competitive threats and market risks
- Operational and financial risk mitigation strategies

## Management Discussion and Notable Policy Changes
- Key management commentary and strategic focus
- Accounting policy changes or one-time items
- Corporate governance or leadership changes
- Market positioning and competitive strategy

Use specific financial metrics, percentages, and dollar amounts where available from the provided sections. Include year-over-year comparisons and context for all major financial metrics. Maintain a professional, analytical tone suitable for institutional investors.

**Source Section Summaries:**
{sections_text}

Please provide a comprehensive analysis following the structure above, ensuring each section contains substantial detail and specific financial metrics where available.
"""
    
    return system_prompt, user_prompt

def generate_comprehensive_report(accession_number: str) -> Optional[str]:
    """Generate a comprehensive report for the given filing."""
    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        print(f"Connected to PostgreSQL database for comprehensive report generation.")

        # Create table first if it doesn't exist
        create_comprehensive_reports_table(cur)
        conn.commit()

        # Fetch section summaries
        print(f"Fetching section summaries for {accession_number}...")
        section_summaries = []
        available_sections = []
        
        for section_key in SOURCE_SECTION_KEYS:
            cur.execute(
                """SELECT summary_text FROM sec_section_summaries
                   WHERE filing_accession_number = %s AND section_key = %s 
                     AND summarization_model_name = %s AND processing_status = 'reduce_complete'""",
                (accession_number, section_key, SOURCE_SUMMARIES_MODEL_NAME)
            )
            result = cur.fetchone()
            if result and result[0]:
                section_summaries.append({"key": section_key, "summary": result[0]})
                available_sections.append(section_key)
                print(f"  Found summary for: {section_key}")
            else:
                print(f"  No summary found for: {section_key}")

        if not section_summaries:
            print(f"No section summaries found for {accession_number}")
            return None

        print(f"Available sections: {available_sections}")

        # Now check if report already exists using the EXACT constraint fields
        print(f"Checking for existing report with sections: {available_sections}")
        cur.execute(
            """SELECT comprehensive_report_text FROM sec_comprehensive_reports 
               WHERE filing_accession_number = %s AND report_model_name = %s 
               AND source_section_keys = %s""",
            (accession_number, COMPREHENSIVE_REPORT_MODEL, available_sections)
        )
        existing_report = cur.fetchone()
        if existing_report:
            print(f"Found existing comprehensive report for {accession_number}. Returning cached version.")
            print(f"Report length: {len(existing_report[0])} characters")
            return existing_report[0]
        else:
            print(f"No existing report found matching exact section keys: {available_sections}")

        # Get filing metadata
        filing_metadata = get_filing_metadata(cur, accession_number)
        if not filing_metadata:
            print(f"Could not find filing metadata for {accession_number}")
            return None

        # Create comprehensive report prompt
        system_prompt, user_prompt = create_comprehensive_report_prompt(filing_metadata, section_summaries)
        
        prompt_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        print(f"Generating comprehensive report using {COMPREHENSIVE_REPORT_MODEL}...")
        comprehensive_report = call_openai_api(
            openai_client, 
            prompt_messages, 
            COMPREHENSIVE_REPORT_MODEL, 
            MAX_TOKENS_FOR_COMPREHENSIVE_REPORT
        )

        if not comprehensive_report:
            print("Failed to generate comprehensive report.")
            return None

        # Save to database
        report_metadata = {
            "available_sections": available_sections,
            "word_count": len(comprehensive_report.split()),
            "ticker": filing_metadata.get("ticker"),
            "generated_model": COMPREHENSIVE_REPORT_MODEL
        }

        try:
            cur.execute(
                """INSERT INTO sec_comprehensive_reports 
                   (filing_accession_number, report_model_name, source_section_keys, 
                    comprehensive_report_text, report_metadata)
                   VALUES (%s, %s, %s, %s, %s)""",
                (accession_number, COMPREHENSIVE_REPORT_MODEL, available_sections, 
                 comprehensive_report, json.dumps(report_metadata))
            )
            conn.commit()
            print(f"Comprehensive report saved to database for {accession_number}")
        except psycopg2.errors.UniqueViolation:
            # Another process might have created the report while we were generating it
            print(f"Report already exists (created by another process). Fetching existing report for {accession_number}")
            conn.rollback()
            cur.execute(
                """SELECT comprehensive_report_text FROM sec_comprehensive_reports 
                   WHERE filing_accession_number = %s AND report_model_name = %s 
                   ORDER BY id DESC LIMIT 1""",
                (accession_number, COMPREHENSIVE_REPORT_MODEL)
            )
            existing_report = cur.fetchone()
            if existing_report:
                return existing_report[0]
            else:
                print("Error: Could not fetch existing report after constraint violation")
                return None

        return comprehensive_report

    except Exception as e:
        print(f"Error generating comprehensive report: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def main():
    """Main function for testing comprehensive report generation."""
    if len(sys.argv) > 1:
        accession_number = sys.argv[1]
    else:
        # Default to TSLA filing for testing
        accession_number = "0001628280-24-002390"
    
    print(f"Generating comprehensive report for accession number: {accession_number}")
    report = generate_comprehensive_report(accession_number)
    
    if report:
        print("\n" + "="*80)
        print("COMPREHENSIVE REPORT GENERATED:")
        print("="*80)
        print(report)
        print("="*80)
    else:
        print("Failed to generate comprehensive report.")

if __name__ == "__main__":
    main() 