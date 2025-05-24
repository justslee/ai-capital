# SEC Filing Summarization Backend

This backend provides a comprehensive system for processing SEC filings through a 5-step pipeline and serving summaries via a REST API.

## Architecture Overview

```
backend/
├── app/                          # Main application code
│   ├── api/                      # REST API endpoints
│   │   └── endpoints/
│   │       └── summary_endpoint.py
│   ├── core/                     # Configuration and utilities
│   │   ├── config.py
│   │   └── database.py
│   ├── db/                       # Database utilities
│   ├── models/                   # Database models (if using ORM)
│   ├── schemas/                  # Pydantic schemas
│   ├── services/                 # Business logic services
│   └── pipeline/                 # 5-Step Summarization Pipeline
│       ├── orchestrator.py      # Pipeline orchestrator
│       ├── ingestion/            # Step 1: Data Ingestion
│       ├── parsing/              # Step 2: Parsing and Cleaning
│       ├── chunking/             # Step 3: Document Chunking
│       ├── embeddings/           # Step 4: Embedding Generation
│       └── summarization/        # Step 5: Summary Generation
├── alembic/                      # Database migrations
├── main.py                       # FastAPI application entry point
└── README.md                     # This file
```

## 5-Step Summarization Pipeline

The system processes SEC filings through the following stages:

### 1. Data Ingestion (`pipeline/ingestion/`)
- Downloads SEC filings from EDGAR database
- Stores raw HTML content in PostgreSQL database
- Handles specific accession numbers or latest filings by ticker

**Key Files:**
- `ingest_specific_filings.py` - Process specific accession numbers
- `test_filing_ingestion.py` - Process latest filings by ticker

### 2. Parsing and Cleaning (`pipeline/parsing/`)
- Extracts clean text from HTML filings
- Identifies and labels document sections (Business, MD&A, Risk Factors, etc.)
- Removes HTML tags and normalizes text formatting

**Key Files:**
- `extract_text_from_html.py` - Main text extraction and section identification

### 3. Document Chunking (`pipeline/chunking/`)
- Breaks large documents into manageable chunks
- Maintains semantic coherence within chunks
- Optimizes chunk sizes for LLM processing

**Key Files:**
- `validate_chunked_output.py` - Validates chunking results

### 4. Embedding Generation (`pipeline/embeddings/`)
- Generates vector embeddings for document chunks
- Stores embeddings in Pinecone vector database
- Enables semantic search and retrieval

**Key Files:**
- `generate_embeddings.py` - Creates and stores embeddings

### 5. Summary Generation (`pipeline/summarization/`)
- Creates section-level summaries using OpenAI GPT
- Generates top-level document summaries
- Optimizes token usage through intelligent chunking

**Key Files:**
- `summarize_sections.py` - Generate section summaries
- `generate_top_level_summary.py` - Create top-level summaries

## Running the Pipeline

### Full Pipeline
```bash
cd backend
PYTHONPATH=. python app/pipeline/orchestrator.py
```

### Individual Steps
```bash
# Step 1: Ingestion
PYTHONPATH=. python app/pipeline/ingestion/ingest_specific_filings.py

# Step 2: Parsing
PYTHONPATH=. python app/pipeline/parsing/extract_text_from_html.py

# Step 4: Embeddings
PYTHONPATH=. python app/pipeline/embeddings/generate_embeddings.py

# Step 5: Summarization
PYTHONPATH=. python app/pipeline/summarization/summarize_sections.py
```

## API Server

### Starting the Server
```bash
cd backend
PYTHONPATH=. uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### Summary Endpoint
```
GET /api/v1/summary/{ticker}/{year}/{form_type}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/summary/TSLA/2024/10-K"
```

**Response:**
```json
{
  "ticker": "TSLA",
  "year": 2024,
  "form_type": "10-K",
  "business_summary": "...",
  "mdna_summary": "...",
  "risk_factors_summary": "...",
  "top_level_summary": "..."
}
```

#### Health Check
```
GET /health
```

## Configuration

The system requires the following environment variables:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
```

## Token Optimization

The system optimizes OpenAI API usage through:

1. **Intelligent Chunking**: Documents are broken into semantically coherent chunks
2. **Section-Level Processing**: Each section is summarized independently 
3. **Progressive Summarization**: Section summaries are combined for top-level summaries
4. **Token Management**: Chunk sizes are optimized to stay within model limits

This approach significantly reduces token usage compared to sending entire documents, while maintaining summary quality and coherence.

## Database Schema

The system uses PostgreSQL with the following key tables:
- `sec_filings` - Raw filing metadata and HTML content
- `filing_sections` - Extracted and labeled text sections
- `section_chunks` - Chunked content for processing
- `section_summaries` - Generated section summaries

## Technologies Used

- **FastAPI** - REST API framework
- **PostgreSQL** - Primary database
- **Pinecone** - Vector database for embeddings
- **OpenAI GPT** - Large language model for summarization
- **Beautiful Soup** - HTML parsing
- **Pydantic** - Data validation and settings 