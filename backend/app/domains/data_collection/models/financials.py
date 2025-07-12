from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import List, Optional
from pydantic import TypeAdapter
from datetime import date
from decimal import Decimal

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
    eps: Optional[float] = None
    epsdiluted: Optional[float] = None
    weighted_average_shs_out: Optional[float] = None
    weighted_average_shs_out_dil: Optional[float] = None # This maps to weightedAverageShsOutDil
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

class FinancialRatiosEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    symbol: str
    date: date
    period: str
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    days_of_sales_outstanding: Optional[float] = None
    days_of_inventory_outstanding: Optional[float] = None
    operating_cycle: Optional[float] = None
    days_of_payables_outstanding: Optional[float] = None
    cash_conversion_cycle: Optional[float] = None
    gross_profit_margin: Optional[float] = None
    operating_profit_margin: Optional[float] = None
    pretax_profit_margin: Optional[float] = None
    net_profit_margin: Optional[float] = None
    effective_tax_rate: Optional[float] = None
    return_on_assets: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_capital_employed: Optional[float] = None
    net_income_per_ebt: Optional[float] = None
    ebt_per_ebit: Optional[float] = None
    ebit_per_revenue: Optional[float] = None
    debt_ratio: Optional[float] = None
    debt_to_equity_ratio: Optional[float] = None
    long_term_debt_to_capitalization: Optional[float] = None
    total_debt_to_capitalization: Optional[float] = None
    interest_coverage: Optional[float] = None
    cash_flow_to_debt_ratio: Optional[float] = None
    company_equity_multiplier: Optional[float] = None
    receivables_turnover: Optional[float] = None
    payables_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    fixed_asset_turnover: Optional[float] = None
    asset_turnover: Optional[float] = None
    operating_cash_flow_per_share: Optional[float] = None
    free_cash_flow_per_share: Optional[float] = None
    cash_per_share: Optional[float] = None
    payout_ratio: Optional[float] = None
    operating_cash_flow_sales_ratio: Optional[float] = None
    free_cash_flow_operating_cash_flow_ratio: Optional[float] = None
    cash_flow_coverage_ratios: Optional[float] = None
    short_term_coverage_ratios: Optional[float] = None
    capital_expenditure_coverage_ratio: Optional[float] = None
    dividend_paid_and_capex_coverage_ratio: Optional[float] = None
    dividend_payout_ratio: Optional[float] = None
    price_book_value_ratio: Optional[float] = None
    price_to_book_ratio: Optional[float] = None
    price_to_sales_ratio: Optional[float] = None
    price_earnings_ratio: Optional[float] = None
    price_to_free_cash_flows_ratio: Optional[float] = None
    price_to_operating_cash_flows_ratio: Optional[float] = None
    price_cash_flow_ratio: Optional[float] = None
    price_earnings_to_growth_ratio: Optional[float] = None
    price_sales_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    enterprise_value_multiple: Optional[float] = None
    price_fair_value: Optional[float] = None

class KeyMetricsEntry(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    symbol: str
    date: date
    period: str
    revenue_per_share: Optional[float] = None
    net_income_per_share: Optional[float] = None
    operating_cash_flow_per_share: Optional[float] = None
    free_cash_flow_per_share: Optional[float] = None
    cash_per_share: Optional[float] = None
    book_value_per_share: Optional[float] = None
    tangible_book_value_per_share: Optional[float] = None
    shareholders_equity_per_share: Optional[float] = None
    interest_debt_per_share: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    pe_ratio: Optional[float] = None
    price_to_sales_ratio: Optional[float] = None
    pocf_ratio: Optional[float] = None
    pfcf_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ptb_ratio: Optional[float] = None
    ev_to_sales: Optional[float] = None
    enterprise_value_over_ebitda: Optional[float] = None
    ev_to_operating_cash_flow: Optional[float] = None
    ev_to_free_cash_flow: Optional[float] = None
    earnings_yield: Optional[float] = None
    free_cash_flow_yield: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    net_debt_to_ebitda: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    income_quality: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    sales_general_and_administrative_to_revenue: Optional[float] = None
    research_and_developement_to_revenue: Optional[float] = None
    intangibles_to_total_assets: Optional[float] = None
    capex_to_operating_cash_flow: Optional[float] = None
    capex_to_revenue: Optional[float] = None
    capex_to_depreciation: Optional[float] = None
    stock_based_compensation_to_revenue: Optional[float] = None
    graham_number: Optional[float] = None
    roic: Optional[float] = None
    return_on_tangible_assets: Optional[float] = None
    graham_net_net: Optional[float] = None
    working_capital: Optional[float] = None
    tangible_asset_value: Optional[float] = None
    net_current_asset_value: Optional[float] = None
    invested_capital: Optional[float] = None
    average_receivables: Optional[float] = None
    average_payables: Optional[float] = None
    average_inventory: Optional[float] = None
    days_sales_outstanding: Optional[float] = None
    days_payables_outstanding: Optional[float] = None
    days_of_inventory_on_hand: Optional[float] = None
    receivables_turnover: Optional[float] = None
    payables_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    capex_per_share: Optional[float] = None

# Define TypeAdapters for lists of models for efficient serialization/deserialization
IncomeStatementListAdapter = TypeAdapter(List[IncomeStatementEntry])
BalanceSheetListAdapter = TypeAdapter(List[BalanceSheetEntry])
CashFlowListAdapter = TypeAdapter(List[CashFlowEntry])
FinancialRatiosListAdapter = TypeAdapter(List[FinancialRatiosEntry])
KeyMetricsListAdapter = TypeAdapter(List[KeyMetricsEntry])

class FMPFundamentalsDataPoint(BaseModel):
    """
    Pydantic data class for FMP fundamentals data points.
    Used for data transfer and API responses.
    """
    ticker: str
    date: date
    period: str = "annual"
    
    # Valuation ratios
    pe_ratio: Optional[Decimal] = None
    pb_ratio: Optional[Decimal] = None
    ps_ratio: Optional[Decimal] = None
    pcf_ratio: Optional[Decimal] = None
    peg_ratio: Optional[Decimal] = None
    ev_to_sales: Optional[Decimal] = None
    ev_to_ebitda: Optional[Decimal] = None
    ev_to_operating_cash_flow: Optional[Decimal] = None
    ev_to_free_cash_flow: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    enterprise_value: Optional[Decimal] = None
    
    # Profitability ratios
    gross_profit_margin: Optional[Decimal] = None
    operating_profit_margin: Optional[Decimal] = None
    pretax_profit_margin: Optional[Decimal] = None
    net_profit_margin: Optional[Decimal] = None
    return_on_assets: Optional[Decimal] = None
    return_on_equity: Optional[Decimal] = None
    return_on_capital_employed: Optional[Decimal] = None
    return_on_invested_capital: Optional[Decimal] = None
    
    # Liquidity ratios
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    cash_ratio: Optional[Decimal] = None
    operating_cash_flow_per_share: Optional[Decimal] = None
    free_cash_flow_per_share: Optional[Decimal] = None
    
    # Leverage ratios
    debt_to_equity: Optional[Decimal] = None
    debt_to_assets: Optional[Decimal] = None
    net_debt_to_ebitda: Optional[Decimal] = None
    debt_to_capital: Optional[Decimal] = None
    debt_to_equity_capital: Optional[Decimal] = None
    interest_coverage: Optional[Decimal] = None
    cash_coverage: Optional[Decimal] = None
    
    # Efficiency ratios
    asset_turnover: Optional[Decimal] = None
    fixed_asset_turnover: Optional[Decimal] = None
    inventory_turnover: Optional[Decimal] = None
    receivables_turnover: Optional[Decimal] = None
    payables_turnover: Optional[Decimal] = None
    days_of_sales_outstanding: Optional[Decimal] = None
    days_of_inventory_outstanding: Optional[Decimal] = None
    days_of_payables_outstanding: Optional[Decimal] = None
    cash_conversion_cycle: Optional[Decimal] = None
    
    # Growth ratios
    revenue_growth: Optional[Decimal] = None
    epsgrowth: Optional[Decimal] = None
    operating_income_growth: Optional[Decimal] = None
    free_cash_flow_growth: Optional[Decimal] = None
    
    # Per share metrics
    book_value_per_share: Optional[Decimal] = None
    tangible_book_value_per_share: Optional[Decimal] = None
    shareholders_equity_per_share: Optional[Decimal] = None
    interest_debt_per_share: Optional[Decimal] = None
    market_cap_per_share: Optional[Decimal] = None
    enterprise_value_per_share: Optional[Decimal] = None
    
    # Additional metrics
    dividend_yield: Optional[Decimal] = None
    dividend_per_share: Optional[Decimal] = None
    dividend_payout_ratio: Optional[Decimal] = None
    shares_outstanding: Optional[Decimal] = None
    weighted_average_shares_outstanding: Optional[Decimal] = None
    weighted_average_shares_outstanding_dil: Optional[Decimal] = None
    earnings_per_share: Optional[Decimal] = None
    eps_diluted: Optional[Decimal] = None
    working_capital: Optional[Decimal] = None
    tangible_asset_value: Optional[Decimal] = None
    net_current_asset_value: Optional[Decimal] = None
    invested_capital: Optional[Decimal] = None
    average_receivables: Optional[Decimal] = None
    average_payables: Optional[Decimal] = None
    average_inventory: Optional[Decimal] = None 