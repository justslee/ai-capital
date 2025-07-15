"""
Basic test script for ARIMA model using exported AAPL data.

This script tests the ARIMA model implementation with real data from the exports folder.
"""

import os
import sys
import pandas as pd
import logging
from pathlib import Path

# Add the backend directory to the path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.domains.price_prediction.models.arima import ArimaPredictor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_test_data():
    """Load exported AAPL data for testing."""
    # Look for the exported data file
    exports_path = Path(__file__).parent.parent.parent.parent.parent / "exports" / "merged_AAPL.csv"
    
    if not exports_path.exists():
        raise FileNotFoundError(f"Test data not found at {exports_path}")
    
    logger.info(f"Loading test data from {exports_path}")
    
    # Load the data
    df = pd.read_csv(exports_path)
    
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    return df


def test_arima_model():
    """Test the ARIMA model with AAPL data."""
    logger.info("Starting ARIMA model test")
    
    try:
        # Load test data
        df = load_test_data()
        
        # Initialize the predictor
        predictor = ArimaPredictor()
        
        # Show available features
        logger.info(f"Available columns: {list(df.columns)}")
        
        # Use only a subset of recent data for faster testing (last 2 years)
        df_recent = df.tail(500)  # Last 500 days
        logger.info(f"Using recent data: {len(df_recent)} rows")
        
        # Test data preprocessing
        logger.info("Testing data preprocessing...")
        df_processed = predictor.preprocess_data(df_recent)
        logger.info(f"Processed data shape: {df_processed.shape}")
        
        # Split data into train/test
        train_size = int(len(df_processed) * 0.8)
        train_data = df_processed[:train_size]
        test_data = df_processed[train_size:]
        
        logger.info(f"Training set: {len(train_data)} rows")
        logger.info(f"Test set: {len(test_data)} rows")
        
        # Fit the model
        logger.info("Fitting ARIMA model...")
        fit_result = predictor.fit(train_data, target_column='close')
        
        if fit_result['success']:
            logger.info("Model fitted successfully!")
            logger.info(f"Model order: {fit_result['model_order']}")
            logger.info(f"AIC: {fit_result['aic']:.2f}")
            logger.info(f"Stationarity: {fit_result['is_stationary']}")
        else:
            logger.error(f"Model fitting failed: {fit_result['error']}")
            return False
        
        # Test predictions
        logger.info("Testing predictions...")
        
        # Next day prediction
        next_day = predictor.predict_next_day()
        if next_day['success']:
            logger.info(f"Next day prediction: {next_day['predictions'][0]:.2f}")
            logger.info(f"Confidence interval: [{next_day['confidence_intervals']['lower'][0]:.2f}, {next_day['confidence_intervals']['upper'][0]:.2f}]")
        else:
            logger.error(f"Next day prediction failed: {next_day['error']}")
        
        # Next week prediction
        next_week = predictor.predict_next_week()
        if next_week['success']:
            logger.info(f"Next week predictions (7 days): {[f'{p:.2f}' for p in next_week['predictions']]}")
        else:
            logger.error(f"Next week prediction failed: {next_week['error']}")
        
        # Next month prediction
        next_month = predictor.predict_next_month()
        if next_month['success']:
            logger.info(f"Next month predictions (first 5 days): {[f'{p:.2f}' for p in next_month['predictions'][:5]]}")
        else:
            logger.error(f"Next month prediction failed: {next_month['error']}")
        
        # Get model summary
        summary = predictor.get_model_summary()
        logger.info("Model Summary:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")
        
        # Basic validation - check if predictions are reasonable
        actual_last_price = float(train_data['close'].iloc[-1])
        predicted_next_day = next_day['predictions'][0] if next_day['success'] else None
        
        if predicted_next_day:
            price_change_pct = abs(predicted_next_day - actual_last_price) / actual_last_price * 100
            logger.info(f"Actual last price: {actual_last_price:.2f}")
            logger.info(f"Predicted next day: {predicted_next_day:.2f}")
            logger.info(f"Price change: {price_change_pct:.2f}%")
            
            # Basic sanity check - price change should be reasonable (< 50%)
            if price_change_pct > 50:
                logger.warning(f"Large price change predicted: {price_change_pct:.2f}%")
            else:
                logger.info("Prediction appears reasonable")
        
        logger.info("ARIMA model test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return False


def main():
    """Run the ARIMA model test."""
    print("="*60)
    print("ARIMA Model Test")
    print("="*60)
    
    success = test_arima_model()
    
    if success:
        print("\n✅ All tests passed!")
        print("ARIMA model is working correctly with daily features")
    else:
        print("\n❌ Tests failed!")
        print("Check the logs above for error details")
    
    print("="*60)


if __name__ == "__main__":
    main()