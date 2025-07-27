from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class DataCollectionSettings(BaseSettings):
    """
    Configuration settings for the data collection domain.
    """
    fmp_api_key: Optional[str] = None
    alpha_vantage_api_key: Optional[str] = None
    tiingo_api_key: Optional[str] = None
    tiingo_base_url: str = "https://api.tiingo.com"
    fred_api_key: Optional[str] = None
    sec_api_user_agent: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    s3_bucket: Optional[str] = None  # Alternative field name

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

@lru_cache()
def get_data_collection_config() -> DataCollectionSettings:
    """Provides a cached singleton instance of the DataCollectionSettings."""
    return DataCollectionSettings()

def get_key_macro_series_ids() -> list[str]:
    """
    Returns a list of key macroeconomic indicator series IDs from FRED.
    These are commonly used indicators for financial analysis and modeling.
    """
    return [
        "GDP",           # Gross Domestic Product
        "CPIAUCSL",      # Consumer Price Index for All Urban Consumers: All Items
        "UNRATE",        # Unemployment Rate
        "DGS10",         # 10-Year Treasury Constant Maturity Rate
        "DFF",           # Federal Funds Rate
        "M2SL",          # M2 Money Stock
        "INDPRO",        # Industrial Production Index
        "HOUST",         # Housing Starts: Total: New Privately Owned Housing Units Started
        "PAYEMS",        # All Employees, Total Nonfarm
        "DEXUSEU",       # U.S. / Euro Foreign Exchange Rate
    ] 