# Standard library imports
import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from functools import partial
from typing import Optional, List, Dict, Any, Union

# Third-party imports
import httpx
from pydantic import parse_obj_as, ValidationError, TypeAdapter, BaseModel
from decimal import Decimal
import pandas as pd

# App imports
from ..config import get_data_collection_config
from ..models.financials import (
    IncomeStatementEntry,
    BalanceSheetEntry,
    CashFlowEntry,
    FinancialsResponse,
    IncomeStatementListAdapter,
    BalanceSheetListAdapter,
    CashFlowListAdapter,
    FMPFundamentalsDataPoint
)

logger = logging.getLogger(__name__)

FMP_API_BASE_URL = "https://financialmodelingprep.com/api"

class FMPClient:
    # Use httpx.AsyncClient for asynchronous requests
    _client: httpx.AsyncClient

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://financialmodelingprep.com/api"):
        self.config = get_data_collection_config()
        self.api_key = api_key or self.config.fmp_api_key
        if not self.api_key:
            raise ValueError("FMP API key is required. Set FMP_API_KEY environment variable.")
        self.base_url = base_url.rstrip('/')
        # Initialize the async client instance
        # Consider adding headers like User-Agent if needed
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0) # Set base_url and timeout
        self.ratios_endpoint = "v3/ratios"
        self.key_metrics_endpoint = "v3/key-metrics"


    # Use __aenter__ and __aexit__ for async context management if creating client per request
    # Or provide explicit close method if client lifecycle is managed externally
    async def close(self):
        """Closes the underlying httpx client."""
        await self._client.aclose()

    # Mark method as async
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[List[Dict]]:
        """Make HTTP request to FMP API with error handling."""
        # Always add API key to params
        all_params = {"apikey": self.api_key, **(params or {})}

        try:
            logger.debug(f"Making request to {endpoint} with params: {params}")
            response = await self._client.get(endpoint, params=all_params)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle API errors
            if isinstance(data, dict) and "Error Message" in data:
                logger.warning(f"FMP API error for endpoint {endpoint}: {data['Error Message']}")
                return None
            
            # Handle empty responses
            if isinstance(data, list) and not data:
                logger.info(f"No data returned from endpoint {endpoint}")
                return []
                
            # Handle unexpected response format
            if not isinstance(data, list):
                logger.warning(f"Unexpected response format from {endpoint}: {type(data)}")
                return None
                
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for endpoint {endpoint}: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error for endpoint {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred for endpoint {endpoint}: {e}")
            return None

    # Generic helper for cache logic
    async def _get_cached_or_fetch(
        self,
        cache_key: str,
        fetch_coroutine,
        list_adapter: TypeAdapter,
        model_name: str,
        symbol: str
    ) -> Optional[List[BaseModel]]:
        # Direct fetch without caching
        api_data_list = await fetch_coroutine()
        if api_data_list is None: return None
        if not api_data_list: return []
        try:
                return parse_obj_as(list_adapter.core_schema, api_data_list)
        except ValidationError as e:
                # Silent validation error
                return None

    # Mark method as async
    async def get_income_statements(self, symbol: str, limit: int = 5, period: str = 'annual') -> Optional[List[IncomeStatementEntry]]:
        """Fetches income statements for a given stock symbol."""
        endpoint = f"/v3/income-statement/{symbol.upper()}"
        params = {'limit': limit, 'period': period}
        cache_key = f"fmp:{symbol.upper()}:{period}:{limit}:income"
        
        # Define the coroutine to fetch data if cache miss
        async def fetch(): 
            return await self._make_request(endpoint, params=params)
            
        return await self._get_cached_or_fetch(
            cache_key=cache_key,
            fetch_coroutine=fetch,
            list_adapter=IncomeStatementListAdapter,
            model_name="income statements",
            symbol=symbol
        )

    # Mark method as async
    async def get_balance_sheets(self, symbol: str, limit: int = 5, period: str = 'annual') -> Optional[List[BalanceSheetEntry]]:
        """Fetches balance sheet statements for a given stock symbol."""
        endpoint = f"/v3/balance-sheet-statement/{symbol.upper()}"
        params = {'limit': limit, 'period': period}
        cache_key = f"fmp:{symbol.upper()}:{period}:{limit}:balance"

        async def fetch():
             return await self._make_request(endpoint, params=params)
             
        return await self._get_cached_or_fetch(
            cache_key=cache_key,
            fetch_coroutine=fetch,
            list_adapter=BalanceSheetListAdapter,
            model_name="balance sheets",
            symbol=symbol
        )

    # Mark method as async
    async def get_cash_flows(self, symbol: str, limit: int = 5, period: str = 'annual') -> Optional[List[CashFlowEntry]]:
        """Fetches cash flow statements for a given stock symbol."""
        endpoint = f"/v3/cash-flow-statement/{symbol.upper()}"
        params = {'limit': limit, 'period': period}
        cache_key = f"fmp:{symbol.upper()}:{period}:{limit}:cashflow"

        async def fetch():
            return await self._make_request(endpoint, params=params)

        return await self._get_cached_or_fetch(
            cache_key=cache_key,
            fetch_coroutine=fetch,
            list_adapter=CashFlowListAdapter,
            model_name="cash flows",
            symbol=symbol
        )

    # Mark method as async
    async def get_financials(self, symbol: str, period: str = "annual", limit: int = 5) -> Optional[FinancialsResponse]:
        """Fetch all financial statements for a company."""
        
        # Use asyncio.gather to run requests concurrently
        results = await asyncio.gather(
            self.get_income_statements(symbol, limit, period),
            self.get_balance_sheets(symbol, limit, period),
            self.get_cash_flows(symbol, limit, period),
            return_exceptions=True # Optionally handle individual errors later if needed
        )

        # Unpack results (check for errors if not using return_exceptions=True)
        income_statements, balance_sheets, cash_flows = results

        # Check if any request failed (returned None or an Exception if return_exceptions=True)
        if isinstance(income_statements, Exception) or income_statements is None or \
           isinstance(balance_sheets, Exception) or balance_sheets is None or \
           isinstance(cash_flows, Exception) or cash_flows is None:
             # Silent error - failed to fetch one or more financial statements
             return None

        return FinancialsResponse(
            income_statements=income_statements,
            balance_sheets=balance_sheets,
            cash_flows=cash_flows
        )

    async def get_fundamentals_ratios(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get fundamentals ratios data from FMP API.
        
        Args:
            ticker: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to fetch
            
        Returns:
            List of ratios data or None if error
        """
        endpoint = f"/{self.ratios_endpoint}/{ticker.upper()}"
        params = { "period": period, "limit": limit }
        return await self._make_request(endpoint, params=params)

    async def get_key_metrics(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get key metrics data from FMP API.
        
        Args:
            ticker: Stock symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to fetch
            
        Returns:
            List of key metrics data or None if error
        """
        endpoint = f"/{self.key_metrics_endpoint}/{ticker.upper()}"
        params = { "period": period, "limit": limit }
        return await self._make_request(endpoint, params=params)
    
    def _merge_fundamentals_data(
        self,
        ratios_data: List[Dict[str, Any]],
        metrics_data: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Merges ratios and key metrics dataframes."""
        
        # Convert to DataFrames
        ratios_df = pd.DataFrame(ratios_data)
        metrics_df = pd.DataFrame(metrics_data)

        # Basic validation
        if ratios_df.empty and metrics_df.empty:
            return pd.DataFrame()
        if ratios_df.empty:
            return metrics_df
        if metrics_df.empty:
            return ratios_df
            
        # Standardize date columns for merging
        ratios_df['date'] = pd.to_datetime(ratios_df['date']).dt.date
        metrics_df['date'] = pd.to_datetime(metrics_df['date']).dt.date

        # Merge on symbol, date, and period
        # Use an outer merge to keep all data from both frames
        merged_df = pd.merge(
            ratios_df,
            metrics_df,
            on=["symbol", "date", "period"],
            how="outer",
            suffixes=('_ratio', '_metric')
        )
        return merged_df

    def _convert_dataframe_to_datapoints(
        self,
        df: pd.DataFrame,
        ticker: str
    ) -> List[FMPFundamentalsDataPoint]:
        """Converts a merged DataFrame into a list of FMPFundamentalsDataPoint objects."""
        
        datapoints = []
        
        # Helper to safely convert values to Decimal
        def safe_decimal(value, default=None):
            if value is None or pd.isna(value):
                return default
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return default

        for _, row in df.iterrows():
            # Use .get() to avoid KeyErrors if a column is missing
            datapoint_data = {
                "ticker": ticker,
                "date": row.get("date"),
                "period": row.get("period"),
                "pe_ratio": safe_decimal(row.get('priceEarningsRatio')),
                "pb_ratio": safe_decimal(row.get('priceToBookRatio')),
                "ps_ratio": safe_decimal(row.get('priceToSalesRatio')),
                "pcf_ratio": safe_decimal(row.get('priceCashFlowRatio')),
                "peg_ratio": safe_decimal(row.get('priceEarningsToGrowthRatio')),
                "ev_to_sales": safe_decimal(row.get('evToSales')),
                "ev_to_ebitda": safe_decimal(row.get('enterpriseValueOverEBITDA')),
                "market_cap": safe_decimal(row.get('marketCap')),
                "enterprise_value": safe_decimal(row.get('enterpriseValue')),
                "net_profit_margin": safe_decimal(row.get('netProfitMargin')),
                "return_on_assets": safe_decimal(row.get('returnOnAssets')),
                "return_on_equity": safe_decimal(row.get('returnOnEquity')),
                "return_on_capital_employed": safe_decimal(row.get('returnOnCapitalEmployed')),
                "current_ratio": safe_decimal(row.get('currentRatio_metric')),
                "quick_ratio": safe_decimal(row.get('quickRatio')),
                "cash_ratio": safe_decimal(row.get('cashRatio')),
                "operating_cash_flow_per_share": safe_decimal(row.get('operatingCashFlowPerShare')),
                "free_cash_flow_per_share": safe_decimal(row.get('freeCashFlowPerShare')),
                "debt_to_equity": safe_decimal(row.get('debtToEquity_metric')),
                "debt_to_assets": safe_decimal(row.get('debtToAssets_metric')),
                "net_debt_to_ebitda": safe_decimal(row.get('netDebtToEBITDA_metric')),
                "interest_coverage": safe_decimal(row.get('interestCoverage_metric')),
                "asset_turnover": safe_decimal(row.get('assetTurnover')),
                "inventory_turnover": safe_decimal(row.get('inventoryTurnover_metric')),
                "receivables_turnover": safe_decimal(row.get('receivablesTurnover_metric')),
                "days_of_sales_outstanding": safe_decimal(row.get('daysOfSalesOutstanding')),
                "days_of_inventory_outstanding": safe_decimal(row.get('daysOfInventoryOutstanding')),
                "days_of_payables_outstanding": safe_decimal(row.get('daysOfPayablesOutstanding')),
                "cash_conversion_cycle": safe_decimal(row.get('cashConversionCycle')),
                "revenue_growth": safe_decimal(row.get('revenue_growth')),
                "epsgrowth": safe_decimal(row.get('eps_growth')),
                "operating_income_growth": safe_decimal(row.get('operating_income_growth')),
                "free_cash_flow_growth": safe_decimal(row.get('free_cash_flow_growth')),
                "book_value_per_share": safe_decimal(row.get('bookValuePerShare')),
                "tangible_book_value_per_share": safe_decimal(row.get('tangibleBookValuePerShare')),
                "shareholders_equity_per_share": safe_decimal(row.get('shareholdersEquityPerShare')),
                "dividend_yield": safe_decimal(row.get('dividendYield_metric')),
                "dividend_payout_ratio": safe_decimal(row.get('payoutRatio_metric')),
                "shares_outstanding": safe_decimal(row.get('shares_outstanding')),
                "weighted_average_shares_outstanding": safe_decimal(row.get('weighted_average_shares_outstanding')),
                "earnings_per_share": safe_decimal(row.get('eps')),
                "working_capital": safe_decimal(row.get('workingCapital')),
            }
            try:
                datapoints.append(FMPFundamentalsDataPoint(**datapoint_data))
            except ValidationError as e:
                logger.warning(f"Validation error for {ticker} on {row.get('date')}: {e}")

        return datapoints

    async def get_combined_fundamentals_data(
        self,
        ticker: str,
        period: str = "annual",
        limit: int = 10
    ) -> Optional[List[FMPFundamentalsDataPoint]]:
        """
        Fetches, merges, and converts financial ratios and key metrics for a given ticker.
        This method orchestrates fetching data from both ratios and key metrics endpoints,
        merges them into a single structure, and converts them to a list of Pydantic models.
        """
        logger.info(f"Starting combined fundamentals collection for {ticker} ({period}, limit={limit})")

        # Fetch both data sources concurrently
        ratios_data, metrics_data = await asyncio.gather(
            self.get_fundamentals_ratios(ticker, period, limit),
            self.get_key_metrics(ticker, period, limit)
        )
        
        # Handle cases where one or both API calls fail
        if not ratios_data or not metrics_data:
            logger.warning(f"Could not fetch complete fundamentals for {ticker}. "
                           f"Ratios fetched: {'Yes' if ratios_data else 'No'}, "
                           f"Metrics fetched: {'Yes' if metrics_data else 'No'}")
            # If one is missing, decide if you want to proceed with partial data.
            # For simplicity, we'll require both for a combined view.
            return None

        # Merge the datasets
        merged_df = self._merge_fundamentals_data(ratios_data, metrics_data)

        if merged_df.empty:
            logger.info(f"No combined fundamental data available for {ticker} after merging.")
            return []

        # Convert the merged DataFrame to a list of Pydantic models
        datapoints = self._convert_dataframe_to_datapoints(merged_df, ticker)
        
        logger.info(f"Successfully created {len(datapoints)} combined fundamental datapoints for {ticker}")
        return datapoints

    async def test_connection(self) -> bool:
        """
        Tests the connection to the FMP API by fetching data for a known ticker.
        """
        try:
            # Test fetching ratios for a common ticker
            ratios = await self.get_fundamentals_ratios("AAPL", limit=1)
            if ratios is not None:
                logger.info("✅ FMP API connection successful.")
                return True
            else:
                logger.error("❌ FMP API connection failed: Could not fetch data for AAPL.")
                return False
        except Exception as e:
            logger.error(f"❌ FMP API connection failed with exception: {e}")
            return False

_fmp_client = None

def get_fmp_client() -> "FMPClient":
    """Provides a singleton instance of the FMPClient."""
    global _fmp_client
    if _fmp_client is None:
        _fmp_client = FMPClient()
    return _fmp_client

# FMP API client for fetching financial market data with caching support. 