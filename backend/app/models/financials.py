from sqlalchemy import Column, String, Float, Date, Integer, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .company import Company

class IncomeStatementDB(Base):
    """Model for income statements."""
    __tablename__ = "income_statements"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    period = Column(String, nullable=False)  # 'annual' or 'quarterly'
    
    # Income Statement items
    revenue = Column(Float)
    cost_of_revenue = Column(Float)
    gross_profit = Column(Float)
    rd_expenses = Column(Float)
    sga_expenses = Column(Float)
    operating_expenses = Column(Float)
    operating_income = Column(Float)
    interest_expense = Column(Float)
    ebt = Column(Float)  # Earnings Before Tax
    income_tax = Column(Float)
    net_income = Column(Float)
    eps = Column(Float)
    shares_outstanding = Column(Float)

    # Create a composite index for efficient lookups
    __table_args__ = (
        Index('idx_income_ticker_date_period', 'ticker', 'date', 'period', unique=True),
    )


class BalanceSheetDB(Base):
    """Model for balance sheets."""
    __tablename__ = "balance_sheets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    period = Column(String, nullable=False)  # 'annual' or 'quarterly'
    
    # Asset items
    cash_and_equivalents = Column(Float)
    short_term_investments = Column(Float)
    cash_and_short_term_investments = Column(Float)
    accounts_receivable = Column(Float)
    inventory = Column(Float)
    total_current_assets = Column(Float)
    property_plant_equipment = Column(Float)
    goodwill = Column(Float)
    intangible_assets = Column(Float)
    total_non_current_assets = Column(Float)
    total_assets = Column(Float)
    
    # Liability items
    accounts_payable = Column(Float)
    short_term_debt = Column(Float)
    total_current_liabilities = Column(Float)
    long_term_debt = Column(Float)
    total_non_current_liabilities = Column(Float)
    total_liabilities = Column(Float)
    
    # Equity items
    common_stock = Column(Float)
    retained_earnings = Column(Float)
    total_stockholders_equity = Column(Float)
    
    # Create a composite index for efficient lookups
    __table_args__ = (
        Index('idx_balance_ticker_date_period', 'ticker', 'date', 'period', unique=True),
    )


class CashFlowDB(Base):
    """Model for cash flow statements."""
    __tablename__ = "cash_flows"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(Date, nullable=False)
    period = Column(String, nullable=False)  # 'annual' or 'quarterly'
    
    # Operating activities
    net_income = Column(Float)
    depreciation_amortization = Column(Float)
    changes_in_working_capital = Column(Float)
    net_cash_from_operating = Column(Float)
    
    # Investing activities
    capital_expenditure = Column(Float)
    acquisitions = Column(Float)
    purchases_of_investments = Column(Float)
    sales_of_investments = Column(Float)
    net_cash_from_investing = Column(Float)
    
    # Financing activities
    debt_issuance = Column(Float)
    debt_repayment = Column(Float)
    share_issuance = Column(Float)
    share_repurchase = Column(Float)
    dividends_paid = Column(Float)
    net_cash_from_financing = Column(Float)
    
    # Summary
    net_change_in_cash = Column(Float)
    cash_at_beginning = Column(Float)
    cash_at_end = Column(Float)
    
    # Create a composite index for efficient lookups
    __table_args__ = (
        Index('idx_cashflow_ticker_date_period', 'ticker', 'date', 'period', unique=True),
    ) 