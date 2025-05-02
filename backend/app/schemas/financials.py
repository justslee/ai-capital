from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import List, Optional
from pydantic import TypeAdapter

# Note: Fields are marked Optional as API responses might vary.
# Configure models to handle camelCase input from the API.

class IncomeStatementEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    date: str
    symbol: str
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    research_and_development_expenses: Optional[float] = None
    selling_general_and_administrative_expenses: Optional[float] = None
    operating_expenses: Optional[float] = None
    operating_income_loss: Optional[float] = None # EBIT
    interest_expense: Optional[float] = None
    income_before_tax: Optional[float] = None
    income_tax_expense: Optional[float] = None
    net_income: Optional[float] = None
    reported_currency: Optional[str] = None
    cik: Optional[str] = None
    filling_date: Optional[str] = None
    accepted_date: Optional[str] = None
    calendar_year: Optional[str] = None
    period: Optional[str] = None
    link: Optional[str] = None
    final_link: Optional[str] = None


class BalanceSheetEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    date: str
    symbol: str
    cash_and_cash_equivalents: Optional[float] = None
    short_term_investments: Optional[float] = None
    cash_and_short_term_investments: Optional[float] = None
    net_receivables: Optional[float] = None
    inventory: Optional[float] = None
    total_current_assets: Optional[float] = None
    property_plant_equipment_net: Optional[float] = None
    goodwill: Optional[float] = None
    intangible_assets: Optional[float] = None
    goodwill_and_intangible_assets: Optional[float] = None
    long_term_investments: Optional[float] = None
    tax_assets: Optional[float] = None
    total_non_current_assets: Optional[float] = None
    total_assets: Optional[float] = None
    account_payables: Optional[float] = None
    short_term_debt: Optional[float] = None
    tax_payables: Optional[float] = None
    deferred_revenue: Optional[float] = None
    total_current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    deferred_revenue_non_current: Optional[float] = None
    deferred_tax_liabilities_non_current: Optional[float] = None
    total_non_current_liabilities: Optional[float] = None
    total_liabilities: Optional[float] = None
    common_stock: Optional[float] = None
    retained_earnings: Optional[float] = None
    accumulated_other_comprehensive_income_loss: Optional[float] = None
    othertotal_stockholders_equity: Optional[float] = Field(None, alias='otherTotalStockholdersEquity')
    total_stockholders_equity: Optional[float] = None
    total_equity: Optional[float] = None
    total_liabilities_and_stockholders_equity: Optional[float] = None
    minority_interest: Optional[float] = None
    total_liabilities_and_total_equity: Optional[float] = None
    total_investments: Optional[float] = None
    total_debt: Optional[float] = None
    net_debt: Optional[float] = None
    reported_currency: Optional[str] = None
    cik: Optional[str] = None
    filling_date: Optional[str] = None
    accepted_date: Optional[str] = None
    calendar_year: Optional[str] = None
    period: Optional[str] = None
    link: Optional[str] = None
    final_link: Optional[str] = None


class CashFlowEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    date: str
    symbol: str
    net_income: Optional[float] = None
    depreciation_and_amortization: Optional[float] = None
    deferred_income_tax: Optional[float] = None
    stock_based_compensation: Optional[float] = None
    change_in_working_capital: Optional[float] = None
    accounts_receivables: Optional[float] = None # Often negative indicates increase
    inventory: Optional[float] = None # Often negative indicates increase
    accounts_payables: Optional[float] = None # Often positive indicates increase
    other_working_capital: Optional[float] = None
    other_non_cash_items: Optional[float] = None
    net_cash_provided_by_operating_activities: Optional[float] = None # Operating Cash Flow
    investments_in_property_plant_and_equipment: Optional[float] = None # Often negative CapEx
    acquisitions_net: Optional[float] = None
    purchases_of_investments: Optional[float] = None
    sales_maturities_of_investments: Optional[float] = None
    other_investing_activites: Optional[float] = None
    net_cash_used_for_investing_activites: Optional[float] = None # Investing Cash Flow
    debt_repayment: Optional[float] = None
    common_stock_issued: Optional[float] = None
    common_stock_repurchased: Optional[float] = None
    dividends_paid: Optional[float] = None
    other_financing_activites: Optional[float] = None
    net_cash_used_provided_by_financing_activities: Optional[float] = None # Financing Cash Flow
    effect_of_forex_changes_on_cash: Optional[float] = None
    net_change_in_cash: Optional[float] = None
    cash_at_end_of_period: Optional[float] = None
    cash_at_beginning_of_period: Optional[float] = None
    operating_cash_flow: Optional[float] = None # Often same as net_cash_provided_by_operating_activities
    capital_expenditure: Optional[float] = None # Usually derived or same as investments_in_property_plant_and_equipment (absolute value)
    free_cash_flow: Optional[float] = None # OCF - CapEx
    reported_currency: Optional[str] = None
    cik: Optional[str] = None
    filling_date: Optional[str] = None
    accepted_date: Optional[str] = None
    calendar_year: Optional[str] = None
    period: Optional[str] = None
    link: Optional[str] = None
    final_link: Optional[str] = None


class FinancialsResponse(BaseModel):
    income_statements: List[IncomeStatementEntry]
    balance_sheets: List[BalanceSheetEntry]
    cash_flows: List[CashFlowEntry]

# Define TypeAdapters for lists of models for efficient serialization/deserialization
IncomeStatementListAdapter = TypeAdapter(List[IncomeStatementEntry])
BalanceSheetListAdapter = TypeAdapter(List[BalanceSheetEntry])
CashFlowListAdapter = TypeAdapter(List[CashFlowEntry]) 