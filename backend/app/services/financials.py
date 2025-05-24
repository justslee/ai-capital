from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert # For upsert
from datetime import date as date_obj

# Ensure absolute imports from backend.app
from backend.app.services.fmp_client import FMPClient
from backend.app.schemas.financials import FinancialsResponse, IncomeStatementEntry, BalanceSheetEntry, CashFlowEntry
from backend.app.models.financials import IncomeStatementDB, BalanceSheetDB, CashFlowDB

async def get_stock_financials(
    db: AsyncSession, # Added db session parameter
    symbol: str,
    limit: int = 5,
    period: str = 'annual'
) -> Optional[FinancialsResponse]:
    """
    Service layer function to fetch and store financial statements for a stock symbol.
    Uses ON CONFLICT DO UPDATE (upsert) based on ticker, date, and period.
    """
    fmp_client = FMPClient()
    financials_api_response = None
    try:
        print(f"Fetching financials for {symbol} ({period}, limit={limit})...")
        financials_api_response = await fmp_client.get_financials(
            symbol=symbol, limit=limit, period=period
        )

        if not financials_api_response:
            print(f"Could not retrieve financials for {symbol} from FMPClient.")
            return None # Return None if API fetch fails

        print(f"Successfully fetched financials for {symbol}. Storing in DB...")

        # Prepare data for bulk upsert
        income_stmt_data = []
        balance_sheet_data = []
        cash_flow_data = []

        # --- Map Income Statements --- 
        for entry in financials_api_response.income_statements:
            # Map Pydantic schema fields to SQLAlchemy model columns
            # Be mindful of potential None values and type conversions
            stmt_dict = {
                "ticker": entry.symbol,
                "date": date_obj.fromisoformat(entry.date),
                "period": entry.period,
                "revenue": entry.revenue,
                "cost_of_revenue": entry.cost_of_revenue,
                "gross_profit": entry.gross_profit,
                "rd_expenses": entry.research_and_development_expenses,
                "sga_expenses": entry.selling_general_and_administrative_expenses,
                "operating_expenses": entry.operating_expenses,
                "operating_income": entry.operating_income_loss,
                "interest_expense": entry.interest_expense,
                "ebt": entry.income_before_tax,
                "income_tax": entry.income_tax_expense,
                "net_income": entry.net_income,
                # Map diluted shares from schema field to DB column
                "shares_outstanding": entry.weighted_average_shs_out_dil, # Use diluted
                "eps": entry.epsdiluted # Map diluted EPS as well if needed
            }
            income_stmt_data.append(stmt_dict)

        # --- Map Balance Sheets --- 
        for entry in financials_api_response.balance_sheets:
            stmt_dict = {
                "ticker": entry.symbol,
                "date": date_obj.fromisoformat(entry.date),
                "period": entry.period,
                "cash_and_equivalents": entry.cash_and_cash_equivalents,
                "short_term_investments": entry.short_term_investments,
                "cash_and_short_term_investments": entry.cash_and_short_term_investments,
                "accounts_receivable": entry.net_receivables, # Map name
                "inventory": entry.inventory,
                "total_current_assets": entry.total_current_assets,
                "property_plant_equipment": entry.property_plant_equipment_net, # Map name
                "goodwill": entry.goodwill,
                "intangible_assets": entry.intangible_assets,
                "total_non_current_assets": entry.total_non_current_assets,
                "total_assets": entry.total_assets,
                "accounts_payable": entry.account_payables, # Map name
                "short_term_debt": entry.short_term_debt,
                "total_current_liabilities": entry.total_current_liabilities,
                "long_term_debt": entry.long_term_debt,
                "total_non_current_liabilities": entry.total_non_current_liabilities,
                "total_liabilities": entry.total_liabilities,
                "common_stock": entry.common_stock,
                "retained_earnings": entry.retained_earnings,
                "total_stockholders_equity": entry.total_stockholders_equity
            }
            balance_sheet_data.append(stmt_dict)

        # --- Map Cash Flows --- 
        for entry in financials_api_response.cash_flows:
            stmt_dict = {
                "ticker": entry.symbol,
                "date": date_obj.fromisoformat(entry.date),
                "period": entry.period,
                "net_income": entry.net_income,
                "depreciation_amortization": entry.depreciation_and_amortization,
                "changes_in_working_capital": entry.change_in_working_capital,
                "net_cash_from_operating": entry.net_cash_provided_by_operating_activities,
                "capital_expenditure": entry.capital_expenditure,
                "acquisitions": entry.acquisitions_net,
                "purchases_of_investments": entry.purchases_of_investments,
                "sales_of_investments": entry.sales_maturities_of_investments,
                "net_cash_from_investing": entry.net_cash_used_for_investing_activites,
                "debt_issuance": entry.common_stock_issued, # Assuming FMP uses this field for debt issuance? Check API docs.
                "debt_repayment": entry.debt_repayment,
                "share_issuance": entry.common_stock_issued, # Map name
                "share_repurchase": entry.common_stock_repurchased, # Map name
                "dividends_paid": entry.dividends_paid,
                "net_cash_from_financing": entry.net_cash_used_provided_by_financing_activities,
                "net_change_in_cash": entry.net_change_in_cash,
                "cash_at_beginning": entry.cash_at_beginning_of_period,
                "cash_at_end": entry.cash_at_end_of_period
            }
            cash_flow_data.append(stmt_dict)

        # --- Perform Bulk Upserts --- 
        if income_stmt_data:
            await _bulk_upsert(db, IncomeStatementDB, income_stmt_data, ["ticker", "date", "period"])
            print(f"Upserted {len(income_stmt_data)} income statement records for {symbol}.")

        if balance_sheet_data:
            await _bulk_upsert(db, BalanceSheetDB, balance_sheet_data, ["ticker", "date", "period"])
            print(f"Upserted {len(balance_sheet_data)} balance sheet records for {symbol}.")
            
        if cash_flow_data:
            await _bulk_upsert(db, CashFlowDB, cash_flow_data, ["ticker", "date", "period"])
            print(f"Upserted {len(cash_flow_data)} cash flow records for {symbol}.")

        await db.commit()
        print(f"Database commit successful for {symbol}.")

    except Exception as e:
        print(f"Error in service layer processing financials for {symbol}: {e}")
        await db.rollback() # Rollback on error
        # Log the full traceback for debugging
        import traceback
        traceback.print_exc()
        return None # Indicate failure
    finally:
        # Ensure the client connection is closed regardless of DB operations
        await fmp_client.close()
        print(f"FMPClient closed for {symbol} request.")

    return financials_api_response # Return the original API response

async def _bulk_upsert(db: AsyncSession, model, data: list[dict], index_elements: list[str]):
    """Helper function for bulk upsert using INSERT ON CONFLICT DO UPDATE."""
    if not data:
        return

    stmt = pg_insert(model.__table__).values(data)
    
    # Map model attributes to table columns for the update part
    update_dict = { 
        col.name: col for col in stmt.excluded if col.name not in index_elements and col.name != 'id' 
        # Assuming 'id' is the primary key and should not be updated directly
    }
    
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=index_elements, # Columns forming the unique constraint/index
        set_=update_dict,
    )
    await db.execute(upsert_stmt)

# Example Usage (commented out) ...

# Example Usage (Requires running within an async context)
# import asyncio
#
# async def main():
#     aapl_financials = await get_stock_financials("AAPL", limit=2)
#     if aapl_financials:
#         print(f"AAPL Income Statements count: {len(aapl_financials.income_statements)}")
#         # Access data like: aapl_financials.income_statements[0].revenue
#     else:
#         print("Failed to get AAPL financials.")
#
# if __name__ == "__main__":
#     # Make sure .env is in the root relative to where this script might be run from
#     # Adjust path to .env loading if necessary
#     # from dotenv import load_dotenv
#     # load_dotenv()
#     asyncio.run(main()) 