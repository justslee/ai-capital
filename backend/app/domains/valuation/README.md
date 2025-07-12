# Valuation Domain - AI Capital

The valuation domain provides institutional-grade company valuation calculations using industry-standard methodologies. It focuses on DCF (Discounted Cash Flow) modeling with comprehensive financial data integration to deliver accurate intrinsic value assessments for equity analysis.

## Features

### ✅ Implemented
- **DCF Valuation Models**: Professional-grade discounted cash flow calculations
- **Financial Data Integration**: Real-time financial data via Financial Modeling Prep API
- **Multi-Statement Analysis**: Income statement, balance sheet, and cash flow analysis
- **Customizable Parameters**: Configurable discount rates, growth rates, and projection periods
- **Historical Analysis**: 5-year historical financial data analysis
- **Key Metrics Calculation**: Financial ratios, growth rates, and profitability metrics
- **Error Handling**: Robust error handling with structured exceptions
- **Caching**: Redis caching for expensive financial data operations

### 🚧 Planned
- **Comparable Company Analysis**: Peer valuation multiples
- **Sensitivity Analysis**: Monte Carlo simulations for valuation ranges
- **Sector-Specific Models**: Industry-tailored valuation approaches
- **Options Pricing**: Black-Scholes and binomial models
- **Credit Analysis**: Credit risk assessment and bond valuation
- **ESG Integration**: Environmental, Social, and Governance factors

## Architecture

```
valuation/
├── api/                          # REST API endpoints
│   ├── valuation_endpoints.py   # Main valuation API
│   ├── public_endpoints.py      # Public API endpoints
│   └── internal_endpoints.py    # Internal operations
├── services/                     # Business logic services
│   ├── valuation.py             # Main valuation logic
│   ├── financials.py            # Financial data processing
│   └── fmp_client.py            # Financial Modeling Prep client
├── models/                       # Data models
│   └── __init__.py              # Domain models
├── config/                       # Configuration management
│   └── __init__.py              # Domain configuration
└── repositories/                 # Data access layer (future)
    └── __init__.py              # Repository patterns
```

## Quick Start

### 1. Environment Setup

Set your Financial Modeling Prep API key:
```bash
export FMP_API_KEY="your_fmp_api_key"
```

Get a free API key at: https://financialmodelingprep.com/

### 2. Start the API Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test the Installation

```bash
# Health check
curl http://localhost:8000/health

# Test DCF valuation
curl "http://localhost:8000/api/v1/valuation/dcf/AAPL"

# Test financial data
curl "http://localhost:8000/api/v1/valuation/financials/AAPL"
```

## API Usage

### DCF Valuation Endpoint

```bash
GET /api/v1/valuation/dcf/{ticker}
```

**Parameters:**
- `ticker`: Company ticker symbol (e.g., AAPL, TSLA, MSFT)

**Query Parameters:**
- `discount_rate`: Custom discount rate (optional, default: 0.10)
- `terminal_growth_rate`: Terminal growth rate (optional, default: 0.025)
- `projection_years`: Projection period (optional, default: 5)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/valuation/dcf/AAPL?discount_rate=0.12&projection_years=10"
```

**Example Response:**
```json
{
  "status": "success",
  "message": "DCF valuation calculated successfully",
  "data": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "valuation_date": "2024-01-15",
    "intrinsic_value_per_share": 185.42,
    "current_share_price": 192.53,
    "upside_downside": -3.7,
    "valuation_summary": {
      "total_intrinsic_value": 2891849280000,
      "shares_outstanding": 15599800000,
      "enterprise_value": 2950000000000,
      "net_debt": -58150720000
    },
    "dcf_components": {
      "projected_free_cash_flows": [
        {"year": 2024, "fcf": 99584000000},
        {"year": 2025, "fcf": 108456000000},
        {"year": 2026, "fcf": 118128000000},
        {"year": 2027, "fcf": 128692000000},
        {"year": 2028, "fcf": 140252000000}
      ],
      "terminal_value": 2450000000000,
      "discount_rate": 0.10,
      "terminal_growth_rate": 0.025
    },
    "financial_metrics": {
      "revenue_growth_5y": 0.076,
      "fcf_margin": 0.27,
      "roic": 0.31,
      "debt_to_equity": 0.18
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Financial Data Endpoint

```bash
GET /api/v1/valuation/financials/{ticker}
```

**Parameters:**
- `ticker`: Company ticker symbol
- `years`: Number of years of historical data (optional, default: 5)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/valuation/financials/AAPL?years=3"
```

**Example Response:**
```json
{
  "status": "success",
  "message": "Financial data retrieved successfully",
  "data": {
    "ticker": "AAPL",
    "company_name": "Apple Inc.",
    "years_of_data": 3,
    "income_statements": [
      {
        "year": 2023,
        "revenue": 394328000000,
        "operating_income": 114301000000,
        "net_income": 96995000000,
        "eps": 6.16
      }
    ],
    "balance_sheets": [
      {
        "year": 2023,
        "total_assets": 352755000000,
        "total_debt": 123930000000,
        "shareholders_equity": 62146000000,
        "cash_and_equivalents": 29965000000
      }
    ],
    "cash_flows": [
      {
        "year": 2023,
        "operating_cash_flow": 110563000000,
        "capex": -10959000000,
        "free_cash_flow": 99604000000
      }
    ],
    "key_metrics": {
      "current_ratio": 1.04,
      "debt_to_equity": 1.99,
      "return_on_equity": 1.56,
      "return_on_assets": 0.27
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Configuration

### Environment Variables

```bash
# Required
FMP_API_KEY=your_fmp_api_key

# Optional API settings
FMP_BASE_URL=https://financialmodelingprep.com/api/v3
FMP_RATE_LIMIT_PER_MINUTE=300

# Optional DCF settings
DCF_DISCOUNT_RATE=0.10
DCF_TERMINAL_GROWTH_RATE=0.025
DCF_PROJECTION_YEARS=5

# Optional risk settings
RISK_FREE_RATE=0.045
MARKET_RISK_PREMIUM=0.06

# Optional caching
FINANCIAL_CACHE_TTL=86400
HISTORICAL_YEARS=5

# Optional validation
MAX_MARKET_CAP_THRESHOLD=10000000000000
MIN_MARKET_CAP_THRESHOLD=1000000
```

### Configuration Class

```python
from app.domains.valuation.config import get_valuation_config

# Get configuration
config = get_valuation_config()

# Access DCF parameters
dcf_params = config.get_dcf_params()
```

## Valuation Methodologies

### DCF (Discounted Cash Flow) Model

The DCF model calculates intrinsic value by discounting projected free cash flows to present value.

**Key Components:**
1. **Historical Analysis**: 5-year financial history analysis
2. **Growth Projections**: Revenue and margin forecasting
3. **Free Cash Flow Calculation**: Operating cash flow minus capex
4. **Terminal Value**: Perpetuity growth model
5. **Discount Rate**: WACC or required rate of return

**Formula:**
```
Intrinsic Value = Σ(FCF_t / (1 + r)^t) + Terminal Value / (1 + r)^n
```

Where:
- FCF_t = Free Cash Flow in year t
- r = Discount rate (WACC)
- n = Number of projection years

### Financial Ratio Analysis

**Profitability Ratios:**
- Return on Equity (ROE)
- Return on Assets (ROA)
- Operating Margin
- Net Margin

**Efficiency Ratios:**
- Asset Turnover
- Inventory Turnover
- Receivables Turnover
- Return on Invested Capital (ROIC)

**Leverage Ratios:**
- Debt-to-Equity
- Interest Coverage
- Debt-to-Assets
- Times Interest Earned

**Liquidity Ratios:**
- Current Ratio
- Quick Ratio
- Cash Ratio
- Working Capital

## Data Sources

### Financial Modeling Prep API

**Coverage:**
- 15,000+ public companies
- 20+ years of historical data
- Real-time financial statements
- Key financial metrics and ratios

**Data Quality:**
- GAAP and IFRS compliant
- Quarterly and annual data
- Adjusted for stock splits and dividends
- Comprehensive footnote data

**Rate Limits:**
- Free tier: 250 requests/day
- Paid tiers: Up to 10,000 requests/day
- Real-time data available

### Alternative Data Sources (Planned)

- **Alpha Vantage**: Fundamental data and ratios
- **Quandl**: Economic and financial data
- **Yahoo Finance**: Market data and basic financials
- **SEC EDGAR**: Direct filing data

## Error Handling

### Common Errors

**Data Not Available**
- Ticker symbol not found
- Historical data insufficient
- Financial statements missing

**Calculation Errors**
- Negative free cash flows
- Invalid discount rates
- Missing key financial metrics

**API Errors**
- Rate limit exceeded
- Network connectivity issues
- Invalid API key

### Error Response Structure

```json
{
  "status": "error",
  "message": "Financial data not found",
  "error": {
    "error_code": "FINANCIAL_DATA_NOT_FOUND",
    "details": {
      "ticker": "INVALID",
      "years_requested": 5,
      "data_source": "FMP"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Performance Optimization

### Caching Strategy

- **Financial Data**: 24-hour cache for financial statements
- **DCF Results**: 1-hour cache for valuation results
- **Company Profiles**: 7-day cache for company information
- **Error Responses**: 5-minute cache for missing data

### Rate Limiting

- **FMP API**: Automatic retry with exponential backoff
- **Concurrent Requests**: Limited to 5 simultaneous requests
- **Request Batching**: Batch multiple company requests

### Data Validation

- **Sanity Checks**: Validate financial data consistency
- **Range Checks**: Ensure realistic financial metrics
- **Historical Validation**: Compare with historical trends
- **Error Detection**: Identify and flag data anomalies

## Development

### Running Tests

```bash
# Run valuation tests
pytest tests/domains/valuation/

# Run specific test files
pytest tests/domains/valuation/test_valuation.py
pytest tests/domains/valuation/test_financials.py
```

### Local Development

```bash
# Run DCF calculation directly
cd backend/app/domains/valuation
python -m services.valuation

# Test financial data client
python -m services.fmp_client
```

### Adding New Features

1. **New Valuation Models**: Add to `services/valuation.py`
2. **Additional Metrics**: Extend financial ratio calculations
3. **New Data Sources**: Create new client services
4. **Enhanced Validation**: Add data quality checks
5. **Sector Models**: Create industry-specific valuations

## Integration

### With Other Domains

```python
# Use with summarization domain
from app.domains.valuation.services.valuation import calculate_dcf
from app.domains.summarization.services.summary_generation import generate_summary

# Get both valuation and business context
dcf_result = await calculate_dcf("AAPL")
summary = await generate_summary("AAPL", 2023, "10-K")
```

### External Services

- **Financial Modeling Prep**: Primary financial data source
- **SEC EDGAR**: Filing data integration
- **Redis**: Caching layer for performance
- **PostgreSQL**: Historical data storage

## Best Practices

### Valuation Quality

1. **Multiple Scenarios**: Run sensitivity analysis
2. **Historical Validation**: Compare with historical valuations
3. **Peer Comparison**: Benchmark against similar companies
4. **Regular Updates**: Update models with new data

### Data Quality

1. **Validate Inputs**: Check data consistency
2. **Handle Missing Data**: Implement fallback strategies
3. **Monitor Sources**: Track data source reliability
4. **Version Control**: Track model versions and changes

### Performance

1. **Cache Aggressively**: Financial data changes infrequently
2. **Batch Operations**: Process multiple companies together
3. **Optimize Queries**: Minimize API calls
4. **Monitor Usage**: Track API costs and limits

## Industry Applications

### Investment Banking
- **M&A Valuations**: Target company assessments
- **IPO Pricing**: Pre-public company valuations
- **Fairness Opinions**: Independent valuation analysis

### Asset Management
- **Stock Selection**: Identify undervalued securities
- **Portfolio Construction**: Risk-adjusted returns
- **Performance Attribution**: Understand value drivers

### Corporate Finance
- **Capital Budgeting**: Project valuation decisions
- **Strategic Planning**: Business unit valuations
- **Investor Relations**: Communicate intrinsic value

## Contributing

1. Follow financial industry standards and practices
2. Implement comprehensive input validation
3. Add unit tests for all calculation methods
4. Document assumptions and methodologies
5. Maintain audit trail for valuation decisions

## License

Part of the AI Capital project. See the main project LICENSE file. 