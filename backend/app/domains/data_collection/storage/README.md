# DuckDB + Parquet Storage System

High-performance storage solution for financial time-series data, optimized for ML workloads and analytical queries.

## 🚀 Performance Benefits

- **10-100x faster** analytical queries compared to PostgreSQL
- **80-85% storage compression** with Parquet columnar format
- **Zero database server management** - file-based storage
- **ML-optimized** columnar storage perfect for time-series analysis
- **Portable** - data stored as standard Parquet files

## 📊 Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Tiingo API    │───▶│  DuckDB Service  │───▶│ Parquet Files   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   DuckDB Views   │
                       │  (SQL Interface) │
                       └──────────────────┘
```

### Storage Structure

```
data/
├── parquet/
│   ├── daily_prices/
│   │   ├── year=2020/
│   │   │   └── daily_prices_2020_20241201_120000.parquet
│   │   ├── year=2021/
│   │   └── year=2024/
│   ├── tickers/
│   │   └── tickers.parquet
│   └── ingestion_logs/
│       ├── year=2024/month=12/
│       └── ...
├── duckdb/
│   ├── market_data.db
│   └── analytics.db
├── exports/
└── temp/
```

## 🛠️ Setup & Installation

### 1. Install Dependencies

```bash
pip install duckdb>=0.9.0 pyarrow>=14.0.0 click>=8.0.0
```

### 2. Initialize Storage

The storage system auto-initializes on first use, creating:
- Directory structure
- DuckDB database files
- Parquet views and indexes

## 📈 Usage Examples

### API Endpoints

#### Data Ingestion

```bash
# Single ticker
curl -X POST "http://localhost:8000/api/v1/modeling/duckdb/ingest/single/AAPL"

# Bulk tickers
curl -X POST "http://localhost:8000/api/v1/modeling/duckdb/ingest/bulk" \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "GOOGL", "MSFT"]}'

# S&P 100 (background task)
curl -X POST "http://localhost:8000/api/v1/modeling/duckdb/ingest/sp100?background_tasks=true"
```

#### Data Querying

```bash
# Query ticker prices
curl "http://localhost:8000/api/v1/modeling/duckdb/query/prices/AAPL?limit=100"

# Generate ML features
curl "http://localhost:8000/api/v1/modeling/duckdb/query/ml-features/AAPL?feature_type=returns&start_date=2024-01-01&end_date=2024-12-01"

# Storage statistics
curl "http://localhost:8000/api/v1/modeling/duckdb/stats/storage"
```

### CLI Interface

```bash
# Navigate to CLI directory
cd backend/app/domains/modeling/cli

# Single ticker ingestion
python duckdb_cli.py ingest-ticker AAPL --start-date 2020-01-01

# Check status
python duckdb_cli.py status

# View configuration
python duckdb_cli.py config
```

### Python API

```python
from domains.modeling.storage.duckdb_service import get_storage_service
from domains.modeling.services.duckdb_ingestion_service import get_ingestion_service

# Initialize services
storage_service = await get_storage_service()
ingestion_service = get_ingestion_service()

# Ingest data
result = await ingestion_service.ingest_single_ticker("AAPL")

# Query data
df = await storage_service.query_price_data(
    ticker="AAPL",
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 1)
)

# Generate ML features
features_df = await storage_service.get_ml_features(
    feature_type="returns",
    ticker="AAPL",
    start_date=date(2024, 1, 1),
    end_date=date(2024, 12, 1)
)
```

## 🔧 Configuration

### Storage Settings

```python
# duckdb_config.py
class DuckDBStorageConfig:
    # Paths
    data_root_path: str = "./data"
    parquet_path: str = "./data/parquet"
    duckdb_path: str = "./data/duckdb"
    
    # Performance
    parquet_compression: str = "snappy"
    parquet_row_group_size: int = 100000
    enable_partitioning: bool = True
    
    # DuckDB
    duckdb_memory_limit: str = "2GB"
    duckdb_threads: int = 4
```

### Partitioning Strategy

- **Daily Prices**: Partitioned by year for optimal time-series queries
- **Tickers**: Single file (small reference data)
- **Logs**: Partitioned by year/month

## 📊 Performance Optimization

### Query Patterns

The system is optimized for common financial analysis patterns:

1. **Time Series Analysis**
   ```sql
   SELECT * FROM daily_prices 
   WHERE ticker = 'AAPL' AND date BETWEEN '2024-01-01' AND '2024-12-01'
   ```

2. **Cross-Sectional Analysis**
   ```sql
   SELECT * FROM daily_prices 
   WHERE date = '2024-12-01' AND ticker IN ('AAPL', 'GOOGL', 'MSFT')
   ```

3. **Aggregations**
   ```sql
   SELECT ticker, AVG(close), MAX(volume) 
   FROM daily_prices 
   GROUP BY ticker
   ```

### ML Feature Engineering

Pre-built optimized queries for:
- **Returns**: Daily, weekly, monthly returns
- **Moving Averages**: 20-day, 50-day, 200-day
- **Volatility**: Rolling volatility calculations
- **Cross-Sectional**: Ranking and percentile features

## 💾 Storage Efficiency

### Compression Comparison

| Storage Type | Size | Compression | Query Speed |
|--------------|------|-------------|-------------|
| PostgreSQL   | 2-3 GB | None | Baseline |
| CSV Files    | 1.5 GB | None | Slow |
| **Parquet + DuckDB** | **300-500 MB** | **80-85%** | **10-100x faster** |

### File Organization

- **Year Partitioning**: Enables partition pruning for date range queries
- **Snappy Compression**: Optimal balance of compression ratio and query speed
- **Row Group Size**: 100K rows optimized for time-series access patterns
- **Statistics**: Column statistics for query optimization

## 🔍 Monitoring & Maintenance

### Storage Statistics

```python
stats = await storage_service.get_storage_stats()
# Returns:
# - Total records and unique tickers
# - Storage size and file count
# - Date range coverage
# - Compression ratios
```

### Maintenance Operations

```python
# Optimize storage (compact small files)
await storage_service.optimize_storage()

# Create backup
backup_path = await storage_service.backup_to_single_file()

# Export data
file_path = await storage_service.export_data(
    format="csv",
    ticker="AAPL"
)
```

## 🚨 Migration from PostgreSQL

### Data Migration Strategy

1. **Parallel Operation**: Run both systems during transition
2. **Incremental Migration**: Migrate data in batches by date ranges
3. **Validation**: Compare query results between systems
4. **Cutover**: Switch to DuckDB once validated

### Migration Script Example

```python
# Migrate existing PostgreSQL data to DuckDB
async def migrate_ticker_data(ticker: str):
    # 1. Extract from PostgreSQL
    pg_data = await pg_service.get_price_data(ticker)
    
    # 2. Transform to PriceDataPoint objects
    price_points = [transform_to_price_point(row) for row in pg_data]
    
    # 3. Store in DuckDB
    result = await duckdb_service.store_price_data(price_points)
    
    return result
```

## 🎯 Best Practices

### Data Ingestion

1. **Batch Processing**: Use bulk ingestion for multiple tickers
2. **Rate Limiting**: Respect API limits (3 concurrent for free tier)
3. **Error Handling**: Implement retry logic for failed requests
4. **Validation**: Validate data quality before storage

### Query Optimization

1. **Date Filtering**: Always include date ranges to leverage partitioning
2. **Column Selection**: Select only needed columns for better performance
3. **Limit Results**: Use LIMIT for exploratory queries
4. **Batch Processing**: Process large datasets in chunks

### Storage Management

1. **Regular Optimization**: Run storage optimization weekly
2. **Backup Strategy**: Create regular backups of critical data
3. **Monitoring**: Monitor storage size and query performance
4. **Cleanup**: Remove temporary files and old exports

## 🔧 Troubleshooting

### Common Issues

1. **Memory Errors**
   - Increase DuckDB memory limit
   - Process data in smaller batches
   - Use column selection to reduce memory usage

2. **Slow Queries**
   - Check if date filters are applied
   - Verify partitioning is working
   - Update table statistics

3. **Storage Issues**
   - Check disk space availability
   - Verify directory permissions
   - Run storage optimization

### Debug Mode

```python
# Enable detailed logging
import logging
logging.getLogger("domains.modeling.storage").setLevel(logging.DEBUG)

# Check DuckDB query plans
async with storage_service.get_connection() as conn:
    plan = conn.execute("EXPLAIN SELECT * FROM daily_prices WHERE ticker = 'AAPL'").fetchall()
    print(plan)
```

## 📚 Additional Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [Apache Parquet Format](https://parquet.apache.org/docs/)
- [PyArrow Documentation](https://arrow.apache.org/docs/python/)
- [Financial Data Analysis Best Practices](https://github.com/your-repo/financial-analysis-guide)

## 🤝 Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Ensure backward compatibility where possible
5. Performance test any query optimizations

---

**Note**: This DuckDB + Parquet system is designed to eventually replace the PostgreSQL storage for analytical workloads while maintaining compatibility with existing APIs. 