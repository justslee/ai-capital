# Standard library imports
import asyncio
import logging
from typing import List

# App imports
from ..clients.alpha_vantage_client import get_alpha_vantage_client, AlphaVantageClient
from ..storage.s3_storage_service import get_s3_storage_service, S3StorageService
from ..models.sentiment import SentimentFeed

logger = logging.getLogger(__name__)

class SentimentIngestionService:
    def __init__(
        self,
        alpha_vantage_client: AlphaVantageClient = get_alpha_vantage_client(),
        s3_storage_service: S3StorageService = get_s3_storage_service(),
    ):
        self.alpha_vantage_client = alpha_vantage_client
        self.s3_storage_service = s3_storage_service

    async def ingest_sentiment_for_ticker(self, ticker: str):
        """Fetches and stores sentiment data for a single ticker."""
        logger.info(f"Ingesting sentiment for {ticker}")
        try:
            sentiment_data = await self.alpha_vantage_client.get_news_sentiment(tickers=[ticker])
            if sentiment_data:
                sentiment_feed = SentimentFeed.model_validate(sentiment_data)
                await self.s3_storage_service.save_sentiment_data(sentiment_feed.feed, ticker)
                logger.info(f"Successfully ingested sentiment for {ticker}")
            else:
                logger.warning(f"No sentiment data returned for {ticker}")
        except Exception as e:
            logger.error(f"Failed to ingest sentiment for {ticker}: {e}")

    async def ingest_sentiment_for_tickers(self, tickers: List[str]):
        """
        Fetches and stores sentiment data for a list of tickers, with a delay
        to respect API rate limits.
        """
        # Alpha Vantage free tier is 5 calls per minute.
        # So we wait 12 seconds between calls.
        delay_seconds = 15 
        for ticker in tickers:
            await self.ingest_sentiment_for_ticker(ticker)
            logger.info(f"Waiting for {delay_seconds} seconds before next ticker...")
            await asyncio.sleep(delay_seconds)

def get_sentiment_ingestion_service() -> "SentimentIngestionService":
    """Returns a singleton instance of the SentimentIngestionService."""
    return SentimentIngestionService() 