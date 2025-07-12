
# TODO

This file will track the tasks for the AI agent.

## Task: Consolidate Ingestion Scripts

The goal of this task is to consolidate the various data ingestion scripts into a more unified and maintainable system. We have identified that `ingest_filings.py` is essential, but other scripts are either redundant or could be better integrated.

### Plan

1.  **[ ] Keep `backend/app/ingestion/ingest_filings.py`:** This script is unique and essential for ingesting SEC filings. We will keep it as the primary script for this purpose.
2.  **[ ] Delete `backend/scripts/ingestion/bulk_ticker_ingestion.py`:** This script is for bulk ingesting historical price data from Tiingo, which is also handled by `simple_bulk_ingest.py` and the data collection CLI. Its functionality is redundant.
3.  **[ ] Delete `backend/scripts/ingestion/simple_bulk_ingest.py`:** This is another script for ingesting price data. This functionality should be handled by the main data collection CLI (`backend/app/domains/data_collection/cli.py`), which already has a command for fetching daily prices.
4.  **[ ] Delete `scripts/summarizer/get_latest_filing.py`:** This is a simple utility script. Its functionality can be absorbed into other scripts or a more robust CLI if needed. It is not essential for the core data ingestion process.
5.  **[ ] Enhance `backend/app/domains/data_collection/cli.py`:** If necessary, we can add more commands or options to this CLI to cover any useful functionality from the deleted scripts. For now, we will focus on removing the redundant scripts.

## Review

_This section will be filled out after the tasks are completed, with a summary of the changes made._
