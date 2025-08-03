#!/usr/bin/env python3
"""
Data Ingestion Management Script

Command-line script for managing historical data ingestion for the modeling domain.
Supports ingesting S&P 100, custom ticker lists, and individual tickers.
"""

import asyncio
import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from typing import List, Optional
import os

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from app.domains.modeling.data_ingestion.price_data_ingestion import price_data_ingestion_service
from app.domains.modeling.config.modeling_config import get_sp100_symbols, get_all_target_symbols, get_index_symbols
from app.domains.data_collection.config.ticker_config import (
    get_dow_tickers, get_sp500_tickers, get_nasdaq_tickers, get_russell2000_tickers, get_top_etfs
)
from app.db.session import AsyncSessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_single_ticker(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: str = "tiingo"
):
    """Ingest data for a single ticker."""
    async with AsyncSessionLocal() as db:
        logger.info(f"Starting ingestion for {ticker}")
        
        result = await price_data_ingestion_service.ingest_historical_prices(
            ticker=ticker.upper(),
            start_date=start_date,
            end_date=end_date,
            source=source,
            db=db
        )
        
        if "error" in result:
            logger.error(f"Failed to ingest {ticker}: {result['error']}")
            return False
        else:
            logger.info(f"Successfully ingested {ticker}: {result.get('records_inserted', 0)} records")
            return True


async def ingest_sp100(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_concurrent: int = 5
):
    """Ingest data for S&P 100 companies."""
    async with AsyncSessionLocal() as db:
        logger.info("Starting S&P 100 bulk ingestion")
        
        result = await price_data_ingestion_service.bulk_ingest_sp100(
            start_date=start_date,
            end_date=end_date,
            max_concurrent=max_concurrent,
            db=db
        )
        
        logger.info(f"S&P 100 ingestion completed: {result['successful']}/{result['total_tickers']} successful")
        
        if result['errors']:
            logger.warning(f"Errors encountered: {len(result['errors'])}")
            for error in result['errors'][:10]:  # Show first 10 errors
                logger.warning(f"  {error}")
        
        return result


async def ingest_all_targets(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_concurrent: int = 5
):
    """Ingest data for all target symbols."""
    async with AsyncSessionLocal() as db:
        logger.info("Starting bulk ingestion for all target symbols")
        
        result = await price_data_ingestion_service.bulk_ingest_all_targets(
            start_date=start_date,
            end_date=end_date,
            max_concurrent=max_concurrent,
            db=db
        )
        
        logger.info(f"Bulk ingestion completed: {result['successful']}/{result['total_tickers']} successful")
        logger.info(f"Total records ingested: {result['total_records']}")
        
        if result['errors']:
            logger.warning(f"Errors encountered: {len(result['errors'])}")
            for error in result['errors'][:10]:  # Show first 10 errors
                logger.warning(f"  {error}")
        
        return result


async def ingest_custom_tickers(
    tickers: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_concurrent: int = 5
):
    """Ingest data for custom list of tickers."""
    async with AsyncSessionLocal() as db:
        logger.info(f"Starting custom bulk ingestion for {len(tickers)} tickers")
        
        result = await price_data_ingestion_service.bulk_ingest_tickers(
            tickers=[ticker.upper() for ticker in tickers],
            start_date=start_date,
            end_date=end_date,
            max_concurrent=max_concurrent,
            db=db
        )
        
        logger.info(f"Custom ingestion completed: {result['successful']}/{result['total_tickers']} successful")
        
        if result['errors']:
            logger.warning(f"Errors encountered: {len(result['errors'])}")
            for error in result['errors'][:10]:  # Show first 10 errors
                logger.warning(f"  {error}")
        
        return result


async def show_data_coverage(tickers: Optional[List[str]] = None):
    """Show data coverage for tickers."""
    async with AsyncSessionLocal() as db:
        logger.info("Checking data coverage...")
        
        coverage = await price_data_ingestion_service.get_data_coverage(
            tickers=tickers,
            db=db
        )
        
        print("\nData Coverage Summary:")
        print("-" * 80)
        print(f"{'Ticker':<10} {'Records':<10} {'Earliest':<12} {'Latest':<12} {'Source':<10}")
        print("-" * 80)
        
        for ticker, info in coverage.items():
            records = info['record_count']
            earliest = info['earliest_date'] or 'N/A'
            latest = info['latest_date'] or 'N/A'
            source = info['data_source'] or 'N/A'
            
            print(f"{ticker:<10} {records:<10} {earliest:<12} {latest:<12} {source:<10}")
        
        # Summary statistics
        total_records = sum(info['record_count'] for info in coverage.values())
        tickers_with_data = sum(1 for info in coverage.values() if info['record_count'] > 0)
        
        print("-" * 80)
        print(f"Total tickers: {len(coverage)}")
        print(f"Tickers with data: {tickers_with_data}")
        print(f"Total records: {total_records:,}")


async def show_ingestion_status():
    """Show recent ingestion activity."""
    async with AsyncSessionLocal() as db:
        logger.info("Checking ingestion status...")
        
        logs = await price_data_ingestion_service.get_ingestion_status(db=db)
        
        print("\nRecent Ingestion Activity:")
        print("-" * 120)
        print(f"{'Ticker':<10} {'Status':<12} {'Records':<10} {'Started':<20} {'Completed':<20} {'Error':<30}")
        print("-" * 120)
        
        for log in logs[:20]:  # Show last 20 entries
            ticker = log['ticker'] or 'N/A'
            status = log['status']
            records = log['records_inserted'] or 0
            started = log['started_at'][:19] if log['started_at'] else 'N/A'
            completed = log['completed_at'][:19] if log['completed_at'] else 'N/A'
            error = (log['error_message'] or '')[:28]
            
            print(f"{ticker:<10} {status:<12} {records:<10} {started:<20} {completed:<20} {error:<30}")


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser(description="AI Capital Data Ingestion Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Single ticker ingestion
    single_parser = subparsers.add_parser('single', help='Ingest data for a single ticker')
    single_parser.add_argument('ticker', help='Stock ticker symbol')
    single_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    single_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    single_parser.add_argument('--source', default='tiingo', help='Data source (default: tiingo)')
    
    # S&P 100 ingestion
    sp100_parser = subparsers.add_parser('sp100', help='Ingest data for S&P 100 companies')
    sp100_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    sp100_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    sp100_parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent requests')
    
    # All targets ingestion
    all_parser = subparsers.add_parser('all', help='Ingest data for all target symbols')
    all_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    all_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    all_parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent requests')
    
    # Custom tickers ingestion
    custom_parser = subparsers.add_parser('custom', help='Ingest data for custom ticker list')
    custom_parser.add_argument('tickers', nargs='+', help='List of ticker symbols')
    custom_parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)')
    custom_parser.add_argument('--end-date', help='End date (YYYY-MM-DD)')
    custom_parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent requests')
    
    # Status and monitoring commands
    subparsers.add_parser('status', help='Show recent ingestion activity')
    
    coverage_parser = subparsers.add_parser('coverage', help='Show data coverage')
    coverage_parser.add_argument('--tickers', nargs='*', help='Specific tickers to check')
    
    # Utility commands
    symbols_parser = subparsers.add_parser('symbols', help='List available symbol groups')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute the appropriate command
    if args.command == 'single':
        asyncio.run(ingest_single_ticker(
            ticker=args.ticker,
            start_date=args.start_date,
            end_date=args.end_date,
            source=args.source
        ))
    
    elif args.command == 'sp100':
        asyncio.run(ingest_sp100(
            start_date=args.start_date,
            end_date=args.end_date,
            max_concurrent=args.max_concurrent
        ))
    
    elif args.command == 'all':
        asyncio.run(ingest_all_targets(
            start_date=args.start_date,
            end_date=args.end_date,
            max_concurrent=args.max_concurrent
        ))
    
    elif args.command == 'custom':
        asyncio.run(ingest_custom_tickers(
            tickers=args.tickers,
            start_date=args.start_date,
            end_date=args.end_date,
            max_concurrent=args.max_concurrent
        ))
    
    elif args.command == 'status':
        asyncio.run(show_ingestion_status())
    
    elif args.command == 'coverage':
        asyncio.run(show_data_coverage(tickers=args.tickers))
    
    elif args.command == 'symbols':
        print("Available Symbol Groups (Centralized Ticker Config):")
        print(f"DOW: {len(get_dow_tickers())} symbols")
        print(f"S&P 500: {len(get_sp500_tickers())} symbols") 
        print(f"NASDAQ 100: {len(get_nasdaq_tickers())} symbols")
        print(f"Russell 2000: {len(get_russell2000_tickers())} symbols")
        print(f"Top ETFs: {len(get_top_etfs())} symbols")
        
        print(f"\nFirst 10 DOW symbols: {', '.join(get_dow_tickers()[:10])}")
        print(f"First 10 S&P 500 symbols: {', '.join(get_sp500_tickers()[:10])}")
        
        # Legacy symbol groups (still available)
        print(f"\nLegacy Groups:")
        print(f"S&P 100: {len(get_sp100_symbols())} symbols")
        print(f"Major Indexes: {len(get_index_symbols())} symbols")
        print(f"All Targets: {len(get_all_target_symbols())} symbols")


if __name__ == "__main__":
    main() 