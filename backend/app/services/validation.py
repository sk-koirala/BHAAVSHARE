"""
BhaavShare Prediction Validation Service.

Automatically checks the accuracy of LSTM forecasts by comparing 
predicted direction vs actual price movement on the subsequent trading day.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import entities as db_models
from app.services.forecasting import _fetch_history, FLAT_BAND

logger = logging.getLogger(__name__)

def run_prediction_validation(db: Session):
    """
    Find all pending predictions that reached their target date
     and validate them against actual price data.
    """
    logger.info("Starting prediction validation run...")
    
    # 1. Get all pending predictions where the predicted date is in the past
    # (Typically predicted_date is T+1 from created_at)
    pending = (
        db.query(db_models.PredictionLog)
        .filter(db_models.PredictionLog.validation_status == 'pending')
        .filter(db_models.PredictionLog.predicted_date <= datetime.utcnow().date())
        .all()
    )
    
    if not pending:
        logger.info("No pending predictions to validate.")
        return 0
    
    validated_count = 0
    for pred in pending:
        try:
            # Fetch history for the symbol
            df = _fetch_history(pred.symbol)
            
            # Find the close price on or immediately after the predicted_date
            # We look for the first candle where date >= predicted_date
            actual_row = df[df['date'].get('date', df['date']).dt.date >= pred.predicted_date].head(1)
            
            if actual_row.empty:
                # If we still don't have data (e.g. market holiday, data delay), skip it for now
                continue
                
            actual_close = float(actual_row['close'].iloc[0])
            prev_close = pred.latest_close # This was stored at prediction time
            
            if not prev_close:
                # Fallback: find the price at prediction time (created_at)
                pred_time_row = df[df['date'].get('date', df['date']).dt.date <= pred.created_at.date()].tail(1)
                if not pred_time_row.empty:
                    prev_close = float(pred_time_row['close'].iloc[0])
                else:
                    logger.warning(f"Could not find baseline price for {pred.symbol} prediction {pred.id}")
                    continue

            # Calculate actual direction
            return_pct = (actual_close - prev_close) / prev_close if prev_close else 0.0
            
            actual_dir = "FLAT"
            if return_pct > FLAT_BAND:
                actual_dir = "UP"
            elif return_pct < -FLAT_BAND:
                actual_dir = "DOWN"
            
            # Check correctness
            is_correct = (actual_dir == pred.predicted_direction)
            
            # Update prediction log
            pred.actual_close = actual_close
            pred.actual_direction = actual_dir
            pred.validation_status = 'correct' if is_correct else 'incorrect'
            pred.validated_at = datetime.utcnow()
            
            validated_count += 1
            
        except Exception as e:
            logger.error(f"Failed to validate prediction {pred.id} for {pred.symbol}: {e}")
            continue
            
    db.commit()
    logger.info(f"Successfully validated {validated_count} predictions.")
    return validated_count
