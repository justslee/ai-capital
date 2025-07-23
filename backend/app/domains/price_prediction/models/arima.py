"""ARIMA model implementation for stock price prediction using daily features."""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.stats.diagnostic import acorr_ljungbox
import warnings

# Suppress warnings from statsmodels
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)


class ArimaPredictor:
    """ARIMA-based price prediction model focusing on daily features only."""
    
    def __init__(self):
        self.model = None
        self.fitted_model = None
        self.is_fitted = False
        self.feature_columns = None
        self.target_column = 'close'
        
        self.daily_features = [
            'open', 'high', 'low', 'close', 'volume', 'adj_close',
            'sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_200',
            'ema_12', 'ema_26', 'ema_50',
            'rsi', 'macd_line', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'volume_sma_20', 'volume_roc', 'obv',
            'DGS10', 'DGS2', 'T10Y2Y', 'FEDFUNDS', 'VIXCLS', 'T10YIE'
        ]
        
        self.exclude_features = ['INDPRO', 'PAYEMS', 'GDP', 'UNRATE']
    
    def filter_daily_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter dataset to include only daily features."""
        # Get available daily features from the dataset
        available_features = [col for col in self.daily_features if col in df.columns]
        
        # Always include date and ticker if available
        essential_cols = []
        if 'date' in df.columns:
            essential_cols.append('date')
        if 'ticker' in df.columns:
            essential_cols.append('ticker')
        
        # Combine essential columns with available daily features, removing duplicates
        selected_columns = essential_cols + [col for col in available_features if col not in essential_cols]
        
        
        return df[selected_columns].copy()
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Preprocess data for ARIMA modeling."""
        # Filter to daily features only
        df_filtered = self.filter_daily_features(df)
        
        # Ensure date column is datetime
        if 'date' in df_filtered.columns:
            df_filtered['date'] = pd.to_datetime(df_filtered['date'])
            df_filtered = df_filtered.sort_values('date')
        
        # Forward fill missing values (appropriate for time series)
        df_filtered = df_filtered.fillna(method='ffill')
        
        # Drop any remaining NaN values
        df_filtered = df_filtered.dropna()
        
        
        return df_filtered
    
    def check_stationarity(self, series: pd.Series) -> bool:
        """Check if a time series is stationary using Augmented Dickey-Fuller test."""
        try:
            result = adfuller(series.dropna())
            p_value = result[1]
            
            # If p-value < 0.05, series is stationary
            is_stationary = p_value < 0.05
            
            
            return is_stationary
        except Exception as e:
            logger.warning(f"Stationarity test failed: {e}")
            return False
    
    def _find_best_arima_order(self, series: pd.Series) -> Tuple[int, int, int]:
        """Find the best ARIMA order using grid search and AIC."""
        best_aic = float('inf')
        best_order = (1, 1, 1)
        
        # Grid search for optimal parameters
        for p in range(0, 3):
            for d in range(0, 2):
                for q in range(0, 3):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except:
                        continue
        
        return best_order
    
    def fit(self, df: pd.DataFrame, target_column: str = 'close') -> Dict[str, Any]:
        """Fit ARIMA model to the data."""
        try:
            # Preprocess data
            df_processed = self.preprocess_data(df)
            
            # Extract target series
            if target_column not in df_processed.columns:
                raise ValueError(f"Target column '{target_column}' not found in data")
            
            target_series = df_processed[target_column]
            
            # Check stationarity
            is_stationary = self.check_stationarity(target_series)
            
            
            # Find best ARIMA order
            best_order = self._find_best_arima_order(target_series)
            
            # Fit the model with best parameters
            self.model = ARIMA(target_series, order=best_order)
            self.fitted_model = self.model.fit()
            self.is_fitted = True
            self.target_column = target_column
            
            # Get model parameters
            aic = self.fitted_model.aic
            
            
            return {
                'success': True,
                'model_order': best_order,
                'aic': aic,
                'n_observations': len(target_series),
                'target_column': target_column,
                'is_stationary': is_stationary
            }
            
        except Exception as e:
            logger.error(f"Failed to fit ARIMA model: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict(self, n_periods: int = 1) -> Dict[str, Any]:
        """Make predictions using the fitted ARIMA model."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before making predictions")
        
        try:
            forecast_result = self.fitted_model.get_forecast(steps=n_periods)
            
            predictions = forecast_result.predicted_mean
            conf_intervals = forecast_result.conf_int()
            
            if np.isscalar(predictions):
                predictions = [predictions]
            else:
                predictions = predictions.values
            
            results = {
                'success': True,
                'predictions': predictions.tolist() if hasattr(predictions, 'tolist') else predictions,
                'confidence_intervals': {
                    'lower': conf_intervals.iloc[:, 0].tolist(),
                    'upper': conf_intervals.iloc[:, 1].tolist()
                },
                'n_periods': n_periods,
                'target_column': self.target_column
            }
            
            
            return results
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def predict_next_day(self) -> Dict[str, Any]:
        """Predict next day price."""
        return self.predict(n_periods=1)
    
    def predict_next_week(self) -> Dict[str, Any]:
        """Predict next 7 days prices."""
        return self.predict(n_periods=7)
    
    def predict_next_month(self) -> Dict[str, Any]:
        """Predict next 30 days prices."""
        return self.predict(n_periods=30)
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of the fitted model."""
        if not self.is_fitted:
            return {'error': 'Model not fitted'}
        
        try:
            summary = {
                'model_order': self.fitted_model.model.order,
                'aic': self.fitted_model.aic,
                'target_column': self.target_column,
                'is_fitted': self.is_fitted,
                'n_daily_features': len(self.daily_features),
                'excluded_features': self.exclude_features
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get model summary: {e}")
            return {'error': str(e)}