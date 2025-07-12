import asyncio
import click
from dotenv import load_dotenv
from .services import get_data_collection_service
from .services.financial_statements_service import get_financial_statements_service
from .services.sentiment_ingestion_service import get_sentiment_ingestion_service

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

if __name__ == '__main__':
    data_collection_cli() 