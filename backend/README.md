# AI Capital Backend

The AI Capital backend provides institutional-grade financial analysis through a domain-driven architecture with three core business domains: Summarization, Valuation, and Modeling.

## Architecture Overview

The backend uses a modern domain-driven architecture that separates business logic into clear, focused modules:

```
backend/
├── app/
│   ├── domains/                  # Business domains
│   │   ├── shared/               # Shared utilities and configuration
│   │   ├── summarization/        # SEC filing analysis
│   │   ├── valuation/            # Company valuation calculations
│   │   └── modeling/             # Price prediction and data modeling
│   ├── api/                      # API layer and dependencies
│   ├── config.py                 # Application configuration
│   ├── main.py                   # FastAPI application entry point
│   └── models/                   # Database models
├── alembic/                      # Database migrations
└── requirements.txt              # Dependencies
```

## Domain Structure

Each domain follows a consistent internal structure:

```
domain_name/
├── __init__.py
├── api/                         # REST API endpoints
├── services/                    # Business logic services  
├── models/                      # Domain data models
├── config/                      # Domain configuration
├── repositories/                # Data access layer (where applicable)
└── [domain-specific dirs]       # Additional domain functionality
```

## Core Domains

### 📊 Summarization Domain
**Purpose**: AI-powered analysis of SEC filings (10-K, 10-Q, 8-K)

**Key Features**:
- Automated text extraction from SEC HTML filings
- Section-level summarization (Business, MD&A, Risk Factors)
- Top-level comprehensive summaries for hedge fund managers
- OpenAI GPT-4 integration with optimized token usage
- Structured output with business insights

**API Endpoints**:
- `GET /api/v1/summary/{ticker}/{year}/{form_type}` - Get filing summary

### 💰 Valuation Domain
**Purpose**: Professional-grade company valuation calculations

**Key Features**:
- DCF (Discounted Cash Flow) calculations
- Financial data integration via Financial Modeling Prep API
- Customizable valuation parameters (discount rate, growth rate)
- Historical financial data analysis
- Intrinsic value calculations

**API Endpoints**:
- `GET /api/v1/valuation/dcf/{ticker}` - DCF valuation
- `GET /api/v1/valuation/financials/{ticker}` - Financial data

### 🔮 Modeling Domain
**Purpose**: Historical market data and ML modeling infrastructure

**Key Features**:
- Multi-source data ingestion (Tiingo, AlphaVantage)
- S&P 100 coverage with 50+ years of historical data
- High-performance DuckDB + Parquet storage
- Bulk data processing with rate limiting
- Foundation for ML model training

**API Endpoints**:
- `POST /api/v1/modeling/ingest/{ticker}` - Data ingestion
- `GET /api/v1/modeling/data/coverage` - Data coverage
- `GET /api/v1/modeling/symbols` - Available symbols

## Quick Start

### 1. Environment Setup

Create a `.env` file with required API keys:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/ai_capital

# OpenAI (for SEC analysis)
OPENAI_API_KEY=your_openai_api_key

# Financial Modeling Prep (for financials)
FMP_API_KEY=your_fmp_api_key

# Tiingo (for market data)
TIINGO_API_KEY=your_tiingo_api_key

# Optional: Additional services
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head
```

### 4. Start the Server

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Test summarization
curl "http://localhost:8000/api/v1/summary/AAPL/2023/10-K"

# Test valuation
curl "http://localhost:8000/api/v1/valuation/dcf/AAPL"
```

## API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Core Endpoints

#### Summarization API
```bash
# Get SEC filing summary
GET /api/v1/summary/{ticker}/{year}/{form_type}

# Example: Apple's 2023 10-K
curl "http://localhost:8000/api/v1/summary/AAPL/2023/10-K"
```

#### Valuation API
```bash
# Get DCF valuation
GET /api/v1/valuation/dcf/{ticker}

# Example: Apple DCF valuation
curl "http://localhost:8000/api/v1/valuation/dcf/AAPL"
```

#### Modeling API
```bash
# Ingest market data
POST /api/v1/modeling/ingest/{ticker}?start_date=2020-01-01

# Bulk ingest S&P 100
POST /api/v1/modeling/ingest/bulk/sp100?start_date=2020-01-01
```

## Configuration

### Domain Configuration

Each domain uses Pydantic-based configuration with environment variable support:

```python
# Summarization configuration
SECTION_SUMMARY_MODEL=gpt-4-turbo
MAX_TOKENS_TOP_LEVEL_SUMMARY=700
SOURCE_SECTION_KEYS=Business,MD&A,Risk Factors

# Valuation configuration
DCF_DISCOUNT_RATE=0.10
DCF_TERMINAL_GROWTH_RATE=0.025
DCF_PROJECTION_YEARS=5

# Modeling configuration
TIINGO_RATE_LIMIT_PER_HOUR=500
MAX_CONCURRENT_REQUESTS=5
DEFAULT_START_DATE=1970-01-01
```

### Shared Configuration

Common settings are managed through the shared configuration system:

```python
# Database and caching
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL_SECONDS=3600

# API settings
API_TIMEOUT_SECONDS=30
MAX_RETRIES=3
BACKOFF_FACTOR=2.0
```

## Database Schema

### Core Tables

**SEC Filing Data**:
- `sec_filings` - Raw filing metadata and content
- `filing_sections` - Extracted text sections
- `sec_section_summaries` - Generated summaries

**Financial Data**:
- `companies` - Company information
- `financial_statements` - Income statements, balance sheets, cash flow
- `financial_ratios` - Key financial metrics

**Market Data**:
- `daily_prices` - Historical price data
- `tickers` - Ticker metadata
- `data_ingestion_logs` - Processing logs

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific domain tests
pytest tests/domains/summarization/
pytest tests/domains/valuation/
pytest tests/domains/modeling/
```

### Domain Development

Each domain is independently developable:

```bash
# Summarization domain
cd app/domains/summarization
python -m services.summarize_sections

# Valuation domain
cd app/domains/valuation
python -m services.valuation

# Modeling domain
cd app/domains/modeling
python -m cli.duckdb_cli --help
```

### Adding New Domains

1. Create domain directory structure
2. Implement domain configuration extending `BaseDomainConfig`
3. Add API endpoints in `api/` subdirectory
4. Create business logic in `services/`
5. Add domain router to main application

## Performance

### Optimization Features

- **Async Processing**: All API endpoints are fully async
- **Connection Pooling**: Database connections are pooled
- **Caching**: Redis caching for expensive operations
- **Rate Limiting**: Built-in rate limiting for external APIs
- **Batching**: Bulk operations for data processing

### Performance Metrics

- **Summarization**: ~30-60 seconds for 10-K analysis
- **Valuation**: ~2-5 seconds for DCF calculations
- **Data Ingestion**: ~1000 records/minute for market data

## Security

### API Security

- Environment variable configuration
- Input validation with Pydantic
- SQL injection prevention with ORM
- Rate limiting on external API calls
- Structured error handling

### Data Security

- Encrypted database connections
- API key management through environment variables
- No sensitive data in logs or responses
- Proper exception handling

## Monitoring

### Health Checks

- `/health` - Basic application health
- `/health/detailed` - Detailed service health
- Domain-specific health endpoints

### Logging

- Structured logging with correlation IDs
- Domain-specific log levels
- Performance metrics tracking
- Error tracking and alerting

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t ai-capital-backend .

# Run container
docker run -p 8000:8000 --env-file .env ai-capital-backend
```

### Environment Variables

Required for production:
- `DATABASE_URL` - PostgreSQL connection
- `OPENAI_API_KEY` - OpenAI API access
- `FMP_API_KEY` - Financial data access
- `TIINGO_API_KEY` - Market data access

## Contributing

1. Follow domain-driven architecture patterns
2. Use shared utilities from `domains/shared/`
3. Add comprehensive tests for new features
4. Update API documentation
5. Follow existing code style and patterns

## License

Part of the AI Capital project. See the main project LICENSE file. 