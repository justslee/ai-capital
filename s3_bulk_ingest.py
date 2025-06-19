#!/usr/bin/env python3
"""
S3 Bulk Ticker Ingestion Script

Simple script to ingest multiple tickers into S3 storage.
Perfect for work devices with zero local storage footprint.
"""

import asyncio
import time
from datetime import date, timedelta
from typing import List

# Popular tickers for testing
POPULAR_TICKERS = [
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX",
    
    # Financial
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    
    # Healthcare
    "JNJ", "PFE", "UNH", "ABBV", "MRK",
    
    # Consumer
    "KO", "PEP", "WMT", "HD", "MCD", "NKE",
    
    # Industrial
    "BA", "CAT", "GE", "MMM", "HON",
    
    # Energy
    "XOM", "CVX", "COP", "SLB",
    
    # Utilities
    "NEE", "DUK", "SO", "AEP"
]


async def ingest_tickers_to_s3(
    tickers: List[str],
    max_concurrent: int = 3,
    rate_limit_seconds: float = 1.5
):
    """
    Ingest multiple tickers to S3 with rate limiting.
    
    Args:
        tickers: List of ticker symbols
        max_concurrent: Maximum concurrent requests
        rate_limit_seconds: Delay between requests
    """
    import aiohttp
    import json
    
    base_url = "http://localhost:8001/api/v1/s3-duckdb"
    
    print(f"🚀 Starting S3 bulk ingestion for {len(tickers)} tickers")
    print(f"📊 Max concurrent: {max_concurrent}")
    print(f"⏱️  Rate limit: {rate_limit_seconds}s between requests")
    print("=" * 60)
    
    # Calculate date range (ALL available historical data)
    end_date = date.today()
    start_date = None  # Get all available data from Tiingo
    
    successful = 0
    failed = 0
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def ingest_single_ticker(ticker: str):
            nonlocal successful, failed
            
            async with semaphore:
                try:
                    print(f"📈 Ingesting {ticker}...")
                    
                    # Make API request
                    url = f"{base_url}/ingest/ticker/{ticker}"
                    params = {
                        "end_date": end_date.isoformat()
                    }
                    # Don't include start_date to get ALL available data
                    
                    async with session.post(url, params=params) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("status") == "success":
                                records = result.get("records_stored", 0)
                                print(f"✅ {ticker}: {records} records stored in S3")
                                successful += 1
                            else:
                                print(f"⚠️  {ticker}: {result.get('message', 'No data')}")
                                successful += 1  # Count as successful even if no data
                        else:
                            error_text = await response.text()
                            print(f"❌ {ticker}: HTTP {response.status} - {error_text}")
                            failed += 1
                    
                    # Rate limiting
                    await asyncio.sleep(rate_limit_seconds)
                    
                except Exception as e:
                    print(f"❌ {ticker}: Error - {str(e)}")
                    failed += 1
        
        # Execute all ingestions
        tasks = [ingest_single_ticker(ticker) for ticker in tickers]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    print("=" * 60)
    print(f"🎉 S3 Bulk Ingestion Complete!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(tickers)}")
    
    if successful > 0:
        print(f"\n🌩️  Data stored in S3 bucket: ai-capital-data")
        print(f"📁 S3 prefix: market-data")
        print(f"💾 Local storage used: ~0 MB (cache only)")


async def check_s3_health():
    """Check if S3 service is healthy."""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8001/api/v1/s3-duckdb/health") as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("status") == "healthy":
                        print("✅ S3 DuckDB service is healthy")
                        return True
                    else:
                        print(f"❌ S3 service unhealthy: {result.get('error')}")
                        return False
                else:
                    print(f"❌ S3 health check failed: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to S3 service: {e}")
        print("💡 Make sure the server is running: cd backend && uvicorn app.main:app --reload --port 8001")
        return False


async def main():
    """Main function."""
    print("🌩️  AI Capital S3 Bulk Ingestion")
    print("=" * 60)
    
    # Health check
    if not await check_s3_health():
        return
    
    print(f"\n📋 Will ingest {len(POPULAR_TICKERS)} popular tickers with ALL available historical data:")
    print(", ".join(POPULAR_TICKERS))
    print(f"\n💡 This will fetch ALL available data (some tickers go back to 1962!)")
    print(f"📊 Expected: 10,000-17,000+ records per ticker vs previous 1,256")
    print(f"🔄 Files will be replaced with fresh data (ticker names in filenames)")
    print(f"📁 New format: daily_prices_TICKER_YEAR.parquet")
    
    # Confirm
    response = input(f"\n🤔 Proceed with FULL historical S3 ingestion? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Cancelled")
        return
    
    # Start ingestion
    start_time = time.time()
    await ingest_tickers_to_s3(POPULAR_TICKERS)
    end_time = time.time()
    
    print(f"\n⏱️  Total time: {end_time - start_time:.1f} seconds")
    print(f"🌩️  All data stored in AWS S3 - zero local storage used!")


if __name__ == "__main__":
    asyncio.run(main()) 