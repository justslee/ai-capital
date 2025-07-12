"""
Modeling Domain Configuration

Configuration settings for the modeling domain including API keys,
data source settings, and market constants.
"""

import os
from typing import List, Optional, Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class ModelingConfig(BaseSettings):
    """Configuration for the modeling domain."""
    
    # Tiingo API Configuration
    tiingo_api_key: str = Field(..., env="TIINGO_API_KEY")
    tiingo_base_url: str = "https://api.tiingo.com/tiingo"
    
    # FMP API Configuration
    fmp_api_key: str = Field(..., env="FMP_API_KEY")
    
    # S3 Configuration
    s3_bucket: str = Field(..., alias="S3_BUCKET")
    s3_region: str = Field("us-east-1", alias="AWS_REGION")
    s3_access_key: str = Field(..., alias="AWS_ACCESS_KEY_ID")
    s3_secret_key: str = Field(..., alias="AWS_SECRET_ACCESS_KEY")
    
    # DuckDB Configuration
    duckdb_path: str = "./data/duckdb/market_data.db"
    
    @property
    def s3_credentials(self) -> Dict[str, str]:
        """Get S3 credentials as a dictionary."""
        return {
            "aws_access_key_id": self.s3_access_key,
            "aws_secret_access_key": self.s3_secret_key,
            "region_name": self.s3_region
        }
        
    class Config:
        """Pydantic config."""
        env_file = ".env"
        extra = 'ignore'  # Ignore extra fields from environment
        populate_by_name = True # Allow population by alias
    
    # Data validation settings
    max_price_threshold: float = 100000.0
    max_volume_threshold: int = 10_000_000_000
    default_lookback_days: int = 365 * 10  # 10 years default
    
    @property
    def sp100_tickers(self) -> List[str]:
        """Get S&P 100 ticker symbols."""
        return SP_100_TICKERS.copy()
    
    @property
    def sp500_tickers(self) -> List[str]:
        """Get S&P 500 ticker symbols."""
        return SP_500_TICKERS.copy()
    
    @property
    def major_indexes(self) -> List[str]:
        """Get major index symbols."""
        symbols = []
        for index_list in MAJOR_INDEXES.values():
            symbols.extend(index_list)
        return sorted(list(set(symbols)))
    
    @property
    def sector_etfs(self) -> List[str]:
        """Get sector ETF symbols."""
        symbols = []
        for sector_list in SECTOR_ETFS.values():
            symbols.extend(sector_list)
        return sorted(list(set(symbols)))

    def validate_required_fields(self) -> Dict[str, bool]:
        """
        Validate that all required fields are present.
        
        Returns:
            Dictionary mapping field names to validation status
        """
        results = super().validate_required_fields()
        
        # Check API keys (optional depending on usage)
        results["tiingo_api_key"] = bool(self.tiingo_api_key)
        results["fmp_api_key"] = bool(self.fmp_api_key)
        
        # Check S3 bucket name (required for S3 storage)
        results["s3_bucket"] = bool(self.s3_bucket)
        
        return results


# Market Constants and Lists
SP_100_TICKERS = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX", "ADBE",
    "CRM", "INTC", "CSCO", "ORCL", "IBM", "QCOM", "TXN", "AVGO", "AMD", "INTU",
    
    # Healthcare
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "TMO", "DHR", "BMY", "AMGN", "GILD",
    "CVS", "MDT", "ISRG", "VRTX", "REGN", "CI", "HUM", "ELV", "LLY",
    
    # Financial Services
    "JPM", "BAC", "WFC", "GS", "MS", "C", "AXP", "USB", "TFC", "PNC",
    "BLK", "SCHW", "CME", "ICE", "SPGI", "MCO", "AON", "MMC", "TRV", "PGR",
    
    # Consumer Discretionary
    "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "MAR", "GM", "F",
    "AMZN", "TSLA", "TGT", "COST", "WMT", "CVX", "XOM", "COP", "SLB", "OXY",
    
    # Consumer Staples & Other
    "KO", "PEP", "WMT", "PG", "JNJ", "KMB", "CL", "GIS", "K", "CPB",
    "MO", "PM", "KHC", "MDLZ", "HSY", "STZ", "TAP", "CAG", "SJM", "HRL",
    
    # Additional top companies
    "V", "MA", "PYPL", "DIS", "VZ", "T", "CMCSA", "NFLX", "CRM", "NOW"
]

# Remove duplicates and sort
SP_100_TICKERS = sorted(list(set(SP_100_TICKERS)))

# Complete S&P 500 ticker list (current as of 2024)
SP_500_TICKERS = [
    # All SP100 tickers are included in SP500
    *SP_100_TICKERS,
    
    # Additional SP500 companies not in SP100
    "A", "AAL", "AAP", "ABBV", "ABC", "ABMD", "ABT", "ACN", "ADBE", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG", "AKAM", "ALB", "ALGN", "ALK", "ALL", "ALLE", "AMAT", "AME", "AMGN", "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH", "APTV", "ARE", "ATO", "ATVI", "AVB", "AVGO", "AVY", "AWK", "AXP", "AZO", 
    "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF.B", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK", "BLL", "BMY", "BR", "BRK.B", "BRO", "BSX", "BWA", 
    "BXP", "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL", "CDAY", "CDNS", "CDW", "CE", "CEG", "CHTR", "CI", "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COST", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSX", "CTAS", "CTLT", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", 
    "D", "DAL", "DD", "DE", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DISH", "DLR", "DLTR", "DOV", "DOW", "DPZ", "DRE", "DRI", "DTE", "DUK", "DVA", "DVN", "DXC", "DXCM", 
    "EA", "EBAY", "ECL", "ED", "EFX", "EIX", "EL", "EMN", "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "ES", "ESS", "ETN", "ETR", "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", 
    "F", "FANG", "FAST", "FB", "FBHS", "FCX", "FDS", "FDX", "FE", "FFIV", "FIS", "FISV", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRC", "FRT", "FTNT", "FTV", 
    "GD", "GE", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", 
    "HAL", "HAS", "HBAN", "HBI", "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX", "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUM", "HWM", 
    "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INFO", "INTC", "INTU", "IP", "IPG", "IPGP", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", 
    "J", "JBHT", "JCI", "JKHY", "JNJ", "JNPR", "JPM", "JWN", 
    "K", "KEY", "KEYS", "KHC", "KIM", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KSS", 
    "L", "LDOS", "LEG", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNC", "LNT", "LOW", "LRCX", "LUMN", "LUV", "LVS", "LW", "LYB", "LYV", 
    "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NLOK", "NLSN", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL", "NWS", "NWSA", 
    "ODFL", "OKE", "OMC", "ORCL", "ORLY", "OTIS", "OXY", 
    "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEAK", "PEG", "PENN", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PKI", "PLD", "PM", "PNC", "PNR", "PNW", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PVH", "PWR", "PXD", "PYPL", 
    "QCOM", "QRVO", "RCL", "RE", "REG", "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY", 
    "SBAC", "SBNY", "SBUX", "SCHW", "SEDG", "SEE", "SHW", "SIVB", "SJM", "SLB", "SNA", "SNPS", "SO", "SPG", "SPGI", "SRE", "STE", "STT", "STX", "STZ", "SWK", "SWKS", "SYF", "SYK", "SYY", 
    "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT", "TJX", "TMO", "TMUS", "TPG", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TWTR", "TXN", "TXT", 
    "UAL", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VFC", "VICI", "VLO", "VMC", "VNO", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ", "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WM", "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", 
    "XEL", "XOM", "XRAY", "XYL", "YUM", "ZBH", "ZBRA", "ZION", "ZTS"
]

# Remove duplicates and sort  
SP_500_TICKERS = sorted(list(set(SP_500_TICKERS)))

# Major Market Indexes
MAJOR_INDEXES = {
    "SP500": ["SPY", "^GSPC"],           # S&P 500
    "NASDAQ": ["QQQ", "^IXIC", "^NDX"],  # NASDAQ
    "DOW": ["DIA", "^DJI"],              # Dow Jones
    "RUSSELL": ["IWM", "^RUT"],          # Russell 2000
    "VIX": ["^VIX"],                     # Volatility Index
}

# Sector ETFs for diversification  
SECTOR_ETFS = {
    "Technology": ["XLK", "VGT", "QTEC", "FTEC", "IYW", "SOXX", "SMH", "HACK", "ARKK", "ARKQ", "ARKW", "ARKG", "ARKF"],
    "Healthcare": ["XLV", "VHT", "IBB", "XBI", "LABU", "CURE", "PJP", "IHE", "BTEC", "SBIO"],
    "Financial": ["XLF", "VFH", "KBE", "KRE", "IAT", "FAS", "KBWB", "KBWR", "KBWP", "KBWD"],
    "Energy": ["XLE", "VDE", "OIH", "XOP", "GUSH", "ERX", "DRIP", "UCO", "SCO", "UNG", "BOIL", "KOLD"],
    "Materials": ["XLB", "VAW", "PICK", "COPX", "SIL", "PPLT", "PALL", "URA", "REMX", "PCEF"],
    "Industrials": ["XLI", "VIS", "ITB", "XHB", "PHO", "PXI", "XAR", "ITA", "JETS", "ROKT"],
    "Utilities": ["XLU", "VPU", "UTSL", "FUTY", "PUI", "FXU", "IDU", "JXI", "NEE", "FAN"],
    "Consumer_Discretionary": ["XLY", "VCR", "XRT", "RTH", "ONLN", "SOCK", "FDIS", "PEJ", "CARZ", "GAMR"],
    "Consumer_Staples": ["XLP", "VDC", "KXI", "FTAG", "PSCC", "BUYZ", "PBJ", "FDNM", "MOO", "WEAT"],
    "Real_Estate": ["XLRE", "VNQ", "IYR", "SCHH", "USRT", "FREL", "PSR", "ICF", "KBWY", "MORT"],
    "Communication": ["XLC", "VOX", "FCOM", "IYZ", "SOCL", "NETZ", "FIVG", "SKYY", "WCLD", "CLOU"],
}

# International & Emerging Market ETFs
INTERNATIONAL_ETFS = [
    # Broad International
    "VEA", "VWO", "VXUS", "FTIHX", "FXNAX", "FDVV", "IEFA", "IEMG", "IXUS", "SPDW", "SPEM",
    # Regional  
    "EFA", "EEM", "FXI", "MCHI", "ASHR", "KWEB", "YINN", "YANG", "EWJ", "EWZ", "EWY", "EWT", "EWG", "EWU", "EWC", "EWA", "EIS", "EWH", "EWS", "EWW", "EWI", "EWP", "EWL", "EWN", "EWO", "EWQ", "EWK", "EWD", "EPOL", "EPHE", "EPU", "EIDO", "INDA", "MINDX", "FLBR", "NORW", "EZU", "IEV", "VGK", "IEUR"
]

# Commodity & Currency ETFs
COMMODITY_ETFS = [
    # Precious Metals
    "GLD", "SLV", "IAU", "SGOL", "SIVR", "PPLT", "PALL", "GDX", "GDXJ", "SIL", "COPX", "PICK",
    # Energy/Oil
    "USO", "UNG", "UCO", "SCO", "BNO", "UGA", "BOIL", "KOLD", "NGAS", "OILU", "OILD",
    # Agriculture
    "DBA", "CORN", "SOYB", "WEAT", "CANE", "JO", "BAL", "COW", "TAGS", "MOO", "FTAG",
    # Broad Commodities
    "DJP", "GSG", "PDBC", "BCD", "USCI", "FTGC", "COMG", "USAG", "FTAG"
]

# Bond ETFs
BOND_ETFS = [
    # Government Bonds
    "TLT", "IEF", "SHY", "AGG", "BND", "GOVT", "SPTL", "SPTS", "SPTI", "VGIT", "VGLT", "VGSH",
    # Corporate Bonds  
    "LQD", "HYG", "JNK", "VCIT", "VCLT", "VCSH", "FALN", "FLOT", "IGLB", "IGIB", "IGSB",
    # International Bonds
    "BNDX", "VTEB", "MUB", "HYD", "PFF", "PFFD", "SPHY", "HYMB", "FLRN", "JPST", "MINT"
]

# NASDAQ 100 Components (Tech-heavy large caps)
NASDAQ_100_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "AVGO", "ORCL", "COST", "NFLX", "ADBE", "PEP", "ASML", "CSCO", "QCOM", "TMUS", "CMCSA", "AMAT", "INTC", "TXN", "AMGN", "INTU", "ISRG", "BKNG", "HON", "VRTX", "SBUX", "GILD", "ADP", "LRCX", "REGN", "PANW", "MU", "ADI", "PYPL", "MDLZ", "KLAC", "SNPS", "CDNS", "CRWD", "MRVL", "ORLY", "CTAS", "CHTR", "ABNB", "FTNT", "DDOG", "TEAM", "DXCM", "ADSK", "MNST", "FAST", "BIIB", "WDAY", "ODFL", "PAYX", "IDXX", "LULU", "CTSH", "VRSK", "ROST", "NXPI", "DLTR", "PCAR", "CPRT", "ALGN", "MCHP", "SGEN", "MRNA", "EBAY", "CSGP", "ILMN", "ANSS", "SIRI", "LCID", "ENPH", "BMRN", "SWKS", "DOCU", "MTCH", "SPLK", "FANG", "ROKU", "SMCI", "DKNG", "RIVN", "OKTA", "HOOD", "COIN", "RBLX", "GLPI", "MPWR", "NTES", "ZS", "VRSN", "MKTX", "TCOM", "NDAQ", "EXPE", "FOXA", "FOX"
]

# Russell 2000 (Small Cap) - Top 100 components by market cap
RUSSELL_2000_TICKERS = [
    "AMC", "BBBY", "CLOV", "WISH", "SPCE", "SNDL", "PLTR", "SOFI", "HOOD", "GME", "RIDE", "WKHS", "NKLA", "BLNK", "CHPT", "EVGO", "VLDR", "LAZR", "LIDR", "AEVA", "OUST", "SEER", "CRSP", "NTLA", "BEAM", "EDIT", "VERV", "BLUE", "RARE", "FOLD", "TGTX", "KPTI", "KURA", "MRTX", "CORT", "ETNB", "PRTA", "PTCT", "RGNX", "SGMO", "VCEL", "VCYT", "VIR", "VYGR", "XLRN", "XNCR", "ZYXI", "ALNY", "AMRN", "ARRY", "BGNE", "BMRN", "BNTX", "CRNX", "CRTX", "DNLI", "DVAX", "EXAS", "FATE", "FBIO", "FGEN", "GTHX", "HALO", "HZNP", "IMMU", "INCY", "IONS", "ITCI", "JAZZ", "LEGN", "LOXO", "MCRB", "MDGL", "MYGN", "NBIX", "NVCR", "NVTA", "OCRX", "PDCO", "PGEN", "PTGX", "RGEN", "SAGE", "SGEN", "SRPT", "TBPH", "TECH", "TPTX", "UTHR", "VCEL", "VRTX", "VYGR", "ZLAB", "ZYME", "ZYXI", "ALXN", "AMGN", "BIIB", "CELG", "GILD", "ILMN", "REGN", "VRTX"
]

# Popular Individual Stocks (beyond S&P 500)
POPULAR_STOCKS = [
    # Meme/Reddit Stocks
    "AMC", "GME", "BBBY", "WISH", "PLTR", "SPCE", "LCID", "RIVN", "SOFI", "HOOD", "COIN",
    # Crypto-related
    "MSTR", "RIOT", "MARA", "BTBT", "EBON", "CAN", "BITF", "HIVE", "HUT", "ARBK", "GREE",
    # Chinese ADRs
    "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "DIDI", "TME", "NTES", "WB", "VIPS",
    # Other Popular
    "TSLA", "RBLX", "SNAP", "UBER", "LYFT", "DOCU", "ZM", "PTON", "NKLA", "WKHS", "RIDE"
]

# Flatten all symbols for comprehensive coverage
ALL_SYMBOLS = SP_500_TICKERS.copy()
for index_list in MAJOR_INDEXES.values():
    ALL_SYMBOLS.extend(index_list)
for sector_list in SECTOR_ETFS.values():
    ALL_SYMBOLS.extend(sector_list)
ALL_SYMBOLS.extend(INTERNATIONAL_ETFS)
ALL_SYMBOLS.extend(COMMODITY_ETFS)
ALL_SYMBOLS.extend(BOND_ETFS)
ALL_SYMBOLS.extend(POPULAR_STOCKS)
ALL_SYMBOLS.extend(NASDAQ_100_TICKERS)
ALL_SYMBOLS.extend(RUSSELL_2000_TICKERS)

# Remove duplicates and sort
ALL_SYMBOLS = sorted(list(set(ALL_SYMBOLS)))

# Data validation settings
VALIDATION_RULES = {
    "min_price": 0.01,
    "max_price": 100000.0,
    "min_volume": 0,
    "max_volume": 10_000_000_000,
    "required_fields": ["date", "close"],
    "optional_fields": ["open", "high", "low", "volume", "adj_close"]
}


def get_modeling_config() -> ModelingConfig:
    """Get the modeling configuration instance."""
    return ModelingConfig()


def get_all_target_symbols() -> List[str]:
    """Get all symbols we want to track."""
    return ALL_SYMBOLS.copy()


def get_sp100_symbols() -> List[str]:
    """Get S&P 100 symbols."""
    return SP_100_TICKERS.copy()


def get_sp500_symbols() -> List[str]:
    """Get S&P 500 symbols."""
    return SP_500_TICKERS.copy()


def get_international_symbols() -> List[str]:
    """Get international ETF symbols."""
    return INTERNATIONAL_ETFS.copy()


def get_commodity_symbols() -> List[str]:
    """Get commodity ETF symbols."""
    return COMMODITY_ETFS.copy()


def get_bond_symbols() -> List[str]:
    """Get bond ETF symbols."""
    return BOND_ETFS.copy()


def get_popular_stocks() -> List[str]:
    """Get popular individual stock symbols."""
    return POPULAR_STOCKS.copy()


def get_nasdaq_100_symbols() -> List[str]:
    """Get NASDAQ 100 symbols."""
    return NASDAQ_100_TICKERS.copy()


def get_russell_2000_symbols() -> List[str]:
    """Get Russell 2000 (IWM) symbols."""
    return RUSSELL_2000_TICKERS.copy()


def get_comprehensive_symbols() -> List[str]:
    """Get all symbols for the most comprehensive dataset."""
    return ALL_SYMBOLS.copy()


def get_new_symbols_to_ingest(already_ingested: List[str]) -> List[str]:
    """Get symbols that haven't been ingested yet."""
    all_symbols = set(ALL_SYMBOLS)
    already_ingested_set = set(already_ingested)
    new_symbols = all_symbols - already_ingested_set
    return sorted(list(new_symbols))


def get_index_symbols() -> List[str]:
    """Get major index symbols."""
    symbols = []
    for index_list in MAJOR_INDEXES.values():
        symbols.extend(index_list)
    return sorted(list(set(symbols))) 