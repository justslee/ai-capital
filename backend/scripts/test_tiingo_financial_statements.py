#!/usr/bin/env python3
"""
Test Script for Tiingo Financial Statements Ingestion

Tests the new Tiingo financial statements functionality including:
- Individual ticker ingestion
- Quarterly aggregation
- S3 storage
- API endpoints
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domains.modeling.services.s3_tiingo_financial_statements_ingestion_service import (
    S3TiingoFinancialStatementsIngestionService
)
from app.domains.modeling.services.tiingo_client import TiingoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_tiingo_client_statements():
    """Test the new Tiingo client financial statements methods."""
    logger.info("🧪 Testing Tiingo client financial statements methods...")
    
    async with TiingoClient() as client:
        # Test getting financial statements for Apple 2023
        ticker = "AAPL"
        year = 2023
        
        logger.info(f"Testing financial statements for {ticker} {year}")
        
        # Test basic financial statements endpoint
        statements = await client.get_financial_statements(
            ticker=ticker,
            frequency="quarterly",
            start_date=f"{year}-01-01",
            end_date=f"{year}-12-31"
        )
        
        if statements:
            logger.info(f"✅ Found {len(statements)} total statements for {ticker}")
            
            # Show statement types
            stmt_types = set()
            for stmt in statements:
                stmt_type = stmt.get('statementType', 'unknown')
                stmt_types.add(stmt_type)
            
            logger.info(f"   Statement types found: {sorted(stmt_types)}")
        else:
            logger.warning(f"❌ No statements found for {ticker}")
        
        # Test aggregated quarterly statements
        aggregated = await client.get_quarterly_statements_aggregated(
            ticker=ticker,
            year=year
        )
        
        if aggregated:
            logger.info(f"✅ Aggregated data structure:")
            for stmt_type, quarters in aggregated.items():
                logger.info(f"   {stmt_type}: {len(quarters)} quarters")
        else:
            logger.warning(f"❌ No aggregated data for {ticker} {year}")


async def test_ingestion_service():
    """Test the S3 financial statements ingestion service."""
    logger.info("🧪 Testing S3 financial statements ingestion service...")
    
    async with S3TiingoFinancialStatementsIngestionService() as service:
        # Test single ticker ingestion
        ticker = "AAPL"
        year = 2023
        
        logger.info(f"Testing ingestion for {ticker} {year}")
        
        result = await service.ingest_ticker_quarterly_statements(
            ticker=ticker,
            year=year,
            statement_types=["income"]  # Start with just income statements
        )
        
        if result['success']:
            logger.info(f"✅ Ingestion successful:")
            logger.info(f"   Statement types: {result.get('statement_types_processed', [])}")
            logger.info(f"   Total quarters: {result.get('total_quarters', 0)}")
            logger.info(f"   Files created: {len(result.get('files_created', []))}")
            logger.info(f"   Data completeness: {result.get('data_completeness')}")
        else:
            logger.error(f"❌ Ingestion failed: {result.get('error')}")


async def test_small_bulk_ingestion():
    """Test bulk ingestion with a small set of tickers."""
    logger.info("🧪 Testing small bulk ingestion...")
    
    async with S3TiingoFinancialStatementsIngestionService() as service:
        # Test with a few major tech stocks
        tickers = ["AAPL", "MSFT", "GOOGL"]
        years = [2023]
        
        logger.info(f"Testing bulk ingestion for {tickers} for years {years}")
        
        result = await service.bulk_ingest_quarterly_statements(
            tickers=tickers,
            years=years,
            statement_types=["income"]  # Start with just income statements
        )
        
        summary = result['bulk_ingestion_summary']
        logger.info(f"✅ Bulk ingestion completed:")
        logger.info(f"   Total combinations: {summary['total_combinations_requested']}")
        logger.info(f"   Successful: {summary['successful_ingestions']}")
        logger.info(f"   Failed: {summary['failed_ingestions']}")
        logger.info(f"   Success rate: {summary['success_rate']:.1%}")
        logger.info(f"   Total files created: {summary['total_files_created']}")


async def test_ingestion_status():
    """Test getting ingestion status."""
    logger.info("🧪 Testing ingestion status...")
    
    async with S3TiingoFinancialStatementsIngestionService() as service:
        # Check overall status
        status = await service.get_ingestion_status()
        
        logger.info(f"✅ Ingestion status:")
        logger.info(f"   Files found: {status['files_found']}")
        logger.info(f"   Coverage: {len(status['coverage_summary'])} ticker-year combinations")
        
        # Check specific ticker status
        if status['files_found'] > 0:
            ticker_status = await service.get_ingestion_status(ticker="AAPL")
            logger.info(f"   AAPL specific files: {ticker_status['files_found']}")


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Tiingo Financial Statements Tests")
    
    try:
        # Test 1: Tiingo client methods
        await test_tiingo_client_statements()
        logger.info("─" * 60)
        
        # Test 2: Ingestion service
        await test_ingestion_service()
        logger.info("─" * 60)
        
        # Test 3: Small bulk ingestion
        await test_small_bulk_ingestion()
        logger.info("─" * 60)
        
        # Test 4: Status checking
        await test_ingestion_status()
        logger.info("─" * 60)
        
        logger.info("🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 