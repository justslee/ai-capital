import logging
import pandas as pd
from typing import Any, Dict, Optional

from app.domains.data_collection.services import get_data_collection_service
from app.domains.data_collection.storage.s3_storage_service import get_s3_storage_service
from app.domains.price_prediction.models.arima import ArimaPredictor
from app.shared.response_utils import error_response, success_response
from app.shared.singleton import get_singleton

logger = logging.getLogger(__name__)

class PricePredictionService:
    """Service for training models and generating stock price predictions."""

    def __init__(self):
        self.data_collection_service = get_data_collection_service()
        self.s3_storage = get_s3_storage_service()
        self.arima_predictor = ArimaPredictor()

    async def prepare_training_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Prepares training data for a ticker by fetching and processing it."""
        await self.data_collection_service.collect_daily_prices(ticker)
        price_df = await self.s3_storage.get_price_data(ticker)

        if price_df is None or price_df.empty:
            logger.warning(f"No price data available for {ticker} to prepare for training.")
            return None
        return price_df

    def train_model(self, data: pd.DataFrame, model_type: str = "arima") -> Dict[str, Any]:
        """Trains a model of a specified type."""
        if model_type.lower() == "arima":
            return self.arima_predictor.fit(data, target_column='close')
        
        logger.error(f"Unsupported model type for training: {model_type}")
        return error_response(f"Unsupported model type: {model_type}")

    def predict(self, ticker: str, days_ahead: int, model_type: str = "arima") -> Dict[str, Any]:
        """Makes a prediction using a trained model."""
        if model_type.lower() == "arima":
            if not self.arima_predictor.is_fitted:
                return error_response('ARIMA model is not fitted. Please train the model first.')
            return self.arima_predictor.predict(n_periods=days_ahead)

        logger.error(f"Unsupported model type for prediction: {model_type}")
        return error_response(f"Unsupported model type: {model_type}")
    
    async def train_and_predict(self, ticker: str, days_ahead: int, model_type: str = "arima") -> Dict[str, Any]:
        """Orchestrates the full train-and-predict pipeline."""
        training_data = await self.prepare_training_data(ticker)
        if training_data is None:
            return error_response(f'Failed to prepare training data for {ticker}')
        
        training_result = self.train_model(training_data, model_type)
        if not training_result.get('success'):
            return error_response(f'Model training failed: {training_result.get("error")}')
        
        prediction_result = self.predict(ticker, days_ahead, model_type)
        if not prediction_result.get('success'):
            return error_response(f'Prediction failed: {prediction_result.get("error")}')

        return success_response({
            'ticker': ticker,
            'model_type': model_type,
            'training_info': training_result.get('model_info', {}),
            'predictions': prediction_result.get('predictions', [])
        })

def get_price_prediction_service() -> PricePredictionService:
    """Provides a singleton instance of the PricePredictionService."""
    return get_singleton(PricePredictionService) 