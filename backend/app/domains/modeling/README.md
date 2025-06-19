# Modeling Domain - AI Capital

The modeling domain provides comprehensive historical market data ingestion and analysis capabilities for machine learning model training. It supports fetching data from multiple sources with a focus on maximizing data availability for ML training purposes.

## Features

### ✅ Implemented
- **Tiingo API Integration**: Full support for historical price data (50+ years for some tickers)
- **S&P 100 Coverage**: Pre-configured list of top 100 S&P companies
- **Major Index Support**: SP500, NASDAQ, Dow Jones, Russell 2000, VIX
- **Sector ETF Coverage**: Technology, Healthcare, Financial, Energy, and more
- **Bulk Data Ingestion**: Concurrent processing with rate limiting
- **Data Validation**: Price and volume validation with configurable rules
- **Database Storage**: PostgreSQL with proper indexing and upserts
- **Ingestion Logging**: Comprehensive tracking of all ingestion activities
- **API Endpoints**: RESTful API for all operations
- **Command-Line Interface**: Easy-to-use management scripts

### 🚧 Planned
- **AlphaVantage Integration**: Additional data source for redundancy
- **Technical Indicators**: RSI, MACD, Bollinger Bands, etc.
- **Price Prediction Models**: LSTM, Random Forest, Linear Regression
- **Feature Engineering**: Automated feature generation for ML
- **Model Training Pipeline**: End-to-end ML training workflow

## Quick Start

### 1. Environment Setup

Set your Tiingo API key in your environment:
```bash
export TIINGO_API_KEY="your_tiingo_api_key"
```

Get a free API key at: https://api.tiingo.com/

### 2. Database Setup

The modeling domain uses the same PostgreSQL database as other domains. Ensure your database is running and the connection string is configured in your `.env` file.

### 3. Start the API Server

```bash
cd backend
python -c "import sys; sys.path.insert(0, '.'); import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=True)"
```

### 4. Test the Installation

```bash
curl http://localhost:8000/api/v1/modeling/health
```

## Data Ingestion

### Using the Command Line Interface

The easiest way to ingest data is using the provided management script:

```bash
cd backend/app/domains/modeling/scripts

# Show available symbol groups
python ingest_data.py symbols

# Ingest data for a single ticker
python ingest_data.py single AAPL --start-date 2020-01-01

# Ingest S&P 100 data (recommended starting point)
python ingest_data.py sp100 --start-date 2020-01-01 --max-concurrent 3

# Ingest all target symbols (S&P 100 + indexes + ETFs)
python ingest_data.py all --start-date 2010-01-01 --max-concurrent 5

# Ingest custom ticker list
python ingest_data.py custom AAPL MSFT GOOGL --start-date 2015-01-01

# Check data coverage
python ingest_data.py coverage --tickers AAPL MSFT GOOGL

# Check ingestion status
python ingest_data.py status
```

### Using the API

```bash
# Ingest single ticker
curl -X POST "http://localhost:8000/api/v1/modeling/ingest/AAPL?start_date=2020-01-01"

# Bulk ingest S&P 100 (background task)
curl -X POST "http://localhost:8000/api/v1/modeling/ingest/bulk/sp100?start_date=2020-01-01&run_async=true"

# Check ingestion status
curl "http://localhost:8000/api/v1/modeling/ingest/status"

# Get data coverage
curl "http://localhost:8000/api/v1/modeling/data/coverage?tickers=AAPL,MSFT,GOOGL"

# Get available symbols
curl "http://localhost:8000/api/v1/modeling/symbols"
```

## Configuration

### Environment Variables

```bash
# Required
TIINGO_API_KEY=your_tiingo_api_key

# Optional (with defaults)
TIINGO_RATE_LIMIT_PER_HOUR=500
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY_SECONDS=0.1
DEFAULT_START_DATE=1970-01-01
```

### Customization

Edit `backend/app/domains/modeling/config/modeling_config.py` to:
- Modify the S&P 100 ticker list
- Add custom sector ETFs
- Adjust validation rules
- Change rate limiting settings

## Data Structure

### Database Tables

**daily_prices**: Historical price data
- `ticker`, `date`, `open`, `high`, `low`, `close`, `volume`
- `adj_close`, `adj_open`, `adj_high`, `adj_low`, `adj_volume`
- `dividend_cash`, `split_factor`, `data_source`

**tickers**: Ticker metadata
- `ticker`, `name`, `exchange`, `sector`, `industry`, `market_cap`

**data_ingestion_logs**: Ingestion tracking
- `ticker`, `source`, `status`, `records_processed`, `error_message`

**index_prices**: Index data
- `index_name`, `date`, `value`, `change`, `change_percent`

### Data Sources

**Tiingo API**:
- Historical daily prices back to 1970s for many tickers
- Adjusted prices for splits and dividends
- High data quality and reliability
- Free tier: 500 requests/hour, 50 unique symbols/day

**AlphaVantage** (planned):
- Alternative data source for redundancy
- Technical indicators
- Real-time quotes

## Target Symbols

### S&P 100 Companies
Top 100 companies by market cap including:
- **Technology**: AAPL, MSFT, GOOGL, AMZN, META, TSLA, NVDA
- **Healthcare**: JNJ, PFE, UNH, ABBV, MRK
- **Financial**: JPM, BAC, WFC, GS, MS
- **Consumer**: HD, MCD, NKE, SBUX, KO, PEP

### Major Indexes
- **S&P 500**: SPY, ^GSPC
- **NASDAQ**: QQQ, ^IXIC, ^NDX
- **Dow Jones**: DIA, ^DJI
- **Russell 2000**: IWM, ^RUT
- **VIX**: ^VIX

### Sector ETFs
Technology, Healthcare, Financial, Energy, Materials, Industrials, Utilities, Consumer Discretionary/Staples, Real Estate, Communication

## Best Practices

### Data Ingestion Strategy

1. **Start Small**: Begin with S&P 100 for recent years (2020+)
2. **Expand Gradually**: Add more years and symbols as needed
3. **Monitor Rate Limits**: Use appropriate concurrent request limits
4. **Validate Data**: Check coverage and quality after ingestion
5. **Regular Updates**: Set up daily/weekly ingestion for recent data

### Free Tier Optimization

With Tiingo's free tier (500 requests/hour):
- S&P 100 data: ~2 hours for full historical data
- All targets: ~6-8 hours for full historical data
- Daily updates: <30 minutes

### Performance Tuning

- Adjust `max_concurrent` based on your API limits
- Use `request_delay_seconds` to avoid rate limiting
- Monitor ingestion logs for failures and retries

## Troubleshooting

### Common Issues

**"Tiingo API key is required"**
- Set the `TIINGO_API_KEY` environment variable
- Verify the key is valid at api.tiingo.com

**"Rate limit exceeded"**
- Reduce `max_concurrent` requests
- Increase `request_delay_seconds`
- Wait for the rate limit window to reset

**"No data returned for ticker"**
- Ticker may not be supported by Tiingo
- Check ticker symbol format (some use ^GSPC format)
- Verify date range is valid

**Database connection errors**
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in your environment
- Verify database permissions

### Logging

Set logging level for detailed debugging:
```python
import logging
logging.getLogger('app.domains.modeling').setLevel(logging.DEBUG)
```

## Advanced Usage

### Custom Data Sources

Extend the ingestion service to support additional data sources:

```python
# In price_data_ingestion.py
async def _fetch_from_custom_source(self, ticker, start_date, end_date):
    # Implement your custom data source
    pass
```

### Feature Engineering

Access the raw price data for feature engineering:

```python
from app.domains.modeling.models.market_data import DailyPrice

# Query price data
prices = await db.query(DailyPrice).filter(
    DailyPrice.ticker == "AAPL"
).order_by(DailyPrice.date).all()

# Calculate technical indicators
# Add your feature engineering logic here
```

## API Documentation

Full API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Key endpoints:
- `POST /api/v1/modeling/ingest/{ticker}` - Single ticker ingestion
- `POST /api/v1/modeling/ingest/bulk/sp100` - S&P 100 bulk ingestion
- `GET /api/v1/modeling/ingest/status` - Ingestion status
- `GET /api/v1/modeling/data/coverage` - Data coverage summary
- `GET /api/v1/modeling/symbols` - Available symbols

## Contributing

To extend the modeling domain:

1. Add new data sources in `services/`
2. Extend data models in `models/market_data.py`
3. Add API endpoints in `api/`
4. Update configuration in `config/modeling_config.py`
5. Add management commands in `scripts/`

## License

Part of the AI Capital project. See the main project LICENSE file. 