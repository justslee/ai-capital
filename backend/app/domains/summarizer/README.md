# Summarization Domain - AI Capital

The summarization domain provides intelligent analysis of SEC filings using advanced AI to extract key business insights, risk factors, and management discussions. It transforms complex financial documents into actionable summaries for hedge fund managers and institutional investors.

## Features

### ✅ Implemented
- **Multi-Format Support**: 10-K, 10-Q, 8-K filing analysis
- **Section-Level Analysis**: Business, MD&A, Risk Factors extraction
- **AI-Powered Summarization**: GPT-4 integration with optimized prompts
- **Top-Level Synthesis**: Comprehensive summaries combining all sections
- **Token Optimization**: Intelligent chunking to minimize API costs
- **Structured Output**: Consistent JSON responses with business insights
- **Error Handling**: Robust error handling with structured exceptions
- **Caching**: Redis caching for expensive operations

### 🚧 Planned
- **Embedding Generation**: Vector embeddings for semantic search
- **Comparative Analysis**: Multi-year and peer comparison
- **Custom Prompts**: User-defined summarization templates
- **Batch Processing**: Bulk filing analysis
- **Multi-Language Support**: Analysis of international filings

## Architecture

```
summarization/
├── api/                          # REST API endpoints
│   └── summary_endpoint.py      # Main summarization API
├── services/                     # Business logic services
│   ├── llm_services.py          # OpenAI integration
│   ├── summarize_sections.py    # Section summarization
│   ├── summary_generation.py    # Main orchestration
│   └── generate_top_level_summary.py  # Top-level synthesis
├── parsing/                      # Text processing utilities
│   └── extract_text_from_html.py  # HTML parsing and cleaning
├── chunking/                     # Document chunking
│   └── validate_chunked_output.py  # Chunk validation
├── embeddings/                   # Vector embeddings (future)
│   └── generate_embeddings.py   # Embedding generation
├── repositories/                 # Data access layer
│   └── section_summary_repository.py  # Database operations
├── config/                       # Configuration management
│   └── __init__.py              # Domain configuration
└── models/                       # Data models
    └── __init__.py              # Domain models
```

## Quick Start

### 1. Environment Setup

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your_openai_api_key"
```

Get a free API key at: https://platform.openai.com/

### 2. Optional: Pinecone Setup (for embeddings)

```bash
export PINECONE_API_KEY="your_pinecone_api_key"
export PINECONE_ENVIRONMENT="your_pinecone_environment"
```

### 3. Start the API Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test the Installation

```bash
# Health check
curl http://localhost:8000/health

# Test summarization
curl "http://localhost:8000/api/v1/summary/AAPL/2023/10-K"
```

## API Usage

### Primary Endpoint

```bash
GET /api/v1/summary/{ticker}/{year}/{form_type}
```

**Parameters:**
- `ticker`: Company ticker symbol (e.g., AAPL, TSLA, MSFT)
- `year`: Filing year (e.g., 2023, 2024)
- `form_type`: SEC form type (10-K, 10-Q, 8-K)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/summary/AAPL/2023/10-K"
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Summary generated successfully",
  "data": {
    "ticker": "AAPL",
    "year": 2023,
    "form_type": "10-K",
    "business_summary": "Apple Inc. designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories...",
    "mdna_summary": "Apple's fiscal 2023 performance was driven by strong iPhone sales despite challenging macroeconomic conditions...",
    "risk_factors_summary": "Key risks include supply chain disruptions, intense competition, and regulatory changes in key markets...",
    "top_level_summary": "Apple demonstrates resilient business model with strong cash generation, though facing headwinds from economic uncertainty and increased competition in key product categories...",
    "processing_metadata": {
      "sections_processed": 3,
      "total_tokens_used": 2847,
      "processing_time_seconds": 45.2
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Responses

```json
{
  "status": "error",
  "message": "Filing not found",
  "error": {
    "error_code": "FILING_NOT_FOUND",
    "details": {
      "ticker": "INVALID",
      "year": 2023,
      "form_type": "10-K"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional model settings
SECTION_SUMMARY_MODEL=gpt-4-turbo
TOP_LEVEL_SUMMARY_MODEL=gpt-4-turbo
MAX_TOKENS_TOP_LEVEL_SUMMARY=700
MAX_TOKENS_SECTION_SUMMARY=150

# Optional processing settings
CHUNK_SIZE=4000
CHUNK_OVERLAP=200
MAX_CONCURRENT_SUMMARIZATIONS=3
SUMMARIZATION_TIMEOUT=300

# Optional section configuration
SOURCE_SECTION_KEYS=Business,MD&A,Risk Factors
ENABLE_SECTION_FILTERING=true

# Optional embedding settings
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX_NAME=sec-filings
```

### Configuration Class

```python
from app.domains.summarization.config import get_summarization_config

# Get configuration
config = get_summarization_config()

# Access model settings
model_params = config.get_model_params()
processing_params = config.get_processing_params()
```

## Data Processing Pipeline

### 1. Data Ingestion
- Retrieves SEC filings from database
- Validates ticker, year, and form type
- Handles missing or incomplete data

### 2. HTML Parsing
- Extracts clean text from SEC HTML filings
- Identifies document sections (Business, MD&A, Risk Factors)
- Removes formatting and normalizes text

### 3. Content Chunking
- Breaks large sections into manageable chunks
- Maintains semantic coherence
- Optimizes for LLM token limits

### 4. AI Summarization
- Uses GPT-4 with optimized prompts
- Generates section-level summaries
- Combines sections for top-level synthesis

### 5. Response Generation
- Structures output in consistent format
- Includes processing metadata
- Provides error handling and validation

## Supported Filing Types

### 10-K (Annual Report)
- **Sections**: Business, Risk Factors, MD&A, Financial Statements
- **Typical Length**: 50-200 pages
- **Processing Time**: 30-60 seconds
- **Key Insights**: Annual performance, strategy, competitive position

### 10-Q (Quarterly Report)
- **Sections**: Financial Information, MD&A, Legal Proceedings
- **Typical Length**: 20-50 pages
- **Processing Time**: 15-30 seconds
- **Key Insights**: Quarterly performance, recent developments

### 8-K (Current Report)
- **Sections**: Event-specific disclosures
- **Typical Length**: 5-20 pages
- **Processing Time**: 10-20 seconds
- **Key Insights**: Material events, executive changes, acquisitions

## Token Optimization

The system optimizes OpenAI API usage through:

1. **Intelligent Chunking**: Documents are broken into semantically coherent chunks
2. **Section-Level Processing**: Each section is summarized independently
3. **Progressive Summarization**: Section summaries are combined for top-level summaries
4. **Token Management**: Chunk sizes are optimized to stay within model limits

### Token Usage Examples

| Filing Type | Average Tokens | Cost (GPT-4) | Processing Time |
|-------------|---------------|--------------|-----------------|
| 10-K        | 2,000-4,000   | $0.06-$0.12 | 30-60 seconds   |
| 10-Q        | 1,000-2,000   | $0.03-$0.06 | 15-30 seconds   |
| 8-K         | 500-1,000     | $0.015-$0.03| 10-20 seconds   |

## Error Handling

### Common Errors

**Filing Not Found**
- Ticker symbol doesn't exist
- Filing year not available
- Form type not supported

**Processing Errors**
- OpenAI API rate limits
- Network connectivity issues
- Invalid HTML structure

**Configuration Errors**
- Missing API keys
- Invalid model settings
- Database connectivity issues

### Error Response Structure

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error": {
    "error_code": "SPECIFIC_ERROR_CODE",
    "details": {
      "additional": "error context"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Performance Optimization

### Caching Strategy

- **Section Summaries**: Cached for 24 hours
- **Top-Level Summaries**: Cached for 1 hour
- **Parsed Content**: Cached for 7 days
- **Error Responses**: Cached for 5 minutes

### Rate Limiting

- **OpenAI API**: Automatic retry with exponential backoff
- **Concurrent Requests**: Limited to 3 simultaneous summarizations
- **Timeout Handling**: 5-minute timeout for long documents

### Monitoring

- **Token Usage**: Track API costs per request
- **Processing Time**: Monitor performance metrics
- **Error Rates**: Track failure rates by error type
- **Cache Hit Rates**: Monitor caching effectiveness

## Development

### Running Tests

```bash
# Run summarization tests
pytest tests/domains/summarization/

# Run specific test files
pytest tests/domains/summarization/test_summarize_sections.py
pytest tests/domains/summarization/test_llm_services.py
```

### Local Development

```bash
# Run section summarization directly
cd backend/app/domains/summarization
python -m services.summarize_sections

# Run top-level summary generation
python -m services.generate_top_level_summary
```

### Adding New Features

1. **New Section Types**: Add to `SECTION_MAPPINGS` in config
2. **Custom Prompts**: Extend `SUMMARIZATION_PROMPTS` dictionary
3. **New Models**: Update model configuration
4. **Enhanced Parsing**: Extend HTML parsing logic
5. **Additional Outputs**: Modify response models

## Integration

### With Other Domains

```python
# Use with valuation domain
from app.domains.summarization.services.summary_generation import generate_summary
from app.domains.valuation.services.valuation import calculate_dcf

# Get summary for context
summary = await generate_summary("AAPL", 2023, "10-K")
dcf_result = await calculate_dcf("AAPL", context=summary)
```

### External Services

- **SEC EDGAR**: Filing data retrieval
- **OpenAI API**: GPT-4 summarization
- **Pinecone**: Vector embeddings (optional)
- **Redis**: Caching layer

## Best Practices

### API Usage

1. **Cache Results**: Summaries are expensive to generate
2. **Batch Requests**: Process multiple filings efficiently
3. **Error Handling**: Implement proper retry logic
4. **Rate Limiting**: Respect OpenAI API limits

### Cost Optimization

1. **Use Caching**: Avoid duplicate summarizations
2. **Optimize Prompts**: Reduce token usage
3. **Monitor Usage**: Track API costs
4. **Batch Processing**: Process multiple filings together

### Quality Assurance

1. **Validate Outputs**: Check summary quality
2. **Monitor Errors**: Track processing failures
3. **User Feedback**: Collect quality metrics
4. **Continuous Improvement**: Refine prompts and processes

## Contributing

1. Follow domain-driven architecture patterns
2. Add comprehensive tests for new features
3. Update API documentation
4. Optimize for cost and performance
5. Maintain backward compatibility

## License

Part of the AI Capital project. See the main project LICENSE file. 