"""
Valuation Service

This service performs company valuations, such as Discounted Cash Flow (DCF),
using the financial data collected by the data_collection domain.
"""
import logging
import pandas as pd
from typing import Optional, Dict, Any

from app.domains.data_collection.services import get_data_collection_service
from app.domains.data_collection.storage.s3_storage_service import get_s3_storage_service

logger = logging.getLogger(__name__)

class ValuationService:
    """A service for performing financial valuations."""

    def __init__(self):
        self.data_collection_service = get_data_collection_service()
        self.s3_storage_service = get_s3_storage_service()

    async def calculate_dcf(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Calculates the DCF valuation for a company.
        This is a simplified example and would need to be expanded with more
        sophisticated assumptions and calculations for real-world use.
        """

        # 1. Ensure fundamentals are collected
        await self.data_collection_service.collect_fundamentals(ticker)

        # 2. Get fundamentals from S3
        fundamentals_df = await self.s3_storage_service.get_fundamentals(ticker)
        if fundamentals_df is None or fundamentals_df.empty:
            logger.warning(f"No fundamentals data available for {ticker} to calculate DCF.")
            return None

        # 3. Perform a simplified DCF calculation
        # This is a highly simplified example. A real DCF model would be much more complex.
        try:
            # Get the most recent year's free cash flow
            latest_fcf = fundamentals_df.sort_values('date', ascending=False).iloc[0]['free_cash_flow_per_share']
            if latest_fcf <= 0:
                logger.warning(f"Cannot calculate DCF for {ticker} due to non-positive free cash flow.")
                return None

            # Simplified assumptions
            growth_rate = 0.05  # 5%
            discount_rate = 0.10 # 10%
            terminal_growth_rate = 0.02 # 2%
            projection_years = 5

            # Project future free cash flows
            future_fcf = [latest_fcf * (1 + growth_rate) ** (i + 1) for i in range(projection_years)]
            
            # Calculate present value of future cash flows
            pv_fcf = sum([fcf / (1 + discount_rate) ** (i + 1) for i, fcf in enumerate(future_fcf)])
            
            # Calculate terminal value
            terminal_value = (future_fcf[-1] * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)
            pv_terminal_value = terminal_value / (1 + discount_rate) ** projection_years
            
            # Calculate intrinsic value
            intrinsic_value = pv_fcf + pv_terminal_value

            return {
                "ticker": ticker,
                "intrinsic_value_per_share": round(intrinsic_value, 2),
                "assumptions": {
                    "latest_fcf_per_share": latest_fcf,
                    "growth_rate": growth_rate,
                    "discount_rate": discount_rate,
                    "terminal_growth_rate": terminal_growth_rate,
                }
            }

        except Exception as e:
            logger.error(f"Error during DCF calculation for {ticker}: {e}")
            return None

def get_valuation_service() -> ValuationService:
    """Provides a singleton instance of the ValuationService."""
    return ValuationService() 