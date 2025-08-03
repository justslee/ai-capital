"""
Centralized Ticker Configuration

This module provides a unified system for managing ticker symbols across all data collection processes.
Focuses on major market indices and top ETFs - all on-demand ingestion.
"""

from enum import Enum
from typing import Dict, List, Set
from pydantic import BaseModel, Field
from functools import lru_cache


class TickerGroup(str, Enum):
    """Major market indices and ETF groups."""
    DOW = "dow"                     # Dow Jones Industrial Average
    SP500 = "sp500"                 # S&P 500
    NASDAQ = "nasdaq"               # NASDAQ 100
    RUSSELL2000 = "russell2000"     # Russell 2000
    TOP_ETFS = "top_etfs"          # Major index ETFs
    ALL = "all"                     # All available tickers


class TickerConfig(BaseModel):
    """Configuration for ticker-based data collection."""
    
    # Dow Jones Industrial Average (30 components)
    DOW_TICKERS: List[str] = Field(default=[
        "AAPL", "MSFT", "UNH", "GS", "HD", "CAT", "CRM", "AMGN", "MCD", "V",
        "BA", "HON", "AXP", "IBM", "JPM", "PG", "CVX", "JNJ", "WMT", "TRV",
        "MMM", "DIS", "NKE", "KO", "MRK", "CSCO", "VZ", "INTC", "WBA", "DOW"
    ])
    
    # S&P 500 - Full list from existing config
    SP500_TICKERS: List[str] = Field(default=[
        "A", "AAL", "AAP", "AAPL", "ABBV", "ABC", "ABMD", "ABT", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM", "ALB", "ALGN", "ALK", "ALL", "ALLE", "AMAT", "AME", "AMGN", "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV", "ARE", "ATO", "ATVI", "AVB", "AVGO", "AVY", "AWK", "AXP", "AZO",
        "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF.B", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK", "BLL", "BMY", "BR", "BRK.B", "BRO", "BSX", "BWA", "BXP",
        "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDAY", "CDNS", "CDW", "CE", "CEG", "CHTR", "CI", "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COST", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR",
        "D", "DAL", "DD", "DE", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DISH", "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRE", "DRI", "DTE", "DUK", "DVA", "DVN", "DXC", "DXCM",
        "EA", "EBAY", "ECL", "ED", "EFX", "EIX", "EL", "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "ES", "ESS", "ETN", "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR",
        "F", "FANG", "FAST", "FB", "FBHS", "FCX", "FDS", "FDX", "FE", "FFIV", "FIS", "FISV", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRC", "FRT", "FTNT", "FTV",
        "GD", "GE", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW",
        "HAL", "HAS", "HBAN", "HBI", "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUM", "HWM",
        "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INFO", "INTC", "INTU", "IP", "IPG", "IPGP", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ",
        "J", "JBHT", "JCI", "JKHY", "JNJ", "JNPR", "JPM", "JWN",
        "K", "KEY", "KEYS", "KHC", "KIM", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KSS",
        "L", "LDOS", "LEG", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX", "LUMN", "LUV", "LVS", "LW", "LYB", "LYV",
        "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU",
        "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NLOK", "NLSN", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL", "NWS", "NWSA",
        "ODFL", "OKE", "OMC", "ORCL", "ORLY", "OTIS", "OXY",
        "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEAK", "PEG", "PENN", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKI", "PLD", "PM", "PNC", "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PVH", "PWR", "PXD", "PYPL",
        "QCOM", "QRVO", "RCL", "RE", "REG", "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY",
        "SBAC", "SBNY", "SBUX", "SCHW", "SEDG", "SEE", "SHW", "SIVB", "SJM", "SLB", "SNA", "SNPS", "SO", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ", "SWK", "SWKS", "SYF", "SYK", "SYY",
        "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT", "TJX", "TMO", "TMUS", "TPG", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TWTR", "TXN", "TXT",
        "UAL", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB",
        "V", "VFC", "VICI", "VLO", "VMC", "VNO", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ",
        "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WM", "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN",
        "XEL", "XOM", "XRAY", "XYL",
        "YUM",
        "ZBH", "ZBRA", "ZION", "ZTS"
    ])
    
    # NASDAQ 100 - Tech-heavy large caps
    NASDAQ_TICKERS: List[str] = Field(default=[
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "AVGO", "ORCL", "COST", "NFLX", "ADBE", "PEP", "ASML", "CSCO", "QCOM", "TMUS", "CMCSA", "AMAT", "INTC", "TXN", "AMGN", "INTU", "ISRG", "BKNG", "HON", "VRTX", "SBUX", "GILD", "ADP", "LRCX", "REGN", "PANW", "MU", "ADI", "PYPL", "MDLZ", "KLAC", "SNPS", "CDNS", "CRWD", "MRVL", "ORLY", "CTAS", "CHTR", "ABNB", "FTNT", "DDOG", "TEAM", "DXCM", "ADSK", "MNST", "FAST", "BIIB", "WDAY", "ODFL", "PAYX", "IDXX", "LULU", "CTSH", "VRSK", "ROST", "NXPI", "DLTR", "PCAR", "CPRT", "ALGN", "MCHP", "SGEN", "MRNA", "EBAY", "CSGP", "ILMN", "ANSS", "SIRI", "LCID", "ENPH", "BMRN", "SWKS", "DOCU", "MTCH", "SPLK", "FANG", "ROKU", "SMCI", "DKNG", "RIVN", "OKTA", "HOOD", "COIN", "RBLX", "GLPI", "MPWR", "NTES", "ZS", "VRSN", "MKTX", "TCOM", "NDAQ", "EXPE", "FOXA", "FOX"
    ])
    
    # Russell 2000 - Small cap stocks (top 100 by market cap)
    RUSSELL2000_TICKERS: List[str] = Field(default=[
        "AMC", "BBBY", "CLOV", "WISH", "SPCE", "SNDL", "PLTR", "SOFI", "HOOD", "GME", "RIDE", "WKHS", "NKLA", "BLNK", "CHPT", "EVGO", "VLDR", "LAZR", "LIDR", "AEVA", "OUST", "SEER", "CRSP", "NTLA", "BEAM", "EDIT", "VERV", "BLUE", "RARE", "FOLD", "TGTX", "KPTI", "KURA", "MRTX", "CORT", "ETNB", "PRTA", "PTCT", "RGNX", "SGMO", "VCEL", "VCYT", "VIR", "VYGR", "XLRN", "XNCR", "ZYXI", "ALNY", "AMRN", "ARRY", "BGNE", "BMRN", "BNTX", "CRNX", "CRTX", "DNLI", "DVAX", "EXAS", "FATE", "FBIO", "FGEN", "GTHX", "HALO", "HZNP", "IMMU", "INCY", "IONS", "ITCI", "JAZZ", "LEGN", "LOXO", "MCRB", "MDGL", "MYGN", "NBIX", "NVCR", "NVTA", "OCRX", "PDCO", "PGEN", "PTGX", "RGEN", "SAGE", "SGEN", "SRPT", "TBPH", "TECH", "TPTX", "UTHR", "VCEL", "VRTX", "VYGR", "ZLAB", "ZYME", "ZYXI", "ALXN", "AMGN", "BIIB", "CELG", "GILD", "ILMN", "REGN", "VRTX"
    ])
    
    # Top Index ETFs
    TOP_ETFS: List[str] = Field(default=[
        # Broad Market ETFs
        "SPY", "VOO", "IVV",           # S&P 500 ETFs
        "QQQ", "QQQM",                 # NASDAQ 100 ETFs
        "DIA",                         # Dow Jones ETF
        "IWM", "VTWO",                 # Russell 2000 ETFs
        "VTI", "ITOT",                 # Total Stock Market ETFs
        
        # Sector ETFs
        "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLB", "XLU", "XLRE", "XLC",
        
        # International ETFs
        "VEA", "VWO", "IEFA", "EEM",
        
        # Bond ETFs
        "AGG", "BND", "TLT", "IEF", "SHY"
    ])
    
    def get_tickers_by_group(self, group: TickerGroup) -> List[str]:
        """Get tickers by predefined group."""
        if group == TickerGroup.DOW:
            return self.DOW_TICKERS.copy()
        elif group == TickerGroup.SP500:
            return self.SP500_TICKERS.copy()
        elif group == TickerGroup.NASDAQ:
            return self.NASDAQ_TICKERS.copy()
        elif group == TickerGroup.RUSSELL2000:
            return self.RUSSELL2000_TICKERS.copy()
        elif group == TickerGroup.TOP_ETFS:
            return self.TOP_ETFS.copy()
        elif group == TickerGroup.ALL:
            return self.get_all_active_tickers()
        else:
            return []
    
    def get_all_active_tickers(self) -> List[str]:
        """Get all tickers that should be actively monitored."""
        all_tickers = set()
        all_tickers.update(self.DOW_TICKERS)
        all_tickers.update(self.SP500_TICKERS)
        all_tickers.update(self.NASDAQ_TICKERS)
        all_tickers.update(self.RUSSELL2000_TICKERS)
        all_tickers.update(self.TOP_ETFS)
        return sorted(list(all_tickers))
    
    def get_group_info(self) -> Dict[str, Dict]:
        """Get information about all ticker groups."""
        info = {}
        for group in TickerGroup:
            if group != TickerGroup.ALL:
                tickers = self.get_tickers_by_group(group)
                info[group.value] = {
                    'count': len(tickers),
                    'sample_tickers': tickers[:5]  # Show first 5 as sample
                }
        return info
    
    def validate_ticker_symbol(self, symbol: str) -> bool:
        """Validate if a ticker symbol is in our system."""
        return symbol.upper() in self.get_all_active_tickers()


@lru_cache()
def get_ticker_config() -> TickerConfig:
    """Get a cached singleton instance of the ticker configuration."""
    return TickerConfig()


# Convenience functions for easy access
def get_dow_tickers() -> List[str]:
    """Get Dow Jones Industrial Average tickers."""
    return get_ticker_config().get_tickers_by_group(TickerGroup.DOW)


def get_sp500_tickers() -> List[str]:
    """Get S&P 500 tickers."""
    return get_ticker_config().get_tickers_by_group(TickerGroup.SP500)


def get_nasdaq_tickers() -> List[str]:
    """Get NASDAQ 100 tickers."""
    return get_ticker_config().get_tickers_by_group(TickerGroup.NASDAQ)


def get_russell2000_tickers() -> List[str]:
    """Get Russell 2000 tickers."""
    return get_ticker_config().get_tickers_by_group(TickerGroup.RUSSELL2000)


def get_top_etfs() -> List[str]:
    """Get top index ETFs."""
    return get_ticker_config().get_tickers_by_group(TickerGroup.TOP_ETFS)


def get_all_ticker_groups() -> List[TickerGroup]:
    """Get all available ticker groups."""
    return [group for group in TickerGroup if group != TickerGroup.ALL]