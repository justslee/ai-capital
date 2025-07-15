"""
Service for merging price data with macroeconomic indicators and calculating technical features.
"""
import logging
import pandas as pd
from typing import List, Optional, Tuple
from datetime import date
import asyncio

from ..storage.s3_storage_service import S3StorageService, get_s3_storage_service
from ...price_prediction.features.technical_indicators import TechnicalIndicatorsGenerator
from ..config import get_key_macro_series_ids

logger = logging.getLogger(__name__)

class DataMergingService:
    """Merges different data sources and calculates technical indicators."""

    def __init__(
        self,
        s3_storage_service: S3StorageService = get_s3_storage_service(),
        technical_indicators_generator: TechnicalIndicatorsGenerator = TechnicalIndicatorsGenerator()
    ):
        self.s3_storage = s3_storage_service
        self.technical_indicators = technical_indicators_generator

    async def get_merged_data(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Retrieves a merged dataset for a ticker, containing price, macro, and technical data.
        It attempts to load from S3 first and regenerates the data if it's not found or invalid.
        """
        if not force_refresh:
            try:
                existing_data = await self._get_existing_merged_data(ticker, start_date, end_date)
                if existing_data is not None:
                    is_valid, _ = self._validate_merged_data(existing_data)
                    if is_valid:
                        return existing_data
            except Exception:
                pass

        merged_df = await self._generate_merged_dataset(ticker, start_date, end_date)

        if merged_df is not None:
            is_valid, issues = self._validate_merged_data(merged_df)
            if not is_valid:
                logger.error(f"Generated data for {ticker} is invalid: {issues}")
                return None
            
            await self._save_merged_data(merged_df, ticker)
            return merged_df

        return None

    async def _generate_merged_dataset(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Optional[pd.DataFrame]:
        """Orchestrates the creation of the merged dataset."""
        price_df = await self.s3_storage.get_price_data(ticker)
        if price_df is None or price_df.empty:
            logger.warning(f"No price data found for {ticker}")
            return None

        price_df['date'] = pd.to_datetime(price_df['date'])
        price_df = price_df.sort_values('date').set_index('date')

        if start_date:
            price_df = price_df[price_df.index.date >= start_date]
        if end_date:
            price_df = price_df[price_df.index.date <= end_date]
        
        if price_df.empty:
            logger.warning(f"No price data for {ticker} in the specified date range.")
            return None

        all_macro_dfs = [df for df in await self._get_all_macro_data() if df is not None]
        
        merged_df = price_df
        if all_macro_dfs:
            macro_df = pd.concat(all_macro_dfs, axis=1).resample('D').ffill()
            merged_df = pd.merge(price_df, macro_df, left_index=True, right_index=True, how='left')

        indicator_features = self.technical_indicators.generate_features(merged_df.reset_index())
        for indicator_type in indicator_features.values():
            if indicator_type:
                for name, series in indicator_type.items():
                    merged_df[name] = series.values

        logger.info(f"Successfully generated dataset for {ticker} with shape {merged_df.shape}")
        return merged_df.reset_index()

    async def _get_all_macro_data(self) -> List[Optional[pd.DataFrame]]:
        """Fetches all key macroeconomic data series from S3."""
        tasks = [self._get_macro_series_data(sid) for sid in get_key_macro_series_ids()]
        return await asyncio.gather(*tasks)

    async def _get_macro_series_data(self, series_id: str) -> Optional[pd.DataFrame]:
        """Helper to get and process a single macro data series."""
        try:
            years = range(1970, date.today().year + 1)
            s3_keys = [f"macro_data/fred/{series_id}/year={y}/data.parquet" for y in years]
            
            all_dfs = await self.s3_storage.download_multiple_dataframes(s3_keys)
            
            if not all_dfs:
                return None
            
            combined_df = pd.concat(all_dfs)
            combined_df.columns = [series_id]
            combined_df.index = pd.to_datetime(combined_df.index)
            return combined_df
        except Exception as e:
            logger.error(f"Failed to get macro series {series_id}: {e}")
            return None

    async def _save_merged_data(self, merged_df: pd.DataFrame, ticker: str):
        """Saves the merged DataFrame to S3, partitioned by year."""
        merged_df['year'] = pd.to_datetime(merged_df['date']).dt.year
        for year, year_df in merged_df.groupby('year'):
            s3_key = f"merged_data/year={year}/merged_{ticker}_{year}.parquet"
            await self.s3_storage._upload_dataframe_to_s3(year_df.drop(columns=['year']), s3_key)

    async def _get_existing_merged_data(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Optional[pd.DataFrame]:
        """Retrieves an existing merged dataset from S3."""
        years = range(start_date.year if start_date else 1970, (end_date or date.today()).year + 1)
        s3_keys = [f"merged_data/year={y}/merged_{ticker}_{y}.parquet" for y in years]
        
        all_dfs = await self.s3_storage.download_multiple_dataframes(s3_keys)
        
        if not all_dfs:
            return None
        
        merged_df = pd.concat(all_dfs).sort_values('date').reset_index(drop=True)
        merged_df['date'] = pd.to_datetime(merged_df['date'])
        
        if start_date:
            merged_df = merged_df[merged_df['date'].dt.date >= start_date]
        if end_date:
            merged_df = merged_df[merged_df['date'].dt.date <= end_date]
            
        return merged_df if not merged_df.empty else None

    def _validate_merged_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validates the data quality of the merged dataset."""
        issues = []
        
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            issues.append(f"Missing required columns: {[col for col in required_columns if col not in df.columns]}")

        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                first_valid = df[col].first_valid_index()
                if first_valid is not None and df[col][first_valid:].isnull().any():
                    issues.append(f"Missing values in '{col}' after first valid entry")
        
        return not issues, issues

# Service instance
data_merging_service = DataMergingService() 