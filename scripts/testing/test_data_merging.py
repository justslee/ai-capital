import asyncio
import logging
import pandas as pd
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.domains.data_collection.services.data_merging_service import data_merging_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Suppress noisy loggers
logging.getLogger("s3transfer").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)


async def main():
    """
    Test the DataMergingService by fetching and merging data for a ticker.
    """
    ticker = "AAPL"
    logging.info(f"Starting test for ticker: {ticker}")

    # Get merged data (force refresh to test the whole pipeline)
    logging.info("Fetching merged data with force_refresh=True...")
    merged_df = await data_merging_service.get_merged_data(ticker=ticker, force_refresh=True)

    if merged_df is not None and not merged_df.empty:
        logging.info(f"Successfully retrieved merged data for {ticker}")
        logging.info(f"DataFrame shape: {merged_df.shape}")
        
        # --- Export to CSV ---
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        csv_path = os.path.join(export_dir, f"merged_{ticker}.csv")
        merged_df.to_csv(csv_path, index=False)
        logging.info(f"Successfully exported data to {csv_path}")
        # ---------------------

        logging.info("DataFrame columns:")
        for col in merged_df.columns:
            print(f"  - {col}")
        
        logging.info("DataFrame head:")
        print(merged_df.head().to_string())
        
        logging.info("DataFrame tail:")
        print(merged_df.tail().to_string())
        
        logging.info("Checking for NaN values in the last 5 rows...")
        print(merged_df.tail().isnull().sum())
    else:
        logging.error(f"Failed to retrieve merged data for {ticker}")

if __name__ == "__main__":
    # Pandas display options
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)
    
    asyncio.run(main()) 