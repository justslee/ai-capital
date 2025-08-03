import asyncio
import click
from dotenv import load_dotenv
from .services import get_data_collection_service
from .services.financial_statements_service import get_financial_statements_service
from .services.sentiment_ingestion_service import get_sentiment_ingestion_service
from .config.ticker_config import TickerGroup, get_ticker_config

# Load environment variables from .env file
load_dotenv()

@click.group()
def data_collection_cli():
    """CLI for managing the data collection domain."""
    pass

@data_collection_cli.command()
def fetch_key_indicators():
    """
    Fetches a predefined list of key macroeconomic indicators from FRED 
    and stores them in S3.
    """
    click.echo("Fetching key macroeconomic indicators from FRED...")
    service = get_data_collection_service()
    
    async def main():
        result = await service.collect_key_macro_indicators()
        click.echo("Collection process completed.")
        click.echo(f"Summary: {result}")

    asyncio.run(main())

@data_collection_cli.command()
@click.argument('ticker')
def fetch_daily_prices(ticker: str):
    """
    Fetches missing daily prices for a stock ticker from Tiingo.
    TICKER: The stock ticker symbol (e.g., 'AAPL').
    """
    click.echo(f"Fetching daily prices for ticker: {ticker.upper()}")
    service = get_data_collection_service()
    
    async def main():
        result = await service.collect_daily_prices(ticker.upper())
        click.echo("Collection process completed.")
        click.echo(f"Summary: {result}")

    asyncio.run(main())

@data_collection_cli.command()
@click.argument('tickers', nargs=-1)
def fetch_fundamentals(tickers: tuple[str]):
    """
    Fetches fundamental data for a list of stock tickers from FMP.
    TICKERS: A space-separated list of stock ticker symbols (e.g., 'AAPL' 'MSFT').
    """
    if not tickers:
        click.echo("Please provide at least one ticker.")
        return

    click.echo(f"Starting fundamental data collection for: {', '.join(tickers)}")
    service = get_data_collection_service()

    async def main():
        tasks = [service.collect_fundamentals(ticker.upper()) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        click.echo("\n--- Bulk Ingestion Summary ---")
        for result in results:
            click.echo(f"  - {result.get('ticker')}: {result.get('status')}, Records: {result.get('records_added', 0)}")
        click.echo("---------------------------------")

    asyncio.run(main())

@data_collection_cli.command()
@click.argument('tickers', nargs=-1)
def fetch_financial_statements(tickers: tuple[str]):
    """
    Fetches financial statements for a list of stock tickers from FMP.
    TICKERS: A space-separated list of stock ticker symbols (e.g., 'AAPL' 'MSFT').
    """
    if not tickers:
        click.echo("Please provide at least one ticker.")
        return

    click.echo(f"Starting financial statement collection for: {', '.join(tickers)}")
    service = get_financial_statements_service()

    async def main():
        for ticker in tickers:
            click.echo(f"Fetching statements for {ticker.upper()}...")
            await service.ingest_financial_statements_for_ticker(ticker.upper())
            click.echo(f"Completed {ticker.upper()}. Waiting 15 seconds before next ticker...")
            await asyncio.sleep(15) # Add a delay to avoid rate-limiting

        click.echo("\n--- Financial Statement Ingestion Complete ---")

    asyncio.run(main())

@data_collection_cli.command()
@click.argument('tickers', nargs=-1)
def fetch_sentiment(tickers: tuple[str]):
    """
    Fetches news sentiment for a list of stock tickers from Alpha Vantage.
    TICKERS: A space-separated list of stock ticker symbols (e.g., 'AAPL' 'MSFT').
    """
    if not tickers:
        click.echo("Please provide at least one ticker.")
        return

    click.echo(f"Starting sentiment data collection for: {', '.join(tickers)}")
    service = get_sentiment_ingestion_service()

    async def main():
        await service.ingest_sentiment_for_tickers(list(tickers))
        click.echo("\n--- Sentiment Ingestion Complete ---")

    asyncio.run(main())


# New Batch Processing Commands with Ticker Groups

@data_collection_cli.command()
@click.option('--group', 
              type=click.Choice(['dow', 'sp500', 'nasdaq', 'russell2000', 'top_etfs']), 
              required=True,
              help='Ticker group to process')
@click.option('--max-concurrent', 
              default=5, 
              help='Maximum concurrent API calls (default: 5)')
def fetch_prices_batch(group: str, max_concurrent: int):
    """
    Fetch daily prices for all tickers in a specified group.
    
    This command uses the centralized ticker configuration to process
    entire index groups efficiently with controlled concurrency.
    """
    click.echo(f"Fetching daily prices for {group.upper()} ticker group...")
    click.echo(f"Max concurrent requests: {max_concurrent}")
    
    service = get_data_collection_service()
    ticker_group = TickerGroup(group)
    
    async def main():
        # Show ticker count before starting
        config = get_ticker_config()
        tickers = config.get_tickers_by_group(ticker_group)
        click.echo(f"Processing {len(tickers)} tickers...")
        
        result = await service.collect_daily_prices_batch(ticker_group, max_concurrent)
        
        click.echo(f"\n--- Batch Price Collection Summary ---")
        click.echo(f"Group: {result['group'].upper()}")
        click.echo(f"Total Tickers: {result['total_tickers']}")
        click.echo(f"✅ Successful: {result['successful']}")
        click.echo(f"📅 Up to Date: {result['up_to_date']}")
        click.echo(f"❌ Failed: {result['failed']}")
        click.echo(f"📭 No New Data: {result['no_new_data']}")
        click.echo("----------------------------------------")
        
        # Show failed tickers if any
        if result['failed'] > 0:
            failed_tickers = [r['ticker'] for r in result['results'] if r.get('status') == 'error']
            click.echo(f"Failed tickers: {', '.join(failed_tickers[:10])}")
            if len(failed_tickers) > 10:
                click.echo(f"... and {len(failed_tickers) - 10} more")

    asyncio.run(main())


@data_collection_cli.command()
@click.option('--group', 
              type=click.Choice(['dow', 'sp500', 'nasdaq', 'russell2000', 'top_etfs']), 
              required=True,
              help='Ticker group to process')
@click.option('--max-concurrent', 
              default=3, 
              help='Maximum concurrent API calls (default: 3)')
@click.option('--limit', 
              default=5, 
              help='Number of years of data to fetch (default: 5)')
def fetch_fundamentals_batch(group: str, max_concurrent: int, limit: int):
    """
    Fetch fundamental data for all tickers in a specified group.
    
    This command processes fundamental data with more conservative
    rate limiting due to API restrictions.
    """
    click.echo(f"Fetching fundamentals for {group.upper()} ticker group...")
    click.echo(f"Max concurrent requests: {max_concurrent}")
    click.echo(f"Years of data: {limit}")
    
    service = get_data_collection_service()
    ticker_group = TickerGroup(group)
    
    async def main():
        # Show ticker count before starting
        config = get_ticker_config()
        tickers = config.get_tickers_by_group(ticker_group)
        click.echo(f"Processing {len(tickers)} tickers...")
        
        result = await service.collect_fundamentals_batch(ticker_group, max_concurrent, limit)
        
        click.echo(f"\n--- Batch Fundamentals Collection Summary ---")
        click.echo(f"Group: {result['group'].upper()}")
        click.echo(f"Total Tickers: {result['total_tickers']}")
        click.echo(f"✅ Successful: {result['successful']}")
        click.echo(f"❌ Failed: {result['failed']}")
        click.echo(f"📭 No New Data: {result['no_new_data']}")
        click.echo("---------------------------------------------")
        
        # Show failed tickers if any
        if result['failed'] > 0:
            failed_tickers = [r['ticker'] for r in result['results'] if r.get('status') == 'error']
            click.echo(f"Failed tickers: {', '.join(failed_tickers[:10])}")
            if len(failed_tickers) > 10:
                click.echo(f"... and {len(failed_tickers) - 10} more")

    asyncio.run(main())


@data_collection_cli.command()
@click.option('--group', 
              type=click.Choice(['dow', 'sp500', 'nasdaq', 'russell2000', 'top_etfs']), 
              required=True,
              help='Ticker group to process')
@click.option('--include-fundamentals/--prices-only', 
              default=True,
              help='Include fundamental data collection (default: True)')
def fetch_comprehensive_batch(group: str, include_fundamentals: bool):
    """
    Fetch both prices and fundamentals for all tickers in a group.
    
    This command performs a comprehensive data collection including
    both daily prices and fundamental data with optimized sequencing.
    """
    click.echo(f"Starting comprehensive data collection for {group.upper()} group...")
    if include_fundamentals:
        click.echo("Including: Daily prices + Fundamental data")
    else:
        click.echo("Including: Daily prices only")
    
    service = get_data_collection_service()
    ticker_group = TickerGroup(group)
    
    async def main():
        # Show ticker count before starting
        config = get_ticker_config()
        tickers = config.get_tickers_by_group(ticker_group)
        click.echo(f"Processing {len(tickers)} tickers...")
        
        result = await service.collect_comprehensive_batch(ticker_group, include_fundamentals)
        
        click.echo(f"\n--- Comprehensive Collection Summary ---")
        click.echo(f"Group: {result['group'].upper()}")
        
        # Price collection summary
        price_result = result['price_collection']
        click.echo(f"\n📈 PRICE COLLECTION:")
        click.echo(f"  ✅ Successful: {price_result['successful']}")
        click.echo(f"  📅 Up to Date: {price_result['up_to_date']}")
        click.echo(f"  ❌ Failed: {price_result['failed']}")
        
        # Fundamentals collection summary (if included)
        if include_fundamentals and 'fundamentals_collection' in result:
            fund_result = result['fundamentals_collection']
            click.echo(f"\n📊 FUNDAMENTALS COLLECTION:")
            click.echo(f"  ✅ Successful: {fund_result['successful']}")
            click.echo(f"  ❌ Failed: {fund_result['failed']}")
        
        click.echo("----------------------------------------")

    asyncio.run(main())


@data_collection_cli.command()
def list_ticker_groups():
    """
    List all available ticker groups and their contents.
    
    Shows the available groups, ticker counts, and sample tickers
    for planning batch data collection operations.
    """
    click.echo("Available Ticker Groups:")
    click.echo("=" * 50)
    
    service = get_data_collection_service()
    groups_info = service.get_available_ticker_groups()
    
    for group_info in groups_info:
        click.echo(f"\n📊 {group_info['group'].upper()}")
        click.echo(f"   Description: {group_info['description']}")
        click.echo(f"   Ticker Count: {group_info['ticker_count']}")
        click.echo(f"   Sample: {', '.join(group_info['sample_tickers'])}")
    
    click.echo("\n" + "=" * 50)
    click.echo("Usage Examples:")
    click.echo("  python -m app.domains.data_collection.cli fetch-prices-batch --group dow")
    click.echo("  python -m app.domains.data_collection.cli fetch-fundamentals-batch --group sp500")
    click.echo("  python -m app.domains.data_collection.cli fetch-comprehensive-batch --group nasdaq")


@data_collection_cli.command()
@click.argument('group', type=click.Choice(['dow', 'sp500', 'nasdaq', 'russell2000', 'top_etfs']))
def show_group_tickers(group: str):
    """
    Show all tickers in a specific group.
    
    GROUP: The ticker group to display (dow, sp500, nasdaq, russell2000, top_etfs)
    """
    config = get_ticker_config()
    ticker_group = TickerGroup(group)
    tickers = config.get_tickers_by_group(ticker_group)
    
    click.echo(f"\n{group.upper()} Tickers ({len(tickers)} total):")
    click.echo("=" * 40)
    
    # Display in columns of 10
    for i in range(0, len(tickers), 10):
        row = tickers[i:i+10]
        click.echo("  ".join(f"{ticker:6}" for ticker in row))
    
    click.echo("=" * 40)


if __name__ == '__main__':
    data_collection_cli() 