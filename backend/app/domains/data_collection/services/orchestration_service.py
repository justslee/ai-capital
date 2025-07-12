"""
Unified Data Collection Service

This service orchestrates data ingestion from multiple sources,
including Tiingo for price data, FMP for fundamentals, and the SEC for filings.
It uses the client and storage services within the data_collection domain
to create a comprehensive dataset.
"""
import logging
from typing import Dict, Any, Optional
import asyncio
from datetime import date, timedelta

from ..clients.tiingo_client import TiingoClient, get_tiingo_client
from ..clients.fmp_client import FMPClient, get_fmp_client
from ..clients.sec_client import SECClient, get_sec_client
from ..clients.fred_client import FredClient, get_fred_client
from ..storage.s3_storage_service import get_s3_storage_service, S3StorageService
from ..config import get_key_macro_series_ids
from ....sec_utils import ticker_to_cik

logger = logging.getLogger(__name__)

class DataCollectionService:
    """A unified service to manage data collection from all sources."""

    def __init__(self):
        self.tiingo_client = get_tiingo_client()
        self.fmp_client = get_fmp_client()
        self.sec_client = get_sec_client()
        self.fred_client = get_fred_client()
        self.storage_service: S3StorageService = get_s3_storage_service()
        logger.info("DataCollectionService initialized.")

    async def collect_key_macro_indicators(self) -> Dict[str, Any]:
        """
        Collects a predefined list of key macroeconomic indicators from FRED.
        """
        series_ids = get_key_macro_series_ids()
        logger.info(f"Starting collection for {len(series_ids)} key macro indicators...")

        tasks = [self.collect_and_store_macro_series(sid) for sid in series_ids]
        results = await asyncio.gather(*tasks)

        successful_collections = [res for res in results if res.get("status") == "success"]
        failed_collections = [res for res in results if res.get("status") != "success"]

        summary = {
            "status": "completed",
            "total_series_processed": len(series_ids),
            "successful_collections": len(successful_collections),
            "failed_collections": len(failed_collections),
            "details": results
        }
        
        if failed_collections:
            logger.warning(f"Completed with {len(failed_collections)} failures.")
        else:
            logger.info("All key macro indicators collected successfully.")
            
        return summary

    async def collect_daily_prices(self, ticker: str) -> Dict[str, Any]:
        """
        Collects daily market prices for a given ticker, fetching only the data
        missing since the last ingestion.
        """
        logger.info(f"Collecting daily prices for {ticker}...")

        latest_date_in_s3 = await self.storage_service.get_latest_price_date(ticker)
        
        start_date = None
        if latest_date_in_s3:
            start_date = latest_date_in_s3 + timedelta(days=1)
            logger.info(f"Found existing data for {ticker}. Fetching new data from {start_date}.")
            if start_date >= date.today():
                 logger.info(f"Price data for {ticker} is already up-to-date. No new data to fetch.")
                 return {"status": "up_to_date", "source": "tiingo", "ticker": ticker}
        else:
            logger.info(f"No existing data for {ticker}. Fetching all available historical data.")

        price_data = await self.tiingo_client.get_historical_prices(ticker, start_date=start_date)
        
        if price_data:
            await self.storage_service.save_price_data([p.model_dump() for p in price_data], ticker)
            logger.info(f"Successfully stored {len(price_data)} new daily price records for {ticker}.")
            return {"status": "success", "source": "tiingo", "ticker": ticker, "records_added": len(price_data)}
        
        logger.info(f"No new price data found for {ticker} from Tiingo.")
        return {"status": "no_new_data", "source": "tiingo", "ticker": ticker}

    async def collect_fundamentals(self, ticker: str, limit: int = 5) -> Dict[str, Any]:
        """Collects annual fundamental data for a given ticker."""
        logger.info(f"Collecting fundamentals for {ticker}...")

        # Free tier is limited to annual data, limit of 5
        annual_data = await self.fmp_client.get_combined_fundamentals_data(
            ticker, period="annual", limit=limit
        )

        if annual_data:
            # Convert Pydantic models to dicts for storage
            records_to_save = [f.model_dump() for f in annual_data]
            await self.storage_service.save_fundamentals_data(records_to_save, ticker)
            
            logger.info(f"Successfully stored {len(records_to_save)} fundamental records for {ticker}.")
            return {
                "status": "success",
                "source": "fmp",
                "ticker": ticker,
                "records_added": len(records_to_save)
            }
            
        logger.info(f"No new fundamental data found for {ticker} from FMP.")
        return {"status": "no_new_data", "source": "fmp", "ticker": ticker}

    async def collect_sec_filings(self, ticker: str, form_type: str = "10-K") -> Dict[str, Any]:
        """Collects and stores raw SEC filings for a given ticker."""
        logger.info(f"Collecting {form_type} filings for {ticker}...")
        filings = self.sec_client.get_company_filings_by_ticker(ticker, [form_type])
        if filings:
            for filing in filings:
                html_content = self.sec_client.download_filing_html(
                    cik=ticker_to_cik(ticker), # This needs a CIK lookup utility
                    accession_number=filing['accession_number'],
                    primary_doc=filing['primary_doc']
                )
                await self.storage_service.save_filing_html(html_content, ticker, filing['accession_number'])
            logger.info(f"Successfully stored {len(filings)} {form_type} filings for {ticker}.")
            return {"status": "success", "source": "sec", "ticker": ticker, "filings": len(filings)}
        return {"status": "no_data", "source": "sec", "ticker": ticker}
        
    async def collect_and_store_macro_series(self, series_id: str) -> Dict[str, Any]:
        """Fetches a macroeconomic series from FRED and stores it in S3."""
        logger.info(f"Collecting macro series {series_id} from FRED...")
        try:
            macro_data = self.fred_client.get_series(series_id)
            if not macro_data.empty:
                await self.storage_service.save_macro_data(macro_data, series_id)
                logger.info(f"Successfully stored macro series {series_id}.")
                return {"status": "success", "source": "fred", "series_id": series_id, "records": len(macro_data)}
            return {"status": "no_data", "source": "fred", "series_id": series_id}
        except Exception as e:
            logger.error(f"Failed to collect macro series {series_id}: {e}")
            return {"status": "error", "source": "fred", "series_id": series_id, "error": str(e)}

    async def collect_sentiment_data(self, ticker: str) -> None:
        """Placeholder for collecting sentiment data."""
        logger.warning(f"Sentiment data collection for {ticker} is not yet implemented.")
        raise NotImplementedError("Sentiment data collection is not yet implemented.")

_data_collection_service = None

def get_data_collection_service() -> DataCollectionService:
    """Provides a singleton instance of the DataCollectionService."""
    global _data_collection_service
    if _data_collection_service is None:
        _data_collection_service = DataCollectionService()
    return _data_collection_service 