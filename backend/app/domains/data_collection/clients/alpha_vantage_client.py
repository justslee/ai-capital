# Standard library imports
import asyncio
import json
import logging
from typing import Optional, List, Dict, Any

# Third-party imports
import httpx
from pydantic import parse_obj_as, ValidationError, TypeAdapter, BaseModel

# App imports
from ..config import get_data_collection_config

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_API_BASE_URL = "https://www.alphavantage.co"

class AlphaVantageClient:
    _client: httpx.AsyncClient

    def __init__(self, api_key: Optional[str] = None, base_url: str = ALPHA_VANTAGE_API_BASE_URL):
        self.config = get_data_collection_config()
        self.api_key = api_key or self.config.alpha_vantage_api_key
        if not self.api_key:
            raise ValueError("Alpha Vantage API key is required. Set ALPHA_VANTAGE_API_KEY environment variable.")
        self.base_url = base_url.rstrip('/')
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self):
        """Closes the underlying httpx client."""
        await self._client.aclose()

    async def _make_request(self, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
        """Make HTTP request to Alpha Vantage API with error handling."""
        all_params = {"apikey": self.api_key, **(params or {})}

        try:
            logger.debug(f"Making request to Alpha Vantage with params: {params}")
            response = await self._client.get("/query", params=all_params)
            response.raise_for_status()
            
            data = response.json()
            
            if isinstance(data, dict) and ("Error Message" in data or "Information" in data):
                logger.warning(f"Alpha Vantage API error: {data.get('Error Message') or data.get('Information')}")
                return None
            
            if not isinstance(data, dict):
                logger.warning(f"Unexpected response format from Alpha Vantage: {type(data)}")
                return None
                
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for Alpha Vantage: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error for Alpha Vantage: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred for Alpha Vantage: {e}")
            return None

    async def get_news_sentiment(self, tickers: List[str]) -> Optional[Dict]:
        """Fetches news and sentiment data for a list of stock symbols."""
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ",".join(tickers),
            'limit': 200 # Default is 50, max is 1000, let's take a reasonable amount
        }
        
        return await self._make_request(params=params)

def get_alpha_vantage_client() -> "AlphaVantageClient":
    """Returns a singleton instance of the AlphaVantageClient."""
    # This is a simple implementation. For a more robust solution,
    # consider a more sophisticated singleton pattern or dependency injection.
    return AlphaVantageClient() 