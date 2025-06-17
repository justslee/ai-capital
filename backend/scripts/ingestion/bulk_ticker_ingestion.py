#!/usr/bin/env python3
"""
Bulk Ticker Ingestion Script

Maximize Tiingo free tier usage by downloading historical data for multiple high-value tickers.
Includes rate limiting, error handling, and progress tracking.
"""

import asyncio
import requests
import json
import time
import sys
import os
from datetime import date, datetime
from typing import List, Dict

# High-value tickers to prioritize (major stocks, ETFs, crypto)
PRIORITY_TICKERS = [
    # FAANG + Major Tech
    "AAPL", "GOOGL", "MSFT", "AMZN", "META", "NFLX", "NVDA", "TSLA",
    
    # Major Banks & Finance
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    
    # Major ETFs
    "SPY", "QQQ", "IWM", "VTI", "VOO", "VEA", "VWO",
    
    # Blue Chip Industrials
    "JNJ", "PG", "KO", "PEP", "WMT", "HD", "UNH", "V", "MA",
    
    # Energy & Commodities
    "XOM", "CVX", "COP", "SLB", "GLD", "SLV",
    
    # Emerging Growth
    "ROKU", "PLTR", "SNOW", "COIN", "RBLX", "ZM", "SHOP",
    
    # Crypto-related
    "MSTR", "RIOT", "MARA",
    
    # REITs
    "VNQ", "O", "REIT",
    
    # International
    "BABA", "TSM", "ASML", "NVO"
]

# Additional tickers if we have capacity
SECONDARY_TICKERS = [
    "DIS", "ADBE", "CRM", "ORCL", "IBM", "INTC", "AMD", "MU",
    "T", "VZ", "CMCSA", "NFLX", "PYPL", "SQ", "UBER", "LYFT",
    "F", "GM", "NIO", "LCID", "RIVN", "BYND", "MRNA", "PFE",
    "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLU", "XLRE"
]

class BulkIngestionManager:
    def __init__(self, base_url: str = "http://localhost:8001/api/v1"):
        self.base_url = base_url
        self.successful_ingestions = []
        self.failed_ingestions = []
        self.rate_limit_delay = 1.0  # Start with 1 second between requests
        self.max_retries = 3
        
    def test_connection(self) -> bool:
        """Test if the API server is running."""
        try:
            response = requests.get(f"http://localhost:8001/docs", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_current_stats(self) -> Dict:
        """Get current storage statistics."""
        try:
            response = requests.get(f"{self.base_url}/modeling/duckdb/stats/storage")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}
    
    def ingest_ticker(self, ticker: str, start_date: str = "2000-01-01") -> Dict:
        """Ingest historical data for a single ticker."""
        print(f"🔄 Ingesting {ticker}...")
        
        try:
            # Make the ingestion request
            response = requests.post(
                f"{self.base_url}/modeling/duckdb/ingest/single/{ticker}",
                params={
                    "start_date": start_date,
                    "end_date": date.today().isoformat(),
                    "force_refresh": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ {ticker}: {result.get('status', 'success')}")
                return {"ticker": ticker, "status": "success", "response": result}
            else:
                print(f"❌ {ticker}: HTTP {response.status_code}")
                return {"ticker": ticker, "status": "failed", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ {ticker}: {str(e)}")
            return {"ticker": ticker, "status": "failed", "error": str(e)}
    
    def wait_for_completion(self, ticker: str, max_wait: int = 30) -> bool:
        """Wait for background ingestion to complete."""
        print(f"⏳ Waiting for {ticker} ingestion to complete...")
        
        for i in range(max_wait):
            try:
                # Check if we can query the ticker (indicates completion)
                response = requests.get(f"{self.base_url}/modeling/duckdb/query/prices/{ticker}?limit=1")
                if response.status_code == 200:
                    data = response.json()
                    if data.get('record_count', 0) > 0:
                        print(f"✅ {ticker} ingestion completed")
                        return True
            except:
                pass
            
            time.sleep(2)  # Wait 2 seconds between checks
        
        print(f"⚠️  {ticker} ingestion timeout")
        return False
    
    def bulk_ingest(self, tickers: List[str], batch_size: int = 5) -> Dict:
        """Perform bulk ingestion with rate limiting and error handling."""
        
        print(f"🚀 Starting bulk ingestion of {len(tickers)} tickers")
        print(f"📊 Batch size: {batch_size}, Rate limit: {self.rate_limit_delay}s")
        print("=" * 60)
        
        # Get initial stats
        initial_stats = self.get_current_stats()
        initial_records = initial_stats.get('storage_stats', {}).get('daily_prices', {}).get('total_records', 0)
        
        start_time = time.time()
        
        for i, ticker in enumerate(tickers):
            print(f"\n📈 Processing {ticker} ({i+1}/{len(tickers)})")
            
            # Ingest the ticker
            result = self.ingest_ticker(ticker)
            
            if result['status'] == 'success':
                self.successful_ingestions.append(result)
                # Wait for completion before proceeding
                self.wait_for_completion(ticker, max_wait=20)
            else:
                self.failed_ingestions.append(result)
            
            # Rate limiting
            if i < len(tickers) - 1:  # Don't wait after the last ticker
                print(f"⏸️  Rate limiting: waiting {self.rate_limit_delay}s...")
                time.sleep(self.rate_limit_delay)
            
            # Show progress every 5 tickers
            if (i + 1) % 5 == 0:
                self.show_progress_summary()
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        final_stats = self.get_current_stats()
        final_records = final_stats.get('storage_stats', {}).get('daily_prices', {}).get('total_records', 0)
        
        summary = {
            "total_tickers": len(tickers),
            "successful": len(self.successful_ingestions),
            "failed": len(self.failed_ingestions),
            "duration_minutes": duration / 60,
            "records_added": final_records - initial_records,
            "initial_records": initial_records,
            "final_records": final_records
        }
        
        self.show_final_summary(summary)
        return summary
    
    def show_progress_summary(self):
        """Show current progress summary."""
        total_processed = len(self.successful_ingestions) + len(self.failed_ingestions)
        success_rate = len(self.successful_ingestions) / total_processed * 100 if total_processed > 0 else 0
        
        print(f"\n📊 Progress Summary:")
        print(f"   ✅ Successful: {len(self.successful_ingestions)}")
        print(f"   ❌ Failed: {len(self.failed_ingestions)}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        
        # Show current storage stats
        current_stats = self.get_current_stats()
        if current_stats:
            daily_stats = current_stats.get('storage_stats', {}).get('daily_prices', {})
            storage_stats = current_stats.get('storage_stats', {}).get('storage', {})
            print(f"   📊 Total Records: {daily_stats.get('total_records', 0):,}")
            print(f"   🎯 Unique Tickers: {daily_stats.get('unique_tickers', 0)}")
            print(f"   💾 Storage Size: {storage_stats.get('total_size_mb', 0):.2f} MB")
    
    def show_final_summary(self, summary: Dict):
        """Show final ingestion summary."""
        print("\n" + "=" * 60)
        print("🎉 BULK INGESTION COMPLETE!")
        print("=" * 60)
        
        print(f"📊 Final Results:")
        print(f"   🎯 Total Tickers Processed: {summary['total_tickers']}")
        print(f"   ✅ Successful Ingestions: {summary['successful']}")
        print(f"   ❌ Failed Ingestions: {summary['failed']}")
        print(f"   📈 Success Rate: {summary['successful']/summary['total_tickers']*100:.1f}%")
        print(f"   ⏱️  Total Duration: {summary['duration_minutes']:.1f} minutes")
        print(f"   📊 Records Added: {summary['records_added']:,}")
        print(f"   💾 Total Records: {summary['final_records']:,}")
        
        if self.failed_ingestions:
            print(f"\n❌ Failed Tickers:")
            for failure in self.failed_ingestions:
                print(f"   • {failure['ticker']}: {failure.get('error', 'Unknown error')}")
        
        print(f"\n🚀 Next Steps:")
        print(f"   • Query data: GET /api/v1/modeling/duckdb/query/prices/{{ticker}}")
        print(f"   • Storage stats: GET /api/v1/modeling/duckdb/stats/storage")
        print(f"   • ML features: GET /api/v1/modeling/duckdb/query/ml-features/{{ticker}}")

def main():
    print("🚀 Tiingo Free Tier Maximizer")
    print("=" * 60)
    
    # Set API key
    os.environ["TIINGO_API_KEY"] = "d108b9d954ee7b892392fe97b101b67ab1899063"
    
    manager = BulkIngestionManager()
    
    # Test connection
    if not manager.test_connection():
        print("❌ Cannot connect to API server!")
        print("   Make sure the server is running: uvicorn app.main:app --reload --port 8001")
        sys.exit(1)
    
    print("✅ Connected to API server")
    
    # Show current stats
    current_stats = manager.get_current_stats()
    if current_stats:
        daily_stats = current_stats.get('storage_stats', {}).get('daily_prices', {})
        print(f"📊 Current Storage: {daily_stats.get('total_records', 0):,} records, {daily_stats.get('unique_tickers', 0)} tickers")
    
    # Ask user for strategy
    print(f"\n🎯 Ingestion Strategy Options:")
    print(f"   1. Priority tickers only ({len(PRIORITY_TICKERS)} tickers)")
    print(f"   2. Priority + Secondary ({len(PRIORITY_TICKERS + SECONDARY_TICKERS)} tickers)")
    print(f"   3. Custom ticker list")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        tickers = PRIORITY_TICKERS
    elif choice == "2":
        tickers = PRIORITY_TICKERS + SECONDARY_TICKERS
    elif choice == "3":
        ticker_input = input("Enter tickers (comma-separated): ").strip()
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    else:
        print("Invalid choice, using priority tickers")
        tickers = PRIORITY_TICKERS
    
    print(f"\n🎯 Will ingest {len(tickers)} tickers: {', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}")
    
    # Confirm before starting
    confirm = input("\nProceed with bulk ingestion? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Start bulk ingestion
    summary = manager.bulk_ingest(tickers, batch_size=5)
    
    print(f"\n✅ Bulk ingestion completed!")
    print(f"   Check your data at: http://localhost:8001/docs")

if __name__ == "__main__":
    main() 