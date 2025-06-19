# AI Capital

A high-performance financial data platform with zero local storage footprint, perfect for work devices.

## 🌩️ Key Features

- **Zero Local Storage**: All data stored in AWS S3
- **63+ Years of Data**: Historical data back to 1962 for many tickers
- **Lightning Fast**: 10-100x faster than PostgreSQL with DuckDB + S3
- **495,643+ Records**: Comprehensive historical data for 39+ tickers
- **Ultra Efficient**: 43MB storage for half a million records
- **Work-Device Friendly**: Perfect for corporate environments

## 🚀 Quick Start

### 1. Setup S3 Storage (First Time Only)
```bash
cd backend/scripts/setup
python setup_s3_storage.py
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Start the Server
```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

### 4. Ingest Financial Data
```bash
# From project root - convenient runner
python run_s3_ingestion.py

# Or run directly
cd backend/scripts/ingestion
python s3_bulk_ingest.py
```

## 📊 What You Get

- **495,643 total records** across 39 tickers
- **Date range**: 1962-01-02 to present
- **Major companies**: AAPL (1980+), MSFT (1986+), IBM (1962+), KO (1962+)
- **Storage cost**: ~$1/month on AWS S3
- **Query performance**: Sub-second analytics

## 🏗️ Architecture

```
AI Capital
├── backend/
│   ├── app/                    # FastAPI application
│   │   ├── domains/           # Domain-driven design
│   │   │   ├── modeling/      # Financial data modeling
│   │   │   ├── summarization/ # AI summarization
│   │   │   └── valuation/     # Company valuation
│   │   └── main.py           # FastAPI entry point
│   └── scripts/              # Utility scripts
│       ├── ingestion/        # Data ingestion scripts
│       ├── setup/           # Setup and configuration
│       └── testing/         # Testing utilities
└── run_s3_ingestion.py      # Convenience script
```

## 📡 API Endpoints

### S3 DuckDB Storage (Recommended)
- `GET /api/v1/s3-duckdb/health` - Health check
- `POST /api/v1/s3-duckdb/ingest/ticker/{ticker}` - Ingest single ticker
- `GET /api/v1/s3-duckdb/data/{ticker}` - Get historical data
- `GET /api/v1/s3-duckdb/data/{ticker}/latest` - Get latest price
- `GET /api/v1/s3-duckdb/storage/stats` - Storage statistics
- `GET /api/v1/s3-duckdb/analysis/tickers` - Available tickers

### Traditional Storage
- `GET /api/v1/duckdb-storage/*` - Local DuckDB endpoints
- `GET /api/v1/summarization/*` - AI summarization
- `GET /api/v1/valuation/*` - Company valuation

## 💾 Storage Systems

| System | Performance | Storage | Cost | Work Device |
|--------|-------------|---------|------|-------------|
| **S3 + DuckDB** | 🚀 10-100x faster | ☁️ Zero local | 💰 ~$1/month | ✅ Perfect |
| Local DuckDB | 🚀 Very fast | 💽 Local files | 💰 Free | ⚠️ Storage required |
| PostgreSQL | 🐌 Standard | 💽 Local/Remote | 💰 Varies | ⚠️ Setup required |

## 🧪 Testing

```bash
# Test S3 connectivity
cd backend/scripts/testing
python test_tiingo_simple.py

# Test DuckDB system
python test_duckdb_system.py
```

## 📈 Example Usage

```python
import requests

# Get latest Apple price
response = requests.get("http://localhost:8001/api/v1/s3-duckdb/data/AAPL/latest")
latest_price = response.json()

# Get historical data
response = requests.get("http://localhost:8001/api/v1/s3-duckdb/data/AAPL?limit=100")
historical_data = response.json()

# Get storage statistics
response = requests.get("http://localhost:8001/api/v1/s3-duckdb/storage/stats")
stats = response.json()
```

## 🛠️ Requirements

- Python 3.8+
- AWS Account (for S3 storage)
- Tiingo API Key (free tier: 500 requests/hour)

## 🌟 Benefits

### For Work Devices
- **Zero local storage footprint**
- **No corporate firewall issues**
- **Easy to move between machines**
- **Compliant with IT policies**

### For Performance
- **Sub-second queries** on 500K+ records
- **Columnar storage** optimized for analytics
- **Automatic compression** (80-85% reduction)
- **Serverless scaling** with S3

### For Cost
- **$1/month** for complete dataset
- **Free Tiingo tier** (500 req/hour)
- **No infrastructure costs**
- **Pay-as-you-go** S3 pricing

---

**Perfect for quantitative analysis, backtesting, and financial modeling on work devices! 🚀** 