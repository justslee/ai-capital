"""
Service for ingesting financial statements from FMP.
"""
import asyncio
import logging
from typing import List

from ..clients.fmp_client import FMPClient, get_fmp_client
from ..storage.s3_storage_service import S3StorageService, get_s3_storage_service
from ..models.financials import IncomeStatementEntry, BalanceSheetEntry, CashFlowEntry

logger = logging.getLogger(__name__)

class FinancialStatementsService:
    """
    A service for fetching financial statements from FMP and storing them in S3.
    """

    def __init__(
        self,
        fmp_client: FMPClient = get_fmp_client(),
        s3_storage_service: S3StorageService = get_s3_storage_service(),
    ):
        self.fmp_client = fmp_client
        self.s3_storage_service = s3_storage_service

    async def ingest_financial_statements_for_ticker(self, ticker: str, limit: int = 5):
        """
        Fetches all available (annual and quarterly) financial statements for a ticker
        and saves them to S3.
        """
        logger.info(f"Starting financial statement ingestion for {ticker}.")

        statement_tasks = []
        periods = ["annual"] # Free tier only supports annual data
        
        for period in periods:
            # Fetching tasks
            income_task = self.fmp_client.get_income_statements(ticker, limit=limit, period=period)
            balance_sheet_task = self.fmp_client.get_balance_sheets(ticker, limit=limit, period=period)
            cash_flow_task = self.fmp_client.get_cash_flows(ticker, limit=limit, period=period)
            
            statement_tasks.extend([income_task, balance_sheet_task, cash_flow_task])

        results = await asyncio.gather(*statement_tasks, return_exceptions=True)
        
        # Process results and save to S3
        saving_tasks = []
        statement_types = ["income_statement", "balance_sheet", "cash_flow"]
        
        for i, result in enumerate(results):
            if isinstance(result, Exception) or result is None:
                logger.error(f"Failed to fetch data for task {i}: {result}")
                continue

            period_index = i // len(statement_types)
            statement_type_index = i % len(statement_types)
            
            period = periods[period_index]
            statement_type = statement_types[statement_type_index]
            
            # The result is a list of Pydantic models, convert to dicts for saving.
            data_to_save = [item.model_dump() for item in result]
            
            if data_to_save:
                saving_tasks.append(
                    self.s3_storage_service.save_fmp_financial_statement(
                        statement_data=data_to_save,
                        ticker=ticker,
                        statement_type=statement_type,
                    )
                )

        if saving_tasks:
            await asyncio.gather(*saving_tasks)
            logger.info(f"Successfully saved all financial statements for {ticker}.")
        else:
            logger.warning(f"No financial statement data was saved for {ticker}.")

_financial_statements_service = None

def get_financial_statements_service() -> "FinancialStatementsService":
    """Provides a singleton instance of the FinancialStatementsService."""
    global _financial_statements_service
    if _financial_statements_service is None:
        _financial_statements_service = FinancialStatementsService()
    return _financial_statements_service 