# Standard library imports
import asyncio
import json
from datetime import timedelta
from functools import partial
from typing import Optional, List, Dict, Any

# Third-party imports
import httpx
from pydantic import parse_obj_as, ValidationError, TypeAdapter, BaseModel
# import redis.asyncio as redis  # Optional dependency

# App imports
from app.config import settings
from app.schemas.financials import (
    IncomeStatementEntry,
    BalanceSheetEntry,
    CashFlowEntry,
    FinancialsResponse,
    IncomeStatementListAdapter,
    BalanceSheetListAdapter,
    CashFlowListAdapter
)
# from app.domains.summarization.core.cache import get_redis_client  # Optional caching

FMP_API_BASE_URL = "https://financialmodelingprep.com/api"

class FMPClient:
    # Use httpx.AsyncClient for asynchronous requests
    _client: httpx.AsyncClient

    def __init__(self, api_key: str = settings.fmp_api_key, base_url: str = FMP_API_BASE_URL):
        if not api_key:
            raise ValueError("FMP API key is required. Set FMP_API_KEY environment variable.")
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        # Initialize the async client instance
        # Consider adding headers like User-Agent if needed
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0) # Set base_url and timeout

    # Use __aenter__ and __aexit__ for async context management if creating client per request
    # Or provide explicit close method if client lifecycle is managed externally
    async def close(self):
        """Closes the underlying httpx client."""
        await self._client.aclose()

    # Mark method as async
    async def _make_request(self, endpoint: str) -> Optional[List[Dict]]:
        """Make HTTP request to FMP API with error handling."""
        request_endpoint = f"{self.base_url}/{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(request_endpoint)
                response.raise_for_status()
                
                data = response.json()
                
                # Handle API errors
                if isinstance(data, dict) and "Error Message" in data:
                    # Silent error - API returned error message
                    return None
                
                # Handle empty responses
                if isinstance(data, list) and len(data) == 0:
                    # Silent empty response - likely no data available
                    return None
                    
                # Handle unexpected response format
                if not isinstance(data, list):
                    # Silent error - unexpected response format
                    return None
                    
                return data
                
        except httpx.HTTPStatusError as e:
            # Silent HTTP error
            return None
        except httpx.RequestError as e:
            # Silent request error
            return None
        except Exception as e:
            # Silent unexpected error
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

        # Redis caching temporarily disabled to avoid dependency issues
        redis_client = None
        if not redis_client:
            # Direct fetch without caching
            api_data_list = await fetch_coroutine()
            if api_data_list is None: return None
            if not api_data_list: return []
            try:
                 return parse_obj_as(list_adapter.core_schema, api_data_list)
            except ValidationError as e:
                 # Silent validation error
                 return None

        cached_data_str = None
        try:
            cached_data_str = await redis_client.get(cache_key)
        except Exception as e:
            # Silent Redis error - proceed to fetch if Redis read fails
            pass

        if cached_data_str:
            # Cache hit - try to deserialize
            try:
                # Deserialize using TypeAdapter
                return list_adapter.validate_json(cached_data_str)
            except (ValidationError, json.JSONDecodeError) as e:
                # Silent cache validation error - fetch fresh data
                # Optionally delete invalid cache entry
                try:
                    await redis_client.delete(cache_key)
                except Exception:
                    pass

        # Cache miss - fetch fresh data
        api_data_list = await fetch_coroutine() # Call the original _make_request via lambda/partial

        if api_data_list is None: # API call failed
            return None
        if not api_data_list: # API call successful but returned empty list
            # Cache the empty list for a short time (e.g., 5 mins) to avoid hammering API for non-existent data?
            # For now, just return it without caching.
            return []

        # Parse/Validate data first to ensure it's valid before caching
        try:
            # Validate the raw list of dicts from API before caching
            parsed_data = parse_obj_as(list_adapter.core_schema, api_data_list)
            # Serialize the *validated* Pydantic list using TypeAdapter
            # dump_json returns bytes, decode to store as string in Redis
            data_to_cache_str = list_adapter.dump_json(parsed_data).decode('utf-8')
            try:
                await redis_client.set(cache_key, data_to_cache_str, ex=settings.cache_ttl_seconds)
                # Silent cache success
            except Exception as e:
                # Silent cache error
                pass
            
            return parsed_data # Return the validated Pydantic objects
        
        except ValidationError as e:
            # Silent validation error
            return None # Don't return or cache invalid data

    # Mark method as async
    async def get_income_statements(self, symbol: str, limit: int = 5, period: str = 'annual') -> Optional[List[IncomeStatementEntry]]:
        """Fetches income statements for a given stock symbol."""
        endpoint = f"/v3/income-statement/{symbol.upper()}"
        params = {'limit': limit, 'period': period}
        cache_key = f"fmp:{symbol.upper()}:{period}:{limit}:income"
        
        # Define the coroutine to fetch data if cache miss
        async def fetch(): 
            return await self._make_request(endpoint)
            
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
             return await self._make_request(endpoint)
             
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
            return await self._make_request(endpoint)

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

# FMP API client for fetching financial market data with caching support. 