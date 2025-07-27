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
from botocore.exceptions import ClientError

from app.domains.data_collection.config import get_data_collection_config
from ..models.sentiment import Sentiment

logger = logging.getLogger(__name__)

class S3StorageService:
    """A unified service for storing financial data in S3."""

    def __init__(self):
        self.config = get_data_collection_config()
        self.bucket_name = self.config.s3_bucket_name or self.config.s3_bucket
        if not self.bucket_name:
            raise ValueError("S3 bucket name not configured. Set S3_BUCKET in .env file")
    
    def _get_s3_client(self):
        """Create a fresh S3 client to avoid token expiration issues."""
        return boto3.client("s3")

    async def _upload_dataframe_to_s3(self, df: pd.DataFrame, s3_key: str):
        try:
            out_buffer = io.BytesIO()
            df.to_parquet(out_buffer, index=True)
            out_buffer.seek(0)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().put_object(Bucket=self.bucket_name, Key=s3_key, Body=out_buffer)
            )
        except Exception as e:
            logger.error(f"Error uploading to {s3_key}: {e}")
            raise

    async def download_multiple_dataframes(self, s3_keys: List[str]) -> List[pd.DataFrame]:
        tasks = [self._download_dataframe_from_s3(key) for key in s3_keys]
        results = await asyncio.gather(*tasks)
        return [df for df in results if df is not None and not df.empty]

    async def _download_dataframe_from_s3(self, s3_key: str) -> Optional[pd.DataFrame]:
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().get_object(Bucket=self.bucket_name, Key=s3_key)
            )
            buffer = io.BytesIO(response['Body'].read())
            table = pq.read_table(buffer)
            return table.to_pandas()
        except ClientError:
            return None
        except Exception as e:
            logger.error(f"Error downloading or parsing {s3_key}: {e}")
            raise

    async def save_price_data(self, price_data: List[Dict], ticker: str):
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

            await self._upload_dataframe_to_s3(combined_df.drop(columns=['year']), s3_key)
        
    async def save_fundamentals_data(self, fundamentals_data: List[Dict], ticker: str):
        if not fundamentals_data:
            return

        new_df = pd.DataFrame(fundamentals_data)
        new_df['date'] = pd.to_datetime(new_df['date']).dt.date
        new_df['year'] = pd.to_datetime(new_df['date']).dt.year

        for (year, period), group_df in new_df.groupby(['year', 'period']):
            s3_key = f"fundamentals/fmp/year={year}/fundamentals_{ticker}_{year}_{period}.parquet"
            
            existing_df = await self._download_dataframe_from_s3(s3_key)

            if existing_df is not None:
                existing_df['date'] = pd.to_datetime(existing_df['date']).dt.date
                combined_df = pd.concat([existing_df, group_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                combined_df = combined_df.sort_values(by='date').reset_index(drop=True)
            else:
                combined_df = group_df.sort_values(by='date').reset_index(drop=True)
            
            await self._upload_dataframe_to_s3(combined_df.drop(columns=['year']), s3_key)

    async def save_sentiment_data(self, sentiment_data: List[Sentiment], ticker: str):
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
        if not statement_data:
            return

        new_df = pd.DataFrame(statement_data)
        if 'date' not in new_df.columns:
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
        if macro_data.empty:
            return
        
        df = macro_data.copy()
        df['year'] = df.index.year

        for year, year_df in df.groupby('year'):
            s3_key = f"macro_data/fred/{series_id}/year={year}/data.parquet"
            await self._upload_dataframe_to_s3(year_df.drop(columns=['year']), s3_key)

    async def save_filing_html(self, html_content: str, ticker: str, accession_number: str):
        s3_key = f"sec_filings/{ticker.upper()}/{accession_number}.html"
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=html_content.encode('utf-8'),
                    ContentType='text/html'
                )
            )
        except Exception as e:
            logger.error(f"Error saving HTML for {accession_number} to S3: {e}")
            raise

    async def get_filing_html(self, ticker: str, accession_number: str) -> Optional[str]:
        """Retrieves the HTML content of a specific filing."""
        key = f"sec_filings/{ticker.upper()}/{accession_number}.html"
        return await self._get_object_content(key)

    async def save_text_chunk(self, chunk_text: str, s3_key: str) -> None:
        """
        Saves a single text chunk to a specified S3 key.

        :param chunk_text: The text content of the chunk.
        :param s3_key: The full S3 key to save the chunk to.
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=chunk_text.encode('utf-8'),
                    ContentType='text/plain'
                )
            )
            logger.info(f"Successfully saved chunk to {s3_key}")
        except ClientError as e:
            logger.error(f"Failed to save chunk to {s3_key}: {e}")
            raise

    async def save_summary_document(self, document_content: str, file_id: str) -> None:
        """
        Saves a final summary document to a specified S3 key.
        Assumes content is Markdown or HTML.

        :param document_content: The content of the summary document.
        :param file_id: The unique ID for the summary file.
        """
        s3_key = f"summaries/{file_id}.md"
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=document_content.encode('utf-8'),
                    ContentType='text/markdown' # Or 'text/html'
                )
            )
            logger.info(f"Successfully saved summary document to {s3_key}")
        except ClientError as e:
            logger.error(f"Failed to save summary document to {s3_key}: {e}")
            raise

    async def list_and_read_chunks(self, ticker: str, accession_number: str, section: str) -> List[str]:
        """Lists and reads all chunk files for a given section from S3."""
        prefix = f"chunks/{ticker.upper()}/{accession_number}/{section}/"
        keys = await self.list_objects(prefix)
        
        tasks = [self._get_object_content(key) for key in keys]
        chunk_contents = await asyncio.gather(*tasks)
        
        # Filter out any None results from failed reads
        return [content for content in chunk_contents if content is not None]

    async def _get_object_content(self, s3_key: str) -> Optional[str]:
        """
        Get the text content of an S3 object.
        
        :param s3_key: The S3 key of the object
        :return: The content as a string, or None if not found
        """
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().get_object(Bucket=self.bucket_name, Key=s3_key)
            )
            return response['Body'].read().decode('utf-8')
        except ClientError:
            logger.warning(f"Object not found: {s3_key}")
            return None
        except Exception as e:
            logger.error(f"Error reading object {s3_key}: {e}")
            return None

    async def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generates a direct public URL for an S3 object.

        :param s3_key: The key of the object in S3.
        :param expiration: (Ignored for public URLs) Time in seconds for the presigned URL to remain valid.
        :return: The direct public URL as a string. If bucket name is not configured, returns None.
        """
        if not self.bucket_name:
            logger.error("S3 bucket name is not configured. Cannot generate public URL.")
            return None
        
        # Construct the public URL
        public_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
        logger.info(f"Generated public S3 URL: {public_url}")
        return public_url

    async def object_exists(self, key: str) -> bool:
        """
        Checks if an object exists in S3.

        :param key: The full S3 key of the object.
        :return: True if the object exists, False otherwise.
        """
        try:
            await self._get_s3_client().head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
        except Exception as e:
            logger.error(f"Error checking object existence for {key}: {e}")
            return False

    async def _read_s3_file(self, s3_key: str) -> Optional[str]:
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._get_s3_client().get_object(Bucket=self.bucket_name, Key=s3_key)
            )
            return response['Body'].read().decode('utf-8')
        except ClientError:
            return None
        except Exception as e:
            logger.error(f"Error reading file from S3 ({s3_key}): {e}")
            return None

    async def get_fundamentals(self, ticker: str) -> Optional[pd.DataFrame]:
        s3_prefix = f"fundamentals/fmp/year="
        try:
            paginator = self._get_s3_client().get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            all_data = []
            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if f"fundamentals_{ticker}" in key:
                        response = self._get_s3_client().get_object(Bucket=self.bucket_name, Key=key)
                        df = pq.read_table(io.BytesIO(response['Body'].read())).to_pandas()
                        all_data.append(df)
            
            if not all_data:
                return None

            return pd.concat(all_data, ignore_index=True)
            
        except Exception as e:
            logger.error(f"Error retrieving fundamentals data for {ticker} from S3: {e}")
            return None

    async def get_price_data(self, ticker: str) -> Optional[pd.DataFrame]:
        s3_prefix = f"market-data/daily_prices/"
        try:
            paginator = self._get_s3_client().get_paginator('list_objects_v2')
            all_ticker_keys = []
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
                for obj in page.get('Contents', []):
                    if f"daily_prices_{ticker}" in obj.get('Key', ''):
                        all_ticker_keys.append(obj['Key'])

            if not all_ticker_keys:
                return None
            
            return pd.concat(await self.download_multiple_dataframes(all_ticker_keys), ignore_index=True)

        except Exception as e:
            logger.error(f"Error retrieving price data for {ticker} from S3: {e}")
            return None

    async def get_latest_price_date(self, ticker: str) -> Optional[date]:
        s3_prefix = "market-data/daily_prices/"
        try:
            paginator = self._get_s3_client().get_paginator('list_objects_v2')
            
            all_ticker_keys = []
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
                for obj in page.get('Contents', []):
                    if f"daily_prices_{ticker}" in obj.get('Key', ''):
                        all_ticker_keys.append(obj['Key'])

            if not all_ticker_keys:
                    return None

            latest_key = max(all_ticker_keys)

            response = self._get_s3_client().get_object(Bucket=self.bucket_name, Key=latest_key)
            df = pq.read_table(io.BytesIO(response['Body'].read())).to_pandas()

            if 'date' not in df.columns:
                return None
            
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            latest_date = df['date'].max()
            return latest_date

        except Exception as e:
            logger.error(f"Error retrieving latest price date for {ticker} from S3: {e}")
            return None

from app.shared.singleton import get_singleton

def get_s3_storage_service() -> "S3StorageService":
    """Provides a singleton instance of the S3StorageService."""
    return get_singleton(S3StorageService) 