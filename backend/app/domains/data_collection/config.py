"""
Configuration for the Data Collection Domain
"""
from typing import List, Dict
from pydantic_settings import BaseSettings
from functools import lru_cache

class DataCollectionSettings(BaseSettings):
    """Pydantic settings for the data collection domain, loaded from .env."""
    tiingo_api_key: str
    tiingo_base_url: str = "https://api.tiingo.com/tiingo"
    fred_api_key: str
    fmp_api_key: str
    alpha_vantage_api_key: str
    s3_bucket: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    storage_type: str 
    s3_prefix: str

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_data_collection_config() -> DataCollectionSettings:
    """Returns a cached instance of the data collection settings."""
    return DataCollectionSettings()

# A curated list of key macroeconomic indicators from FRED
# This list includes a mix of interest rates, inflation, market volatility, and economic activity indicators.
KEY_MACRO_SERIES: Dict[str, str] = {
    # Interest Rates & Yields (Daily)
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "DGS2": "2-Year Treasury Constant Maturity Rate",
    "T10Y2Y": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity", # Yield Curve
    "FEDFUNDS": "Federal Funds Effective Rate",

    # Market Volatility (Daily)
    "VIXCLS": "CBOE Volatility Index: VIX",

    # Inflation (Daily updates, good for merging)
    "T10YIE": "10-Year Breakeven Inflation Rate",

    # Economic Activity (Monthly/Quarterly - will be forward-filled in analysis)
    "INDPRO": "Industrial Production Index",
    "PAYEMS": "Total Nonfarm Payroll",
    "GDP": "Gross Domestic Product",
    "UNRATE": "Unemployment Rate"
}

def get_key_macro_series_ids() -> List[str]:
    """Returns the list of key FRED series IDs."""
    return list(KEY_MACRO_SERIES.keys()) 