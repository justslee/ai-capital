"""
Unified S3 Storage Service

This service handles all interactions with S3 for the data_collection domain.
It provides a single, consistent interface for storing various types of financial data,
such as price data, fundamentals, and SEC filings, in a structured Parquet format.
"""
import asyncio
import io
import logging
from typing import List, Dict, Any, Optional
from datetime import date

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import get_data_collection_config
from ..models.sentiment import Sentiment

logger = logging.getLogger(__name__)

class S3StorageService:
    """A unified service for storing financial data in S3."""

    def __init__(self):
        self.config = get_data_collection_config()
        self.s3_client = boto3.client("s3")
        self.bucket_name = self.config.s3_bucket
        logger.info(f"S3StorageService initialized for bucket: {self.bucket_name}")

    async def _upload_dataframe_to_s3(self, df: pd.DataFrame, s3_key: str):
        """Upload DataFrame to S3 as Parquet using in-memory buffer."""
        try:
            table = pa.Table.from_pandas(df)
            buffer = io.BytesIO()
            pq.write_table(table, buffer, compression='snappy')
            buffer.seek(0)
            
            # Use run_in_executor for the blocking S3 call
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=buffer.getvalue(),
                    ContentType='application/octet-stream'
                )
            )
            logger.info(f"Successfully uploaded to s3://{self.bucket_name}/{s3_key}")
        except Exception as e:
            logger.error(f"Error uploading to S3 key {s3_key}: {e}")
            raise

    async def _download_dataframe_from_s3(self, s3_key: str) -> Optional[pd.DataFrame]:
        """Downloads and reads a Parquet file from S3 into a DataFrame."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            )
            buffer = io.BytesIO(response['Body'].read())
            table = pq.read_table(buffer)
            return table.to_pandas()
        except self.s3_client.exceptions.NoSuchKey:
            logger.info(f"File not found at s3://{self.bucket_name}/{s3_key}. A new file will be created.")
            return None
        except Exception as e:
            logger.error(f"Error downloading or parsing {s3_key}: {e}")
            raise

    async def save_price_data(self, price_data: List[Dict], ticker: str):
        """Saves price data to S3, appending to existing data if present."""
        if not price_data:
            return
        
        new_df = pd.DataFrame(price_data)
        new_df['date'] = pd.to_datetime(new_df['date'])
        new_df['year'] = new_df['date'].dt.year

        for year, year_df in new_df.groupby('year'):
            s3_key = f"market-data/daily_prices/year={year}/daily_prices_{ticker}_{year}.parquet"
            
            existing_df = await self._download_dataframe_from_s3(s3_key)
            
            if existing_df is not None:
                existing_df['date'] = pd.to_datetime(existing_df['date'])
                combined_df = pd.concat([existing_df, year_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                combined_df = combined_df.sort_values(by='date').reset_index(drop=True)
            else:
                combined_df = year_df.sort_values(by='date').reset_index(drop=True)

            # The 'year' column is only for grouping and should not be saved in the parquet file.
            await self._upload_dataframe_to_s3(combined_df.drop(columns=['year']), s3_key)
        
    async def save_fundamentals_data(self, fundamentals_data: List[Dict], ticker: str):
        """Saves fundamentals data to S3, appending to existing data if present."""
        if not fundamentals_data:
            return

        new_df = pd.DataFrame(fundamentals_data)
        # Ensure 'date' is a datetime object for proper handling
        new_df['date'] = pd.to_datetime(new_df['date']).dt.date
        new_df['year'] = pd.to_datetime(new_df['date']).dt.year

        # Group data by year and period (annual/quarterly) to save into separate files
        for (year, period), group_df in new_df.groupby(['year', 'period']):
            s3_key = f"fundamentals/fmp/year={year}/fundamentals_{ticker}_{year}_{period}.parquet"
            
            existing_df = await self._download_dataframe_from_s3(s3_key)

            if existing_df is not None:
                # Ensure 'date' column in existing_df is also in the correct format
                existing_df['date'] = pd.to_datetime(existing_df['date']).dt.date
                # Combine old and new data
                combined_df = pd.concat([existing_df, group_df], ignore_index=True)
                # Remove duplicates, keeping the most recent entry for each date
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                # Sort by date for consistency
                combined_df = combined_df.sort_values(by='date').reset_index(drop=True)
            else:
                # If no existing data, just use the new data
                combined_df = group_df.sort_values(by='date').reset_index(drop=True)
            
            # Drop the 'year' column as it's part of the path, not the data itself
            await self._upload_dataframe_to_s3(combined_df.drop(columns=['year']), s3_key)

    async def save_sentiment_data(self, sentiment_data: List[Sentiment], ticker: str):
        """Saves sentiment data to S3, partitioned by date."""
        if not sentiment_data:
            return

        records = []
        for sentiment in sentiment_data:
            for ticker_sentiment in sentiment.ticker_sentiment:
                if ticker_sentiment.ticker == ticker:
                    records.append({
                        "title": sentiment.title,
                        "url": sentiment.url,
                        "time_published": sentiment.time_published,
                        "summary": sentiment.summary,
                        "source": sentiment.source,
                        "source_domain": sentiment.source_domain,
                        "overall_sentiment_score": sentiment.overall_sentiment_score,
                        "overall_sentiment_label": sentiment.overall_sentiment_label,
                        "ticker": ticker_sentiment.ticker,
                        "relevance_score": ticker_sentiment.relevance_score,
                        "ticker_sentiment_score": ticker_sentiment.ticker_sentiment_score,
                        "ticker_sentiment_label": ticker_sentiment.ticker_sentiment_label,
                    })

        if not records:
            return

        df = pd.DataFrame(records)
        df['time_published'] = pd.to_datetime(df['time_published'], format='%Y%m%dT%H%M%S')
        df['date'] = df['time_published'].dt.date
        
        s3_key = f"sentiment/alpha_vantage/{ticker}/{date.today().isoformat()}.parquet"
        
        await self._upload_dataframe_to_s3(df, s3_key)


    async def save_fmp_financial_statement(
        self,
        statement_data: List[Dict[str, Any]],
        ticker: str,
        statement_type: str
    ):
        """
        Saves a single type of financial statement (e.g., balance sheet) to S3.
        It appends to existing data to ensure no data is lost.
        """
        if not statement_data:
            logger.warning(f"No {statement_type} data provided for {ticker}.")
            return

        new_df = pd.DataFrame(statement_data)
        if 'date' not in new_df.columns:
            logger.error(f"Missing 'date' column in {statement_type} data for {ticker}.")
            return

        new_df['date'] = pd.to_datetime(new_df['date']).dt.date
        new_df['year'] = pd.to_datetime(new_df['date']).dt.year

        for (year, period), group_df in new_df.groupby(['year', 'period']):
            s3_key = f"financial_statements/{statement_type}/{ticker}/year={year}/fmp_{ticker}_{year}_{period}.parquet"
            
            existing_df = await self._download_dataframe_from_s3(s3_key)

            if existing_df is not None:
                existing_df['date'] = pd.to_datetime(existing_df['date']).dt.date
                combined_df = pd.concat([existing_df, group_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                combined_df = combined_df.sort_values(by='date').reset_index(drop=True)
            else:
                combined_df = group_df.sort_values(by='date').reset_index(drop=True)

            await self._upload_dataframe_to_s3(combined_df.drop(columns=['year']), s3_key)

    async def save_financial_statements(self, statements_data: List[Dict], ticker: str):
        """Saves financial statements to S3, partitioned by year and quarter."""
        if not statements_data:
            return
        df = pd.DataFrame(statements_data)
        df['year'] = pd.to_datetime(df['date']).dt.year
        df['quarter'] = pd.to_datetime(df['date']).dt.quarter

        for (year, quarter), group_df in df.groupby(['year', 'quarter']):
            period = f"Q{quarter}" if quarter > 0 else "annual"
            s3_key = f"fundamentals/sec/financial_statements/year={year}/statements_{ticker}_{year}_{period}.parquet"
            await self._upload_dataframe_to_s3(group_df.drop(columns=['year', 'quarter']), s3_key)

    async def save_macro_data(self, macro_data: pd.DataFrame, series_id: str):
        """Saves macroeconomic data to S3, partitioned by year."""
        if macro_data.empty:
            return
        
        df = macro_data.copy()
        df['year'] = df.index.year

        for year, year_df in df.groupby('year'):
            s3_key = f"macro_data/fred/{series_id}/year={year}/data.parquet"
            await self._upload_dataframe_to_s3(year_df.drop(columns=['year']), s3_key)

    async def save_filing_html(self, html_content: str, ticker: str, accession_number: str):
        """Saves raw SEC filing HTML to S3."""
        s3_key = f"sec_filings/{ticker}/{accession_number}.html"
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=html_content.encode('utf-8'),
                    ContentType='text/html'
                )
            )
            logger.info(f"Successfully saved HTML for {accession_number} to s3://{self.bucket_name}/{s3_key}")
        except Exception as e:
            logger.error(f"Error saving HTML for {accession_number} to S3: {e}")
            raise

    async def get_filing_html(self, ticker: str, accession_number: str) -> Optional[str]:
        """Retrieves the HTML content of a specific SEC filing from S3."""
        s3_key = f"sec_filings/{ticker}/{accession_number}.html"
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            )
            html_content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully retrieved HTML for {accession_number} from s3://{self.bucket_name}/{s3_key}")
            return html_content
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Filing not found in S3: {s3_key}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving HTML for {accession_number} from S3: {e}")
            return None

    async def get_fundamentals(self, ticker: str) -> Optional[pd.DataFrame]:
        """Retrieves all fundamentals data for a ticker from S3."""
        s3_prefix = f"fundamentals/fmp/year="
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            all_data = []
            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if f"fundamentals_{ticker}" in key:
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        df = pq.read_table(io.BytesIO(response['Body'].read())).to_pandas()
                        all_data.append(df)
            
            if not all_data:
                logger.warning(f"No fundamentals data found for {ticker} in S3.")
                return None

            return pd.concat(all_data, ignore_index=True)
            
        except Exception as e:
            logger.error(f"Error retrieving fundamentals data for {ticker} from S3: {e}")
            return None

    async def get_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Retrieves all price data for a ticker from S3."""
        s3_prefix = f"market-data/daily_prices/year="
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            all_data = []
            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if f"daily_prices_{ticker}" in key:
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                        df = pq.read_table(io.BytesIO(response['Body'].read())).to_pandas()
                        all_data.append(df)
            
            if not all_data:
                logger.warning(f"No price data found for {ticker} in S3.")
                return None

            return pd.concat(all_data, ignore_index=True)
            
        except Exception as e:
            logger.error(f"Error retrieving price data for {ticker} from S3: {e}")
            return None

    async def get_latest_price_date(self, ticker: str) -> Optional[date]:
        """Retrieves the latest date for which price data exists for a ticker."""
        s3_prefix = "market-data/daily_prices/"
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            # Find all keys for the ticker to identify the latest file
            all_ticker_keys = []
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
                for obj in page.get('Contents', []):
                    if f"daily_prices_{ticker}" in obj.get('Key', ''):
                        all_ticker_keys.append(obj['Key'])

            if not all_ticker_keys:
                logger.info(f"No existing price data found for {ticker} in S3.")
                return None

            # The latest key corresponds to the file with the most recent data
            latest_key = max(all_ticker_keys)
            logger.info(f"Latest price data file found for {ticker}: {latest_key}")

            # Download and read only the latest file to find the max date
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=latest_key)
            df = pq.read_table(io.BytesIO(response['Body'].read())).to_pandas()

            if 'date' not in df.columns:
                logger.warning(f"Column 'date' not found in {latest_key}")
                return None
            
            # Ensure the date column is properly formatted
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            latest_date = df['date'].max()
            logger.info(f"Latest price date for {ticker} is {latest_date}")
            return latest_date

        except Exception as e:
            logger.error(f"Error retrieving latest price date for {ticker} from S3: {e}")
            return None

_s3_storage_service = None

def get_s3_storage_service() -> "S3StorageService":
    """Provides a singleton instance of the S3StorageService."""
    global _s3_storage_service
    if _s3_storage_service is None:
        _s3_storage_service = S3StorageService()
    return _s3_storage_service 