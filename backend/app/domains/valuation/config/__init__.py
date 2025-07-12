"""
Valuation Domain Configuration

Configuration settings and constants for company valuation calculations.
"""

# Standard library imports
from typing import Dict, Optional, Any

# Third-party imports
from pydantic import Field

# App imports
from app.shared.config_helpers import BaseDomainConfig, create_domain_config


class ValuationConfig(BaseDomainConfig):
    """Configuration for the valuation domain."""
    
    # Financial Modeling Prep API Configuration
    fmp_api_key: Optional[str] = Field(None, env="FMP_API_KEY")
    fmp_base_url: str = Field(default="https://financialmodelingprep.com/api/v3", env="FMP_BASE_URL")
    fmp_rate_limit_per_minute: int = Field(default=300, env="FMP_RATE_LIMIT_PER_MINUTE")  # Free tier limit
    
    # DCF Calculation Settings
    discount_rate: float = Field(default=0.10, env="DCF_DISCOUNT_RATE")  # 10% default WACC
    terminal_growth_rate: float = Field(default=0.025, env="DCF_TERMINAL_GROWTH_RATE")  # 2.5% default
    projection_years: int = Field(default=5, env="DCF_PROJECTION_YEARS")  # 5-year projection
    
    # Financial Data Settings
    financial_cache_ttl: int = Field(default=86400, env="FINANCIAL_CACHE_TTL")  # 24 hours
    historical_years: int = Field(default=5, env="HISTORICAL_YEARS")  # 5 years of historical data
    
    # Risk-free Rate and Market Data
    risk_free_rate: float = Field(default=0.045, env="RISK_FREE_RATE")  # 4.5% default
    market_risk_premium: float = Field(default=0.06, env="MARKET_RISK_PREMIUM")  # 6% default
    
    # Validation Settings
    max_market_cap_threshold: float = Field(default=10_000_000_000_000, env="MAX_MARKET_CAP_THRESHOLD")  # $10T
    min_market_cap_threshold: float = Field(default=1_000_000, env="MIN_MARKET_CAP_THRESHOLD")  # $1M
    
    def validate_required_fields(self) -> Dict[str, bool]:
        """
        Validate that all required fields are present.
        
        Returns:
            Dictionary mapping field names to validation status
        """
        results = super().validate_required_fields()
        
        # Check FMP API key
        results["fmp_api_key"] = bool(self.fmp_api_key)
        
        return results
    
    def get_dcf_params(self) -> Dict[str, Any]:
        """
        Get DCF calculation parameters.
        
        Returns:
            Dictionary of DCF parameters
        """
        return {
            "discount_rate": self.discount_rate,
            "terminal_growth_rate": self.terminal_growth_rate,
            "projection_years": self.projection_years,
            "risk_free_rate": self.risk_free_rate,
            "market_risk_premium": self.market_risk_premium,
        }


# Global configuration instance
_valuation_config = None


def get_valuation_config() -> ValuationConfig:
    """Get the global valuation configuration."""
    global _valuation_config
    if _valuation_config is None:
        _valuation_config = create_domain_config(ValuationConfig)
    return _valuation_config


# Constants for valuation calculations
FINANCIAL_STATEMENT_TYPES = {
    "income_statement": "income-statement",
    "balance_sheet": "balance-sheet-statement", 
    "cash_flow": "cash-flow-statement",
    "key_metrics": "key-metrics",
    "ratios": "ratios",
    "growth": "financial-growth",
}

REQUIRED_FINANCIAL_FIELDS = {
    "income_statement": [
        "revenue", "totalRevenue", "costOfRevenue", "grossProfit",
        "operatingIncome", "netIncome", "eps", "epsdiluted"
    ],
    "balance_sheet": [
        "totalAssets", "totalLiabilities", "totalStockholdersEquity",
        "totalDebt", "cash", "cashAndCashEquivalents"
    ],
    "cash_flow": [
        "operatingCashFlow", "capitalExpenditure", "freeCashFlow",
        "netCashProvidedByOperatingActivities"
    ],
}

DCF_CALCULATION_CONSTANTS = {
    "min_projection_years": 3,
    "max_projection_years": 10,
    "min_discount_rate": 0.05,  # 5%
    "max_discount_rate": 0.20,  # 20%
    "min_terminal_growth": 0.0,  # 0%
    "max_terminal_growth": 0.05,  # 5%
    "default_tax_rate": 0.21,  # 21% corporate tax rate
}


__all__ = [
    "ValuationConfig",
    "get_valuation_config",
    "FINANCIAL_STATEMENT_TYPES",
    "REQUIRED_FINANCIAL_FIELDS",
    "DCF_CALCULATION_CONSTANTS",
] 