import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Optional
# Assuming date field might be string or date object
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financials import CashFlowDB, IncomeStatementDB
from app.schemas.valuation import ValuationResponse
from app.domains.valuation.services.financials import get_stock_financials

logger = logging.getLogger(__name__)

# --- DCF Configuration ---
DISCOUNT_RATE = Decimal("0.09")  # Example WACC (9%)
TERMINAL_GROWTH_RATE = Decimal("0.025") # Example perpetual growth rate (2.5%)
PROJECTION_YEARS = 5 # Project FCF for 5 years
MIN_YEARS_FOR_GROWTH = 3 # Need at least 3 years of positive FCF to estimate growth


async def calculate_dcf_valuation(ticker: str, db: AsyncSession) -> ValuationResponse:
    """
    Calculates intrinsic value using a simple DCF model based on data in the DB.
    Fetches data using get_stock_financials if not present.
    Returns total value and per-share value if shares outstanding data is available.
    """
    ticker = ticker.upper()
    logger.info(f"Starting DCF valuation for {ticker}")

    # 1. Query historical cash flow data - Use 'date' and correct column names
    stmt_cf = (
        select(CashFlowDB.date, CashFlowDB.net_cash_from_operating, CashFlowDB.capital_expenditure)
        .where(CashFlowDB.ticker == ticker)
        .order_by(CashFlowDB.date.asc())
    )
    result_cf = await db.execute(stmt_cf)
    rows_cf = result_cf.all()

    # 2. Check if data exists, fetch if necessary
    if not rows_cf:
        logger.warning(f"No cash flow data found for {ticker} in DB. Fetching from FMP...")
        try:
            logger.info(f"Calling get_stock_financials for symbol: {ticker}")
            financials_response = await get_stock_financials(db, ticker)
            if not financials_response:
                # Handle case where fetching failed completely
                 logger.error(f"get_stock_financials returned None for {ticker}. Cannot proceed.")
                 return ValuationResponse(ticker=ticker, message="Failed to fetch required financial data.")

            logger.info(f"Finished get_stock_financials call for symbol: {ticker}")
            # Re-query after fetching
            result_cf = await db.execute(stmt_cf)
            rows_cf = result_cf.all()
            if not rows_cf:
                logger.error(f"Still no cash flow data found for {ticker} after FMP call.")
                return ValuationResponse(ticker=ticker, message="Data not found and could not be fetched.")
        except Exception as e:
            logger.error(f"Error during data fetch for {ticker}: {e}", exc_info=True)
            return ValuationResponse(ticker=ticker, message=f"Error fetching data: {e}")

    # 3. Calculate Historical Free Cash Flow (FCF)
    historical_fcf = {}
    for row in rows_cf:
        try:
            # Extract year from the date field
            row_date = row.date
            if isinstance(row_date, date_type):
                year = row_date.year
            elif isinstance(row_date, str) and len(row_date) >= 4:
                year = int(row_date[:4])
            else:
                 logger.warning(f"Could not determine year from date field '{row_date}' for {ticker}. Skipping row.")
                 continue

            # Use the correct attribute names from the row
            op_cf = Decimal(row.net_cash_from_operating or 0)
            cap_ex = Decimal(row.capital_expenditure or 0)
            fcf = op_cf + cap_ex
            historical_fcf[year] = fcf
        except (TypeError, ValueError, InvalidOperation) as e:
             logger.warning(f"Skipping FCF calculation for date {row.date} for {ticker} due to invalid numeric data: {e}")
             continue
        except Exception as e:
             logger.warning(f"Skipping FCF calculation for date {row.date} for {ticker} due to unexpected error: {e}")
             continue

    if not historical_fcf:
         return ValuationResponse(ticker=ticker, message="No valid historical cash flow data available to calculate FCF.")

    # 4. Estimate FCF Growth Rate
    sorted_years = sorted(historical_fcf.keys())
    positive_fcf_years = [yr for yr in sorted_years if historical_fcf.get(yr, 0) > 0]
    growth_rate = Decimal("0.05")
    if len(positive_fcf_years) >= MIN_YEARS_FOR_GROWTH:
        growth_rates = []
        relevant_years = sorted(positive_fcf_years[-(MIN_YEARS_FOR_GROWTH + 1):])
        for i in range(len(relevant_years) - 1):
            year1, year2 = relevant_years[i], relevant_years[i+1]
            fcf1, fcf2 = historical_fcf[year1], historical_fcf[year2]
            if fcf1 > 0:
                try:
                   rate = (fcf2 / fcf1) - 1
                   growth_rates.append(rate)
                except InvalidOperation:
                     logger.warning(f"Invalid growth calculation {ticker} {year1}->{year2}")
        if growth_rates:
            avg_growth = sum(growth_rates) / len(growth_rates)
            growth_rate = max(Decimal("0.00"), min(avg_growth, Decimal("0.20")))
            logger.info(f"Calculated FCF growth for {ticker}: {growth_rate:.2%}")
        else:
             logger.warning(f"No valid growth rates calculated for {ticker}, using default.")
    else:
        logger.warning(f"Insufficient positive FCF years ({len(positive_fcf_years)}) for {ticker}, using default growth.")

    # 5. Project Future FCFs
    projected_fcf = {}
    last_actual_year = sorted_years[-1]
    last_fcf = historical_fcf.get(last_actual_year)
    recent_positive_fcf = next((historical_fcf[yr] for yr in sorted(positive_fcf_years, reverse=True)), None)
    if last_fcf is None or last_fcf <= 0:
        if recent_positive_fcf:
            last_fcf = recent_positive_fcf
            logger.warning(f"Using most recent positive FCF ({last_fcf}) for {ticker} projection baseline.")
        else:
             logger.error(f"No positive historical FCF for {ticker}. Cannot perform DCF.")
             return ValuationResponse(ticker=ticker, message="No positive FCF available for projection.")
    current_fcf = last_fcf
    for i in range(1, PROJECTION_YEARS + 1):
        current_fcf *= (1 + growth_rate)
        projected_fcf[last_actual_year + i] = current_fcf

    # 6. Calculate PV of Projected FCFs
    pv_projected_fcf = Decimal("0.0")
    for i in range(1, PROJECTION_YEARS + 1):
        year = last_actual_year + i
        pv = projected_fcf[year] / ((1 + DISCOUNT_RATE) ** i)
        pv_projected_fcf += pv

    # 7. Calculate Terminal Value (TV) and its PV
    terminal_value = Decimal("0.0")
    pv_terminal_value = Decimal("0.0")
    final_projected_fcf = projected_fcf[last_actual_year + PROJECTION_YEARS]
    if DISCOUNT_RATE > TERMINAL_GROWTH_RATE:
        terminal_value = final_projected_fcf * (1 + TERMINAL_GROWTH_RATE) / (DISCOUNT_RATE - TERMINAL_GROWTH_RATE)
        pv_terminal_value = terminal_value / ((1 + DISCOUNT_RATE) ** PROJECTION_YEARS)
    else:
        logger.error(f"Discount rate <= terminal growth rate for {ticker}. Terminal value is invalid.")
        # Optionally return only PV of FCFs or error

    # 8. Calculate Total Intrinsic Value
    total_intrinsic_value = pv_projected_fcf + pv_terminal_value
    logger.info(f"Calculated total intrinsic value for {ticker}: {total_intrinsic_value:.2f}")

    # --- NEW: Fetch Shares Outstanding and Calculate Per Share Value --- 
    shares_outstanding = None
    intrinsic_value_per_share = None
    message = None

    try:
        # Query IncomeStatementDB for the most recent shares_outstanding
        stmt_shares = (
            select(IncomeStatementDB.shares_outstanding)
            .where(IncomeStatementDB.ticker == ticker)
            .order_by(IncomeStatementDB.date.desc()) # Most recent first
            .limit(1)
        )
        result_shares = await db.execute(stmt_shares)
        shares_row = result_shares.scalar_one_or_none()

        if shares_row is not None:
            # Use Decimal for precision, convert shares_row if it's float
            shares_outstanding_dec = Decimal(str(shares_row))
            if shares_outstanding_dec > 0:
                shares_outstanding = float(shares_outstanding_dec) # Store as float for response
                intrinsic_value_per_share_dec = total_intrinsic_value / shares_outstanding_dec
                # Round to sensible precision, e.g., 2 decimal places for currency
                intrinsic_value_per_share = float(intrinsic_value_per_share_dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                logger.info(f"Found shares outstanding for {ticker}: {shares_outstanding}. Per share value: {intrinsic_value_per_share:.2f}")
            else:
                logger.warning(f"Shares outstanding found for {ticker} but is zero or negative: {shares_row}")
                message = "Shares outstanding is zero or negative; cannot calculate per-share value."
        else:
            logger.warning(f"Could not find shares outstanding data for {ticker} in IncomeStatementDB.")
            message = "Shares outstanding data not found; cannot calculate per-share value."

    except Exception as e:
        logger.error(f"Error fetching or calculating shares outstanding for {ticker}: {e}", exc_info=True)
        message = "Error occurred while fetching shares outstanding."

    # Return the complete response
    return ValuationResponse(
        ticker=ticker,
        total_intrinsic_value=float(total_intrinsic_value),
        shares_outstanding=shares_outstanding,
        intrinsic_value_per_share=intrinsic_value_per_share,
        message=message
    )

# Example of how you might need to adjust get_stock_financials if it doesn't commit
# or if you need finer control (this part is hypothetical - adjust based on your actual financials service)
# async def ensure_financial_data(ticker: str, db: AsyncSession):
#     """Placeholder: checks if data exists, calls fetch if not."""
#     # Check if data exists first (e.g., check Company table or one of the statement tables)
#     # exists = await db.scalar(select(Company).where(Company.symbol == ticker))
#     # if not exists:
#     #     await get_stock_financials(ticker, db) # Assuming this fetches AND commits
#     pass 