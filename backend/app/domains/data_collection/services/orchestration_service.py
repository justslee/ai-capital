"""
Unified Data Collection Service

This service orchestrates data ingestion from multiple sources,
including Tiingo for price data, FMP for fundamentals, and the SEC for filings.
It uses the client and storage services within the data_collection domain
to create a comprehensive dataset.

Enhanced with centralized ticker management and batch processing capabilities.
"""
import logging
from typing import Dict, Any, Optional, List
import asyncio
from datetime import date, timedelta

from ..clients.tiingo_client import TiingoClient, get_tiingo_client
from ..clients.fmp_client import FMPClient, get_fmp_client
from ..clients.sec_client import SECClient, get_sec_client
from ..clients.fred_client import FredClient, get_fred_client
from ..storage.s3_storage_service import get_s3_storage_service, S3StorageService
from ..config import get_key_macro_series_ids
from ..config.ticker_config import get_ticker_config, TickerGroup, TickerConfig
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
        self.ticker_config: TickerConfig = get_ticker_config()

    async def collect_key_macro_indicators(self) -> Dict[str, Any]:
        """
        Collects a predefined list of key macroeconomic indicators from FRED.
        """
        series_ids = get_key_macro_series_ids()

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
        
            
        return summary

    async def collect_daily_prices(self, ticker: str) -> Dict[str, Any]:
        """
        Collects daily market prices for a given ticker, fetching only the data
        missing since the last ingestion.
        """

        latest_date_in_s3 = await self.storage_service.get_latest_price_date(ticker)
        
        start_date = None
        if latest_date_in_s3:
            start_date = latest_date_in_s3 + timedelta(days=1)
            if start_date >= date.today():
                 return {"status": "up_to_date", "source": "tiingo", "ticker": ticker}

        price_data = await self.tiingo_client.get_historical_prices(ticker, start_date=start_date)
        
        if price_data:
            await self.storage_service.save_price_data([p.model_dump() for p in price_data], ticker)
            return {"status": "success", "source": "tiingo", "ticker": ticker, "records_added": len(price_data)}
        return {"status": "no_new_data", "source": "tiingo", "ticker": ticker}

    async def collect_fundamentals(self, ticker: str, limit: int = 5) -> Dict[str, Any]:

        # Free tier is limited to annual data, limit of 5
        annual_data = await self.fmp_client.get_combined_fundamentals_data(
            ticker, period="annual", limit=limit
        )

        if annual_data:
            # Convert Pydantic models to dicts for storage
            records_to_save = [f.model_dump() for f in annual_data]
            await self.storage_service.save_fundamentals_data(records_to_save, ticker)
            return {
                "status": "success",
                "source": "fmp",
                "ticker": ticker,
                "records_added": len(records_to_save)
            }
            
        return {"status": "no_new_data", "source": "fmp", "ticker": ticker}

    async def collect_sec_filings(self, ticker: str, form_type: str = "10-K") -> Dict[str, Any]:
        filings = self.sec_client.get_company_filings_by_ticker(ticker, [form_type])
        if filings:
            for filing in filings:
                html_content = self.sec_client.download_filing_html(
                    cik=ticker_to_cik(ticker), # This needs a CIK lookup utility
                    accession_number=filing['accession_number'],
                    primary_doc=filing['primary_doc']
                )
                await self.storage_service.save_filing_html(html_content, ticker, filing['accession_number'])
            return {"status": "success", "source": "sec", "ticker": ticker, "filings": len(filings)}
        return {"status": "no_data", "source": "sec", "ticker": ticker}
        
    async def collect_and_store_macro_series(self, series_id: str) -> Dict[str, Any]:
        try:
            macro_data = self.fred_client.get_series(series_id)
            if not macro_data.empty:
                await self.storage_service.save_macro_data(macro_data, series_id)
                return {"status": "success", "source": "fred", "series_id": series_id, "records": len(macro_data)}
            return {"status": "no_data", "source": "fred", "series_id": series_id}
        except Exception as e:
            logger.error(f"Failed to collect macro series {series_id}: {e}")
            return {"status": "error", "source": "fred", "series_id": series_id, "error": str(e)}

    async def collect_sentiment_data(self, ticker: str) -> None:
        """Placeholder for collecting sentiment data."""
        raise NotImplementedError("Sentiment data collection is not yet implemented.")

    # Batch Processing Methods with Ticker Groups

    async def collect_daily_prices_batch(self, group: TickerGroup, max_concurrent: int = 5) -> Dict[str, Any]:
        """
        Collect daily prices for all tickers in a specified group.
        
        Args:
            group: The ticker group to process
            max_concurrent: Maximum number of concurrent API calls
            
        Returns:
            Dictionary with batch processing results
        """
        tickers = self.ticker_config.get_tickers_by_group(group)
        
        if not tickers:
            return {
                "status": "no_tickers",
                "group": group.value,
                "message": f"No tickers found for group {group.value}"
            }
        
        logger.info(f"Starting batch price collection for {group.value} group ({len(tickers)} tickers)")
        
        # Use semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def collect_single_ticker(ticker: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.collect_daily_prices(ticker)
                    # Add small delay to respect API rate limits
                    await asyncio.sleep(0.1)
                    return result
                except Exception as e:
                    logger.error(f"Failed to collect prices for {ticker}: {e}")
                    return {
                        "status": "error", 
                        "ticker": ticker, 
                        "source": "tiingo",
                        "error": str(e)
                    }
        
        # Execute all ticker collections concurrently
        tasks = [collect_single_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        # Summarize results
        successful = [r for r in results if r.get("status") == "success"]
        up_to_date = [r for r in results if r.get("status") == "up_to_date"]
        failed = [r for r in results if r.get("status") == "error"]
        no_data = [r for r in results if r.get("status") == "no_new_data"]
        
        summary = {
            "status": "completed",
            "group": group.value,
            "total_tickers": len(tickers),
            "successful": len(successful),
            "up_to_date": len(up_to_date),
            "failed": len(failed),
            "no_new_data": len(no_data),
            "results": results
        }
        
        logger.info(f"Batch price collection completed for {group.value}: "
                   f"{len(successful)} successful, {len(failed)} failed")
        
        return summary

    async def collect_fundamentals_batch(self, group: TickerGroup, max_concurrent: int = 3, limit: int = 5) -> Dict[str, Any]:
        """
        Collect fundamental data for all tickers in a specified group.
        
        Args:
            group: The ticker group to process
            max_concurrent: Maximum number of concurrent API calls (lower for fundamentals)
            limit: Number of years of fundamental data to fetch
            
        Returns:
            Dictionary with batch processing results
        """
        tickers = self.ticker_config.get_tickers_by_group(group)
        
        if not tickers:
            return {
                "status": "no_tickers",
                "group": group.value,
                "message": f"No tickers found for group {group.value}"
            }
        
        logger.info(f"Starting batch fundamentals collection for {group.value} group ({len(tickers)} tickers)")
        
        # Use semaphore to limit concurrent API calls (more conservative for fundamentals)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def collect_single_ticker(ticker: str) -> Dict[str, Any]:
            async with semaphore:
                try:
                    result = await self.collect_fundamentals(ticker, limit=limit)
                    # Add delay to respect API rate limits
                    await asyncio.sleep(0.5)
                    return result
                except Exception as e:
                    logger.error(f"Failed to collect fundamentals for {ticker}: {e}")
                    return {
                        "status": "error", 
                        "ticker": ticker, 
                        "source": "fmp",
                        "error": str(e)
                    }
        
        # Execute all ticker collections concurrently
        tasks = [collect_single_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        
        # Summarize results
        successful = [r for r in results if r.get("status") == "success"]
        failed = [r for r in results if r.get("status") == "error"]
        no_data = [r for r in results if r.get("status") == "no_new_data"]
        
        summary = {
            "status": "completed",
            "group": group.value,
            "total_tickers": len(tickers),
            "successful": len(successful),
            "failed": len(failed),
            "no_new_data": len(no_data),
            "results": results
        }
        
        logger.info(f"Batch fundamentals collection completed for {group.value}: "
                   f"{len(successful)} successful, {len(failed)} failed")
        
        return summary

    async def collect_comprehensive_batch(self, group: TickerGroup, include_fundamentals: bool = True) -> Dict[str, Any]:
        """
        Collect both prices and fundamentals for all tickers in a group.
        
        Args:
            group: The ticker group to process
            include_fundamentals: Whether to collect fundamental data
        
        Returns:
            Dictionary with comprehensive batch processing results
        """
        logger.info(f"Starting comprehensive data collection for {group.value} group")
        
        # Collect prices first (faster)
        price_results = await self.collect_daily_prices_batch(group)
        
        results = {
            "status": "completed",
            "group": group.value,
            "price_collection": price_results
        }
        
        if include_fundamentals:
            # Collect fundamentals second (slower, more rate-limited)
            fundamentals_results = await self.collect_fundamentals_batch(group)
            results["fundamentals_collection"] = fundamentals_results
        
        return results

    def get_available_ticker_groups(self) -> List[Dict[str, Any]]:
        """Get information about all available ticker groups."""
        return [
            {
                "group": group.value,
                "description": self._get_group_description(group),
                "ticker_count": len(self.ticker_config.get_tickers_by_group(group)),
                "sample_tickers": self.ticker_config.get_tickers_by_group(group)[:5]
            }
            for group in TickerGroup if group != TickerGroup.ALL
        ]
    
    def _get_group_description(self, group: TickerGroup) -> str:
        """Get human-readable description for ticker groups."""
        descriptions = {
            TickerGroup.DOW: "Dow Jones Industrial Average (30 components)",
            TickerGroup.SP500: "S&P 500 Index (500 large-cap stocks)",
            TickerGroup.NASDAQ: "NASDAQ 100 Index (100 largest non-financial stocks)",
            TickerGroup.RUSSELL2000: "Russell 2000 Index (small-cap stocks)",
            TickerGroup.TOP_ETFS: "Major Index and Sector ETFs"
        }
        return descriptions.get(group, f"Ticker group: {group.value}")

_data_collection_service = None

def get_data_collection_service() -> DataCollectionService:
    """Provides a singleton instance of the DataCollectionService."""
    global _data_collection_service
    if _data_collection_service is None:
        _data_collection_service = DataCollectionService()
    return _data_collection_service 