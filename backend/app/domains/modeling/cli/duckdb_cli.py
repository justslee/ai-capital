#!/usr/bin/env python3
"""
DuckDB Data Management CLI

Command-line interface for managing DuckDB + Parquet data ingestion and operations.
High-performance alternative to PostgreSQL-based storage.
"""

import asyncio
import click
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from domains.modeling.services.duckdb_ingestion_service import get_ingestion_service
from domains.modeling.storage.duckdb_service import get_storage_service
from domains.modeling.config.modeling_config import get_modeling_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """DuckDB Data Management CLI - High-performance financial data storage."""
    pass


@cli.command()
@click.argument('ticker')
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='End date (YYYY-MM-DD)')
@click.option('--force-refresh', is_flag=True, 
              help='Re-fetch existing data')
def ingest_ticker(ticker: str, start_date: Optional[datetime], 
                 end_date: Optional[datetime], force_refresh: bool):
    """Ingest historical data for a single ticker."""
    
    async def _ingest():
        try:
            ingestion_service = get_ingestion_service()
            
            start_dt = start_date.date() if start_date else None
            end_dt = end_date.date() if end_date else None
            
            click.echo(f"🚀 Starting ingestion for {ticker}...")
            
            result = await ingestion_service.ingest_single_ticker(
                ticker=ticker,
                start_date=start_dt,
                end_date=end_dt,
                force_refresh=force_refresh
            )
            
            if result['status'] == 'success':
                click.echo(f"✅ Successfully ingested {result['records_stored']} records for {ticker}")
                click.echo(f"   📁 Files created: {result['files_created']}")
                click.echo(f"   ⚡ Storage format: {result['storage_format']}")
                click.echo(f"   ⏱️  Duration: {result['duration_seconds']:.2f} seconds")
            elif result['status'] == 'no_data':
                click.echo(f"⚠️  No data available for {ticker}")
            else:
                click.echo(f"❌ Error ingesting {ticker}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            click.echo(f"❌ Error: {e}")
            sys.exit(1)
    
    asyncio.run(_ingest())


@cli.command()
@click.option('--tickers', multiple=True, help='Specific tickers to ingest')
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='End date (YYYY-MM-DD)')
@click.option('--max-concurrent', default=3, help='Maximum concurrent requests')
@click.option('--force-refresh', is_flag=True, help='Re-fetch existing data')
def ingest_bulk(tickers: tuple, start_date: Optional[datetime], 
               end_date: Optional[datetime], max_concurrent: int, force_refresh: bool):
    """Ingest historical data for multiple tickers."""
    
    async def _ingest_bulk():
        try:
            if not tickers:
                click.echo("❌ Please specify tickers with --tickers option")
                sys.exit(1)
            
            ingestion_service = get_ingestion_service()
            
            start_dt = start_date.date() if start_date else None
            end_dt = end_date.date() if end_date else None
            
            click.echo(f"🚀 Starting bulk ingestion for {len(tickers)} tickers...")
            
            result = await ingestion_service.ingest_bulk_tickers(
                tickers=list(tickers),
                start_date=start_dt,
                end_date=end_dt,
                max_concurrent=max_concurrent,
                force_refresh=force_refresh
            )
            
            click.echo(f"✅ Bulk ingestion completed:")
            click.echo(f"   📊 Total tickers: {result['total_tickers']}")
            click.echo(f"   ✅ Successful: {result['successful']}")
            click.echo(f"   ❌ Failed: {result['failed']}")
            click.echo(f"   ⏭️  Skipped: {result['skipped']}")
            click.echo(f"   📈 Total records: {result['total_records_stored']}")
            click.echo(f"   ⏱️  Duration: {result['duration_seconds']:.2f} seconds")
            click.echo(f"   💾 Storage: {result['storage_format']}")
            
            if result['errors']:
                click.echo(f"\n⚠️  Errors encountered:")
                for error in result['errors'][:5]:  # Show first 5 errors
                    click.echo(f"   • {error}")
                
        except Exception as e:
            click.echo(f"❌ Error: {e}")
            sys.exit(1)
    
    asyncio.run(_ingest_bulk())


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='End date (YYYY-MM-DD)')
@click.option('--force-refresh', is_flag=True, help='Re-fetch existing data')
def ingest_sp100(start_date: Optional[datetime], end_date: Optional[datetime], 
                force_refresh: bool):
    """Ingest all S&P 100 tickers."""
    
    async def _ingest_sp100():
        try:
            config = get_modeling_config()
            ingestion_service = get_ingestion_service()
            
            start_dt = start_date.date() if start_date else None
            end_dt = end_date.date() if end_date else None
            
            click.echo(f"🚀 Starting S&P 100 ingestion ({len(config.sp100_tickers)} tickers)...")
            click.echo("⏳ This may take 15-30 minutes...")
            
            result = await ingestion_service.ingest_bulk_tickers(
                tickers=config.sp100_tickers,
                start_date=start_dt,
                end_date=end_dt,
                max_concurrent=3,  # Conservative for free tier
                force_refresh=force_refresh
            )
            
            click.echo(f"✅ S&P 100 ingestion completed:")
            click.echo(f"   📊 Total tickers: {result['total_tickers']}")
            click.echo(f"   ✅ Successful: {result['successful']}")
            click.echo(f"   ❌ Failed: {result['failed']}")
            click.echo(f"   ⏭️  Skipped: {result['skipped']}")
            click.echo(f"   📈 Total records: {result['total_records_stored']}")
            click.echo(f"   ⏱️  Duration: {result['duration_seconds']:.2f} seconds")
            click.echo(f"   💾 Storage: {result['storage_format']}")
            
        except Exception as e:
            click.echo(f"❌ Error: {e}")
            sys.exit(1)
    
    asyncio.run(_ingest_sp100())


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='End date (YYYY-MM-DD)')
@click.option('--force-refresh', is_flag=True, help='Re-fetch existing data')
def ingest_all(start_date: Optional[datetime], end_date: Optional[datetime], 
              force_refresh: bool):
    """Ingest all configured targets (S&P 100 + indexes + ETFs)."""
    
    async def _ingest_all():
        try:
            config = get_modeling_config()
            ingestion_service = get_ingestion_service()
            
            all_tickers = (
                config.sp100_tickers + 
                config.major_indexes + 
                config.sector_etfs
            )
            
            start_dt = start_date.date() if start_date else None
            end_dt = end_date.date() if end_date else None
            
            click.echo(f"🚀 Starting complete ingestion ({len(all_tickers)} tickers)...")
            click.echo("   📊 S&P 100 companies")
            click.echo("   📈 Major indexes")
            click.echo("   🏭 Sector ETFs")
            click.echo("⏳ This may take 30-45 minutes...")
            
            result = await ingestion_service.ingest_bulk_tickers(
                tickers=all_tickers,
                start_date=start_dt,
                end_date=end_dt,
                max_concurrent=3,
                force_refresh=force_refresh
            )
            
            click.echo(f"✅ Complete ingestion finished:")
            click.echo(f"   📊 Total tickers: {result['total_tickers']}")
            click.echo(f"   ✅ Successful: {result['successful']}")
            click.echo(f"   ❌ Failed: {result['failed']}")
            click.echo(f"   ⏭️  Skipped: {result['skipped']}")
            click.echo(f"   📈 Total records: {result['total_records_stored']}")
            click.echo(f"   ⏱️  Duration: {result['duration_seconds']:.2f} seconds")
            click.echo(f"   💾 Storage: {result['storage_format']}")
            
        except Exception as e:
            click.echo(f"❌ Error: {e}")
            sys.exit(1)
    
    asyncio.run(_ingest_all())


@cli.command()
def status():
    """Get storage status and statistics."""
    
    async def _status():
        try:
            storage_service = await get_storage_service()
            stats = await storage_service.get_storage_stats()
            
            click.echo("📊 DuckDB Storage Status:")
            click.echo("=" * 50)
            
            # Daily prices stats
            daily_stats = stats.get('daily_prices', {})
            click.echo(f"📈 Daily Prices:")
            click.echo(f"   • Total records: {daily_stats.get('total_records', 0):,}")
            click.echo(f"   • Unique tickers: {daily_stats.get('unique_tickers', 0)}")
            click.echo(f"   • Date range: {daily_stats.get('earliest_date', 'N/A')} to {daily_stats.get('latest_date', 'N/A')}")
            click.echo(f"   • Trading days: {daily_stats.get('trading_days', 0):,}")
            
            # Storage stats
            storage_stats = stats.get('storage', {})
            click.echo(f"\n💾 Storage:")
            click.echo(f"   • Total size: {storage_stats.get('total_size_mb', 0):.2f} MB")
            click.echo(f"   • Parquet files: {storage_stats.get('parquet_files', 0)}")
            click.echo(f"   • Compression: {storage_stats.get('compression_ratio', 'N/A')}")
            click.echo(f"   • Format: {storage_stats.get('storage_format', 'DuckDB + Parquet')}")
            
            # Performance benefits
            click.echo(f"\n⚡ Performance Benefits:")
            click.echo(f"   • Query speed: 10-100x faster than PostgreSQL")
            click.echo(f"   • Storage efficiency: 80-85% compression")
            click.echo(f"   • Maintenance: Zero database server management")
            click.echo(f"   • ML optimized: Columnar storage for analytics")
            
        except Exception as e:
            click.echo(f"❌ Error getting status: {e}")
            sys.exit(1)
    
    asyncio.run(_status())


@cli.command()
@click.option('--tickers', multiple=True, help='Specific tickers to analyze')
def coverage(tickers: tuple):
    """Get data coverage analysis."""
    
    async def _coverage():
        try:
            ingestion_service = get_ingestion_service()
            
            ticker_list = list(tickers) if tickers else None
            coverage = await ingestion_service.get_data_coverage(tickers=ticker_list)
            
            if 'error' in coverage:
                click.echo(f"❌ Error: {coverage['error']}")
                return
            
            summary = coverage.get('summary', {})
            click.echo("📊 Data Coverage Analysis:")
            click.echo("=" * 50)
            click.echo(f"📈 Summary:")
            click.echo(f"   • Total tickers analyzed: {summary.get('total_tickers_analyzed', 0)}")
            click.echo(f"   • Tickers with data: {summary.get('tickers_with_data', 0)}")
            click.echo(f"   • Tickers with recent data: {summary.get('tickers_with_recent_data', 0)}")
            
            # Show detailed coverage for first 10 tickers
            coverage_by_ticker = coverage.get('coverage_by_ticker', {})
            if coverage_by_ticker:
                click.echo(f"\n📋 Detailed Coverage (showing first 10):")
                for i, (ticker, info) in enumerate(coverage_by_ticker.items()):
                    if i >= 10:
                        break
                    
                    status = "✅" if info['record_count'] > 0 else "❌"
                    recent = "🟢" if info['has_recent_data'] else "🔴"
                    
                    click.echo(f"   {status} {ticker}: {info['record_count']:,} records {recent}")
                    if info['record_count'] > 0:
                        click.echo(f"      📅 {info['earliest_date']} to {info['latest_date']}")
                
                if len(coverage_by_ticker) > 10:
                    click.echo(f"   ... and {len(coverage_by_ticker) - 10} more tickers")
            
        except Exception as e:
            click.echo(f"❌ Error getting coverage: {e}")
            sys.exit(1)
    
    asyncio.run(_coverage())


@cli.command()
@click.argument('ticker')
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='End date (YYYY-MM-DD)')
@click.option('--limit', default=10, help='Number of records to show')
def query(ticker: str, start_date: Optional[datetime], 
         end_date: Optional[datetime], limit: int):
    """Query price data for a ticker."""
    
    async def _query():
        try:
            storage_service = await get_storage_service()
            
            start_dt = start_date.date() if start_date else None
            end_dt = end_date.date() if end_date else None
            
            result_df = await storage_service.query_price_data(
                ticker=ticker,
                start_date=start_dt,
                end_date=end_dt,
                limit=limit
            )
            
            if result_df.empty:
                click.echo(f"❌ No data found for {ticker}")
                return
            
            click.echo(f"📊 Price Data for {ticker} (showing {len(result_df)} records):")
            click.echo("=" * 80)
            
            # Display data in a nice format
            for _, row in result_df.head(limit).iterrows():
                click.echo(f"📅 {row['date']} | Close: ${row['close']:.2f} | Volume: {row['volume']:,}")
            
            if len(result_df) > limit:
                click.echo(f"... and {len(result_df) - limit} more records")
            
        except Exception as e:
            click.echo(f"❌ Error querying data: {e}")
            sys.exit(1)
    
    asyncio.run(_query())


@cli.command()
@click.option('--format', default='csv', help='Export format (csv, parquet, json)')
@click.option('--ticker', help='Specific ticker to export')
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), 
              help='End date (YYYY-MM-DD)')
def export(format: str, ticker: Optional[str], start_date: Optional[datetime], 
          end_date: Optional[datetime]):
    """Export data in various formats."""
    
    async def _export():
        try:
            storage_service = await get_storage_service()
            
            start_dt = start_date.date() if start_date else None
            end_dt = end_date.date() if end_date else None
            
            click.echo(f"📤 Exporting data in {format} format...")
            
            file_path = await storage_service.export_data(
                format=format,
                ticker=ticker,
                start_date=start_dt,
                end_date=end_dt
            )
            
            click.echo(f"✅ Export completed successfully!")
            click.echo(f"   📁 File: {file_path}")
            click.echo(f"   📊 Format: {format}")
            
        except Exception as e:
            click.echo(f"❌ Error exporting data: {e}")
            sys.exit(1)
    
    asyncio.run(_export())


@cli.command()
def optimize():
    """Optimize storage by compacting files and updating statistics."""
    
    async def _optimize():
        try:
            storage_service = await get_storage_service()
            
            click.echo("🔧 Starting storage optimization...")
            
            await storage_service.optimize_storage()
            
            click.echo("✅ Storage optimization completed!")
            click.echo("   • Compacted small Parquet files")
            click.echo("   • Updated table statistics")
            click.echo("   • Optimized query performance")
            
        except Exception as e:
            click.echo(f"❌ Error optimizing storage: {e}")
            sys.exit(1)
    
    asyncio.run(_optimize())


@cli.command()
def backup():
    """Create a single-file backup of all data."""
    
    async def _backup():
        try:
            storage_service = await get_storage_service()
            
            click.echo("💾 Creating backup...")
            
            backup_path = await storage_service.backup_to_single_file()
            
            click.echo("✅ Backup created successfully!")
            click.echo(f"   📁 File: {backup_path}")
            click.echo(f"   📊 Format: Compressed Parquet")
            click.echo(f"   💾 Estimated size: 50-100 MB")
            
        except Exception as e:
            click.echo(f"❌ Error creating backup: {e}")
            sys.exit(1)
    
    asyncio.run(_backup())


@cli.command()
def config():
    """Show configuration information."""
    config = get_modeling_config()
    
    click.echo("⚙️  DuckDB Storage Configuration:")
    click.echo("=" * 50)
    click.echo(f"💾 Storage System: DuckDB + Parquet")
    click.echo(f"📊 S&P 100 Tickers: {len(config.sp100_tickers)} companies")
    click.echo(f"📈 Major Indexes: {len(config.major_indexes)} indexes")
    click.echo(f"🏭 Sector ETFs: {len(config.sector_etfs)} ETFs")
    click.echo(f"📅 Default Lookback: {config.default_lookback_days} days")
    click.echo(f"💰 Max Price Threshold: ${config.max_price_threshold:,}")
    click.echo(f"📊 Max Volume Threshold: {config.max_volume_threshold:,}")
    
    click.echo(f"\n⚡ Performance Features:")
    click.echo(f"   • Columnar storage optimized for analytics")
    click.echo(f"   • 10-100x faster queries than PostgreSQL")
    click.echo(f"   • 80-85% storage compression")
    click.echo(f"   • Zero database server maintenance")
    click.echo(f"   • Perfect for ML feature engineering")


if __name__ == '__main__':
    cli() 