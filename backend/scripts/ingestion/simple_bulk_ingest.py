#!/usr/bin/env python3
"""
Simple Bulk Ticker Ingestion

Fire-and-forget approach to maximize Tiingo free tier usage.
Sends all requests quickly without waiting for completion.
"""

import requests
import time
import os
from datetime import date

# High-value tickers prioritized for maximum impact
PRIORITY_TICKERS = [
    # FAANG + Major Tech
    "AAPL", "GOOGL", "MSFT", "AMZN", "META", "NFLX", "NVDA", 
    
    # Major ETFs (most important for diversified analysis)
    "SPY", "QQQ", "IWM", "VTI", "VOO", "VEA", "VWO",
    
    # Blue Chip Stocks
    "JNJ", "PG", "KO", "PEP", "WMT", "HD", "UNH", "V", "MA",
    
    # Major Banks
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    
    # Energy & Commodities
    "XOM", "CVX", "GLD", "SLV",
    
    # Growth Stocks
    "ROKU", "PLTR", "SNOW", "COIN", "ZM",
    
    # International
    "BABA", "TSM", "ASML"
]

# Additional tickers if we want more
SECONDARY_TICKERS = [
    "DIS", "ADBE", "CRM", "ORCL", "IBM", "INTC", "AMD", "MU",
    "T", "VZ", "PYPL", "SQ", "UBER", "LYFT", "F", "GM", "NIO",
    "XLF", "XLE", "XLK", "XLV", "XLI", "XLP", "XLU", "XLRE"
]

def fire_ingestion_requests(tickers, delay=2.0):
    """Fire ingestion requests for all tickers with minimal delay."""
    
    print(f"🚀 Firing ingestion requests for {len(tickers)} tickers")
    print(f"⏱️  Delay between requests: {delay} seconds")
    print("=" * 60)
    
    base_url = "http://localhost:8001/api/v1/modeling/duckdb/ingest/single"
    successful = 0
    failed = 0
    
    for i, ticker in enumerate(tickers):
        try:
            print(f"📈 {ticker} ({i+1}/{len(tickers)})... ", end="", flush=True)
            
            response = requests.post(
                f"{base_url}/{ticker}",
                params={
                    "start_date": "2000-01-01",  # Get maximum history
                    "end_date": date.today().isoformat(),
                    "force_refresh": False
                },
                timeout=10  # Quick timeout
            )
            
            if response.status_code == 200:
                print("✅")
                successful += 1
            else:
                print(f"❌ ({response.status_code})")
                failed += 1
                
        except Exception as e:
            print(f"❌ (Error: {str(e)[:30]})")
            failed += 1
        
        # Rate limiting
        if i < len(tickers) - 1:
            time.sleep(delay)
    
    print("\n" + "=" * 60)
    print(f"📊 Requests Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success Rate: {successful/(successful+failed)*100:.1f}%")
    print(f"\n⏳ Background ingestion is now running...")
    print(f"   Check progress: curl http://localhost:8001/api/v1/modeling/duckdb/stats/storage")

def check_progress():
    """Check current ingestion progress."""
    try:
        response = requests.get("http://localhost:8001/api/v1/modeling/duckdb/stats/storage")
        if response.status_code == 200:
            data = response.json()
            stats = data['storage_stats']['daily_prices']
            storage = data['storage_stats']['storage']
            
            print(f"📊 Current Progress:")
            print(f"   📈 Total Records: {stats['total_records']:,}")
            print(f"   🎯 Unique Tickers: {stats['unique_tickers']}")
            print(f"   📅 Date Range: {stats.get('earliest_date', 'N/A')} to {stats.get('latest_date', 'N/A')}")
            print(f"   💾 Storage Size: {storage['total_size_mb']:.2f} MB")
            print(f"   📄 Parquet Files: {storage['parquet_files']}")
        else:
            print(f"❌ Could not get stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking progress: {e}")

def main():
    print("🚀 Simple Bulk Ticker Ingestion")
    print("=" * 60)
    
    # Set API key
    os.environ["TIINGO_API_KEY"] = "d108b9d954ee7b892392fe97b101b67ab1899063"
    
    # Test connection
    try:
        response = requests.get("http://localhost:8001/docs", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding!")
            return
    except:
        print("❌ Cannot connect to server!")
        print("   Start server: cd backend && uvicorn app.main:app --reload --port 8001")
        return
    
    print("✅ Connected to API server")
    
    # Show current stats
    print("\n📊 Current Status:")
    check_progress()
    
    # Choose ticker set
    print(f"\n🎯 Ticker Options:")
    print(f"   1. Priority tickers ({len(PRIORITY_TICKERS)} tickers) - Recommended")
    print(f"   2. Priority + Secondary ({len(PRIORITY_TICKERS + SECONDARY_TICKERS)} tickers)")
    print(f"   3. Custom list")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "2":
        tickers = PRIORITY_TICKERS + SECONDARY_TICKERS
    elif choice == "3":
        ticker_input = input("Enter tickers (comma-separated): ").strip()
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    else:
        tickers = PRIORITY_TICKERS
    
    print(f"\n🎯 Selected {len(tickers)} tickers")
    print(f"   First 10: {', '.join(tickers[:10])}")
    if len(tickers) > 10:
        print(f"   ... and {len(tickers)-10} more")
    
    # Confirm
    confirm = input(f"\nFire {len(tickers)} ingestion requests? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Fire all requests
    fire_ingestion_requests(tickers, delay=1.5)
    
    print(f"\n🎉 All requests fired!")
    print(f"\n📋 What happens next:")
    print(f"   • Background tasks are ingesting data")
    print(f"   • Each ticker gets full historical data (2000-2025)")
    print(f"   • Data is stored in compressed Parquet files")
    print(f"   • Check progress periodically with the stats endpoint")
    
    print(f"\n🔍 Monitor Progress:")
    print(f"   curl http://localhost:8001/api/v1/modeling/duckdb/stats/storage")
    
    print(f"\n⏰ Wait 5-10 minutes then check final results!")

if __name__ == "__main__":
    main() 