import os
from fredapi import Fred
import pandas as pd

class FredClient:
    """
    A client for interacting with the Federal Reserve Economic Data (FRED) API.
    """
    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY")
        if not self.api_key:
            raise ValueError("FRED_API_KEY environment variable not set.")
        self.fred = Fred(api_key=self.api_key)

    def get_series(self, series_id: str) -> pd.DataFrame:
        """
        Fetches a time series from FRED.

        Args:
            series_id: The ID of the series to fetch (e.g., 'GDP').

        Returns:
            A pandas DataFrame containing the time series data.
        """
        series_data = self.fred.get_series(series_id)
        df = pd.DataFrame({series_id: series_data})
        df.index.name = 'date'
        return df

_fred_client = None

def get_fred_client() -> "FredClient":
    """Provides a singleton instance of the FredClient."""
    global _fred_client
    if _fred_client is None:
        _fred_client = FredClient()
    return _fred_client 