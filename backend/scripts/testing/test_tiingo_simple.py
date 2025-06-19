#!/usr/bin/env python3
"""
Simple Tiingo API Test

Test the Tiingo API connection and data fetching.
"""

import asyncio
import sys
import os
from datetime import date, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

async def test_tiingo_api():
    """Test Tiingo API connectivity."""
    
    print("🔗 Testing Tiingo API Connection")
    print("=" * 40)
    
    try:
        from domains.modeling.services.tiingo_client import TiingoClient
        
        # Test with proper async context manager
        async with TiingoClient() as client:
            print("✅ Tiingo client initialized")
            
            # Test connection
            print("\n🔍 Testing connection...")
            connection_ok = await client.test_connection()
            if connection_ok:
                print("✅ Connection successful")
            else:
                print("❌ Connection failed")
                return False
            
            # Test getting metadata
            print("\n📊 Testing metadata fetch...")
            metadata = await client.get_ticker_metadata("AAPL")
            if metadata:
                print(f"✅ Metadata: {metadata.ticker} - {metadata.name}")
            else:
                print("❌ Metadata fetch failed")
            
            # Test getting historical data
            print("\n📈 Testing historical data fetch...")
            start_date = date.today() - timedelta(days=30)
            end_date = date.today() - timedelta(days=1)
            
            print(f"   Fetching AAPL data from {start_date} to {end_date}")
            
            data = await client.get_historical_prices(
                ticker="AAPL",
                start_date=start_date,
                end_date=end_date
            )
            
            if data:
                print(f"✅ Successfully fetched {len(data)} data points")
                if len(data) > 0:
                    latest = data[-1]
                    print(f"   Latest: {latest.date} - Close: ${latest.close}")
                return True
            else:
                print("❌ No data returned")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import os
    
    # Set API key
    os.environ["TIINGO_API_KEY"] = "d108b9d954ee7b892392fe97b101b67ab1899063"
    
    success = asyncio.run(test_tiingo_api())
    
    if success:
        print("\n🎉 Tiingo API test successful!")
    else:
        print("\n❌ Tiingo API test failed!")
        sys.exit(1) 