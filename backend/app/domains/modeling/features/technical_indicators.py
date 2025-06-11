"""
Technical Indicators Feature Engineering

Generates technical analysis indicators for price prediction modeling.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TechnicalIndicatorsGenerator:
    """Generates technical indicators for stock price data."""
    
    def __init__(self):
        self.indicators = {
            "sma": self._calculate_sma,
            "ema": self._calculate_ema,
            "rsi": self._calculate_rsi,
            "macd": self._calculate_macd,
            "bollinger_bands": self._calculate_bollinger_bands,
            "volume_indicators": self._calculate_volume_indicators
        }
    
    def generate_features(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate technical indicator features from price data.
        
        Args:
            price_data: DataFrame with columns [date, open, high, low, close, volume]
            
        Returns:
            Dictionary containing calculated technical indicators
        """
        try:
            logger.info("Generating technical indicator features")
            
            features = {}
            
            # Calculate all technical indicators
            for indicator_name, calculator in self.indicators.items():
                try:
                    features[indicator_name] = calculator(price_data)
                    logger.debug(f"Successfully calculated {indicator_name}")
                except Exception as e:
                    logger.warning(f"Failed to calculate {indicator_name}: {e}")
                    features[indicator_name] = None
            
            return features
            
        except Exception as e:
            logger.error(f"Error generating technical indicators: {e}")
            return {}
    
    def _calculate_sma(self, data: pd.DataFrame, periods: List[int] = [5, 10, 20, 50, 200]) -> Dict[str, pd.Series]:
        """Calculate Simple Moving Averages."""
        sma_features = {}
        for period in periods:
            if len(data) >= period:
                sma_features[f"sma_{period}"] = data['close'].rolling(window=period).mean()
        return sma_features
    
    def _calculate_ema(self, data: pd.DataFrame, periods: List[int] = [12, 26, 50]) -> Dict[str, pd.Series]:
        """Calculate Exponential Moving Averages."""
        ema_features = {}
        for period in periods:
            if len(data) >= period:
                ema_features[f"ema_{period}"] = data['close'].ewm(span=period).mean()
        return ema_features
    
    def _calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate Relative Strength Index."""
        if len(data) < period + 1:
            return {"rsi": pd.Series(dtype=float)}
        
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {"rsi": rsi}
    
    def _calculate_macd(self, data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        if len(data) < slow:
            return {
                "macd_line": pd.Series(dtype=float),
                "macd_signal": pd.Series(dtype=float),
                "macd_histogram": pd.Series(dtype=float)
            }
        
        ema_fast = data['close'].ewm(span=fast).mean()
        ema_slow = data['close'].ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        macd_signal = macd_line.ewm(span=signal).mean()
        macd_histogram = macd_line - macd_signal
        
        return {
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_histogram": macd_histogram
        }
    
    def _calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        if len(data) < period:
            return {
                "bb_upper": pd.Series(dtype=float),
                "bb_middle": pd.Series(dtype=float),
                "bb_lower": pd.Series(dtype=float),
                "bb_width": pd.Series(dtype=float)
            }
        
        sma = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()
        
        bb_upper = sma + (std * std_dev)
        bb_lower = sma - (std * std_dev)
        bb_width = bb_upper - bb_lower
        
        return {
            "bb_upper": bb_upper,
            "bb_middle": sma,
            "bb_lower": bb_lower,
            "bb_width": bb_width
        }
    
    def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate volume-based indicators."""
        volume_features = {}
        
        # Volume Moving Average
        if len(data) >= 20:
            volume_features["volume_sma_20"] = data['volume'].rolling(window=20).mean()
        
        # Volume Rate of Change
        if len(data) >= 10:
            volume_features["volume_roc"] = data['volume'].pct_change(periods=10)
        
        # On-Balance Volume (OBV)
        obv = [0]
        for i in range(1, len(data)):
            if data['close'].iloc[i] > data['close'].iloc[i-1]:
                obv.append(obv[-1] + data['volume'].iloc[i])
            elif data['close'].iloc[i] < data['close'].iloc[i-1]:
                obv.append(obv[-1] - data['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        volume_features["obv"] = pd.Series(obv, index=data.index)
        
        return volume_features


# Service instance
technical_indicators_generator = TechnicalIndicatorsGenerator() 