"""
Modeling Domain Configuration

Configuration settings for the modeling domain including API keys,
data source settings, and market constants.
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class ModelingConfig(BaseSettings):
    """Configuration for the modeling domain."""
    
    # Tiingo API Configuration
    tiingo_api_key: Optional[str] = Field(None, env="TIINGO_API_KEY")
    tiingo_base_url: str = "https://api.tiingo.com/tiingo"
    tiingo_rate_limit_per_hour: int = 500  # Free tier limit
    
    # AlphaVantage API Configuration (for future use)
    alphavantage_api_key: Optional[str] = Field(None, env="ALPHAVANTAGE_API_KEY")
    alphavantage_base_url: str = "https://www.alphavantage.co/query"
    alphavantage_rate_limit_per_minute: int = 5  # Free tier limit
    
    # Data Ingestion Settings
    max_concurrent_requests: int = 5
    request_delay_seconds: float = 0.1
    batch_size: int = 100
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Historical Data Settings
    default_start_date: str = "1970-01-01"  # Go back as far as possible
    data_frequency: str = "daily"  # daily, weekly, monthly
    
    # Database Settings
    enable_database_storage: bool = True
    enable_csv_backup: bool = True
    csv_backup_path: str = "./data/backups/"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables
    
    # Data validation settings
    max_price_threshold: float = 100000.0
    max_volume_threshold: int = 10_000_000_000
    default_lookback_days: int = 365 * 10  # 10 years default
    
    @property
    def sp100_tickers(self) -> List[str]:
        """Get S&P 100 ticker symbols."""
        return SP_100_TICKERS.copy()
    
    @property
    def major_indexes(self) -> List[str]:
        """Get major index symbols."""
        symbols = []
        for index_list in MAJOR_INDEXES.values():
            symbols.extend(index_list)
        return sorted(list(set(symbols)))
    
    @property
    def sector_etfs(self) -> List[str]:
        """Get sector ETF symbols."""
        symbols = []
        for sector_list in SECTOR_ETFS.values():
            symbols.extend(sector_list)
        return sorted(list(set(symbols)))


# Market Constants and Lists
SP_100_TICKERS = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE",
    "CRM", "INTC", "CSCO", "ORCL", "IBM", "QCOM", "TXN", "AVGO", "AMD", "INTU",
    
    # Healthcare
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "TMO", "DHR", "BMY", "AMGN", "GILD",
    "CVS", "MDT", "ISRG", "VRTX", "REGN", "CI", "HUM", "ANTM", "ELV", "LLY",
    
    # Financial Services
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "USB", "TFC", "PNC",
    "BLK", "SCHW", "CME", "ICE", "SPGI", "MCO", "AON", "MMC", "TRV", "PGR",
    
    # Consumer Discretionary
    "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "MAR", "GM", "F",
    "AMZN", "TSLA", "TGT", "COST", "WMT", "CVX", "XOM", "COP", "SLB", "OXY",
    
    # Consumer Staples & Other
    "KO", "PEP", "WMT", "PG", "JNJ", "KMB", "CL", "GIS", "K", "CPB",
    "MO", "PM", "KHC", "MDLZ", "HSY", "STZ", "TAP", "CAG", "SJM", "HRL",
    
    # Additional top companies
    "V", "MA", "PYPL", "DIS", "VZ", "T", "CMCSA", "NFLX", "CRM", "NOW"
]

# Remove duplicates and sort
SP_100_TICKERS = sorted(list(set(SP_100_TICKERS)))

# Major Market Indexes
MAJOR_INDEXES = {
    "SP500": ["SPY", "^GSPC"],           # S&P 500
    "NASDAQ": ["QQQ", "^IXIC", "^NDX"],  # NASDAQ
    "DOW": ["DIA", "^DJI"],              # Dow Jones
    "RUSSELL": ["IWM", "^RUT"],          # Russell 2000
    "VIX": ["^VIX"],                     # Volatility Index
}

# Sector ETFs for diversification
SECTOR_ETFS = {
    "Technology": ["XLK", "VGT"],
    "Healthcare": ["XLV", "VHT"],
    "Financial": ["XLF", "VFH"],
    "Energy": ["XLE", "VDE"],
    "Materials": ["XLB", "VAW"],
    "Industrials": ["XLI", "VIS"],
    "Utilities": ["XLU", "VPU"],
    "Consumer_Discretionary": ["XLY", "VCR"],
    "Consumer_Staples": ["XLP", "VDC"],
    "Real_Estate": ["XLRE", "VNQ"],
    "Communication": ["XLC", "VOX"],
}

# Flatten all symbols for easy access
ALL_SYMBOLS = SP_100_TICKERS.copy()
for index_list in MAJOR_INDEXES.values():
    ALL_SYMBOLS.extend(index_list)
for sector_list in SECTOR_ETFS.values():
    ALL_SYMBOLS.extend(sector_list)

# Remove duplicates
ALL_SYMBOLS = sorted(list(set(ALL_SYMBOLS)))

# Data validation settings
VALIDATION_RULES = {
    "min_price": 0.01,
    "max_price": 100000.0,
    "min_volume": 0,
    "max_volume": 10_000_000_000,
    "required_fields": ["date", "close"],
    "optional_fields": ["open", "high", "low", "volume", "adj_close"]
}


def get_modeling_config() -> ModelingConfig:
    """Get the modeling configuration instance."""
    return ModelingConfig()


def get_all_target_symbols() -> List[str]:
    """Get all symbols we want to track."""
    return ALL_SYMBOLS.copy()


def get_sp100_symbols() -> List[str]:
    """Get S&P 100 symbols."""
    return SP_100_TICKERS.copy()


def get_index_symbols() -> List[str]:
    """Get major index symbols."""
    symbols = []
    for index_list in MAJOR_INDEXES.values():
        symbols.extend(index_list)
    return sorted(list(set(symbols))) 