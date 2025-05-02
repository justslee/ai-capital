import httpx
import asyncio
import json
from typing import Optional, List, Dict, Any
from pydantic import parse_obj_as, ValidationError, TypeAdapter, BaseModel
from functools import partial

# Ensure absolute imports from backend.app and point to config.py
from backend.app.config import settings # Corrected path
from backend.app.schemas.financials import (
    IncomeStatementEntry,
    BalanceSheetEntry,
    CashFlowEntry,
    FinancialsResponse,
    IncomeStatementListAdapter,
    BalanceSheetListAdapter,
    CashFlowListAdapter
)
from backend.app.core.cache import get_redis_client # This seems correct

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
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Optional[List[dict]]:
        """Helper method to make async GET requests to the FMP API."""
        if params is None:
            params = {}
        # API key added globally or per request depending on client setup
        params['apikey'] = self.api_key
        request_endpoint = endpoint.lstrip('/') # Use relative endpoint with base_url

        try:
            # Use the async client and await the response
            response = await self._client.get(request_endpoint, params=params)
            # Log the status code
            print(f"FMP API Request to {response.url} returned status code: {response.status_code}")
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'Error Message' in data:
                print(f"API Error for {response.url}: {data['Error Message']}")
                return None
            elif len(data) == 0: # Handle empty list response common with FMP
                print(f"Received empty list from {response.url}, likely no data for period/symbol.")
                return [] # Return empty list instead of None for clarity
            else:
                print(f"Unexpected response format from {response.url}: {data}")
                return None

        # Catch httpx specific exceptions
        except httpx.HTTPStatusError as e:
             print(f"HTTP Error for {e.request.url}: {e.response.status_code} - {e.response.text}")
             return None
        except httpx.RequestError as e:
            print(f"HTTP Request failed for {e.request.url}: {e}")
            return None
        except Exception as e:
            # Catch other potential errors (like JSON decoding)
            print(f"An error occurred during request to {request_endpoint}: {e}")
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

        redis_client = await get_redis_client()
        if not redis_client:
            print(f"Redis client unavailable, fetching {model_name} directly for {symbol}.")
            # Fallback to direct fetch if Redis is down
            api_data_list = await fetch_coroutine()
            if api_data_list is None: return None
            if not api_data_list: return []
            try:
                 return parse_obj_as(list_adapter.core_schema, api_data_list)
            except ValidationError as e:
                 print(f"Direct fetch data validation error for {model_name} ({symbol}): {e}")
                 return None

        cached_data_str = None
        try:
            cached_data_str = await redis_client.get(cache_key)
        except Exception as e:
            print(f"Redis GET error for key {cache_key}: {e}")
            # Proceed to fetch if Redis read fails

        if cached_data_str:
            print(f"Cache HIT for {cache_key}")
            try:
                # Deserialize using TypeAdapter
                return list_adapter.validate_json(cached_data_str)
            except (ValidationError, json.JSONDecodeError) as e:
                print(f"Cache data validation/decode error for {cache_key}: {e}. Fetching fresh data.")
                # Optionally delete invalid cache entry
                # try: await redis_client.delete(cache_key) except Exception as del_e: print(f"Failed to delete invalid cache key {cache_key}: {del_e}")

        # --- Cache MISS --- 
        print(f"Cache MISS for {cache_key}")
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
                print(f"Cached data for {cache_key} with TTL {settings.cache_ttl_seconds}s")
            except Exception as e:
                print(f"Redis SET error for key {cache_key}: {e}")
            
            return parsed_data # Return the validated Pydantic objects
        
        except ValidationError as e:
            print(f"Data validation error for {model_name} ({symbol}) after fetch: {e}")
            return None # Don't return or cache invalid data

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
    async def get_financials(self, symbol: str, limit: int = 5, period: str = 'annual') -> Optional[FinancialsResponse]:
        """Fetches all three primary financial statements for a symbol."""
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
             print(f"Failed to fetch one or more financial statements for {symbol}.")
             # Log specific errors if needed by checking exception types
             # e.g., if isinstance(income_statements, Exception): print(income_statements)
             return None

        return FinancialsResponse(
            income_statements=income_statements,
            balance_sheets=balance_sheets,
            cash_flows=cash_flows
        )

# Example of how to potentially use the client (can be imported elsewhere)
# async def main():
#     client = FMPClient()
#     try:
#         ticker = "AAPL"
#         financials = await client.get_financials(ticker, limit=3)
#         if financials:
#             print(f"Fetched financials for {ticker}:")
#             print("Income Statements:", len(financials.income_statements))
#             # print(financials.income_statements[0].model_dump_json(indent=2)) # Use model_dump_json in Pydantic v2
#             print("Balance Sheets:", len(financials.balance_sheets))
#             # print(financials.balance_sheets[0].model_dump_json(indent=2))
#             print("Cash Flows:", len(financials.cash_flows))
#             # print(financials.cash_flows[0].model_dump_json(indent=2))
#         else:
#             print(f"Could not fetch financials for {ticker}.")
#     finally:
#         await client.close() # Ensure client is closed

# if __name__ == "__main__":
#      asyncio.run(main()) 