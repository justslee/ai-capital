# AI Capital - Domain-Based Architecture

This document outlines the new domain-based architecture for the AI Capital project, which clearly separates the three main business domains.

## Architecture Overview

The project is now organized into three main domains:

```
backend/app/domains/
├── summarization/          # Financial statement and SEC filing summarization
├── valuation/             # Company valuation calculations  
└── modeling/              # Price prediction and modeling
```

## Domain Structure

Each domain follows a consistent structure:

```
domain_name/
├── __init__.py
├── api/                   # FastAPI endpoints for this domain
├── services/              # Business logic and core services
├── core/                  # Core functionality (for summarization)
├── data_ingestion/        # Data ingestion services (for modeling)
├── features/              # Feature engineering (for modeling)
└── models/                # ML models (for modeling)
```

## Domain Responsibilities

### 📊 Summarization Domain (`/domains/summarization/`)
- **Purpose**: Financial statement and SEC filing summarization
- **Key Services**: 
  - Summary generation for 10-K filings
  - Section-level analysis (Business, MD&A, Risk Factors)
  - Text processing and chunking
  - Document embeddings
- **API Endpoints**: `/api/v1/summary/{ticker}/{year}/{form_type}`

### 💰 Valuation Domain (`/domains/valuation/`)
- **Purpose**: Company valuation calculations and financial analysis
- **Key Services**:
  - DCF (Discounted Cash Flow) calculations
  - Financial data fetching and storage
  - Financial metrics and ratios
- **API Endpoints**: 
  - `/api/v1/valuation/dcf/{ticker}`
  - `/api/v1/valuation/financials/{ticker}`

### 🔮 Modeling Domain (`/domains/modeling/`)
- **Purpose**: Price prediction and modeling functionality
- **Key Services**:
  - Price prediction models
  - Historical data ingestion
  - Technical indicator generation
  - Feature engineering
- **API Endpoints**:
  - `/api/v1/modeling/predict/{ticker}`
  - `/api/v1/modeling/ingest/{ticker}`

## Migration Benefits

1. **Clear Separation**: Each domain has distinct responsibilities
2. **Microservice Ready**: Domains can easily be split into separate services
3. **Maintainable**: Related code is co-located
4. **Scalable**: Each domain can scale independently
5. **Testable**: Domain isolation makes testing easier

## API Structure

All domains are accessible under `/api/v1/` with domain-specific prefixes:

- Summarization: `/api/v1/summary/...`
- Valuation: `/api/v1/valuation/...`
- Modeling: `/api/v1/modeling/...`

## Future Microservice Migration

When ready to split into microservices, each domain can become its own service:

```
ai-capital-summarization/    # Summarization microservice
ai-capital-valuation/        # Valuation microservice  
ai-capital-modeling/         # Modeling microservice
```

Each would maintain its own database, API, and deployment pipeline while communicating via well-defined APIs. 