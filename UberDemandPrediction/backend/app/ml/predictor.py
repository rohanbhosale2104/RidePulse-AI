"""
ML inference layer.

Loads `uber_demand_model.joblib` exactly ONCE at application startup and
exposes a singleton `ModelBundle` instance used by the prediction routes.

The joblib artifact is expected to be a dict with the keys:
    preprocessor    -> sklearn ColumnTransformer (StandardScaler + OneHotEncoder)
    demand_model    -> trained XGBoost multi-class classifier (0=Low,1=Medium,2=High)
    value_model     -> trained LightGBM regressor (fare)
    cancel_model    -> trained XGBoost binary classifier (cancellation probability)
    feature_names   -> list[str] raw feature columns expected by `preprocessor`
    demand_mapping  -> {0: "Low", 1: "Medium", 2: "High"}

NOTE: This module never retrains the model. It only loads and performs
inference on the pre-trained artifacts.
"""
import logging
from datetime import datetime
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd

from app.core.config import settings

logger = logging.getLogger("uvicorn")

PEAK_HOURS = set(range(7, 11)) | set(range(17, 21))  # 7-10 and 17-20 inclusive


class ModelBundle:
    """Singleton wrapper around the loaded joblib artifact."""

    _instance: "ModelBundle" = None

    def __init__(self):
        self.preprocessor = None
        self.demand_model = None
        self.value_model = None
        self.cancel_model = None
        self.feature_names = None
        self.demand_mapping = None
        self.loaded = False

    @classmethod
    def instance(cls) -> "ModelBundle":
        if cls._instance is None:
            cls._instance = ModelBundle()
        return cls._instance

    def load(self, model_path: str = None):
        """Load the joblib artifact into memory. Called once at startup."""
        path = model_path or settings.MODEL_PATH
        logger.info("Loading ML model artifact from: %s", path)
        try:
            artifact: Dict[str, Any] = joblib.load(path)
        except FileNotFoundError as exc:
            logger.error(
                "Model file not found at %s. Place your trained "
                "'uber_demand_model.joblib' inside the trained_models/ directory.",
                path,
            )
            raise exc

        self.preprocessor = artifact["preprocessor"]
        self.demand_model = artifact["demand_model"]
        self.value_model = artifact["value_model"]
        self.cancel_model = artifact["cancel_model"]
        self.feature_names = artifact["feature_names"]
        self.demand_mapping = artifact.get(
            "demand_mapping", {0: "Low", 1: "Medium", 2: "High"}
        )
        self.loaded = True
        logger.info(
            "Model artifact loaded successfully. Expected feature columns: %s",
            self.feature_names,
        )

    def is_ready(self) -> bool:
        return self.loaded


def _distance_category(distance: float) -> str:
    if distance <= 5:
        return "Short"
    elif distance <= 15:
        return "Medium"
    else:
        return "Long"


def engineer_features(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Derive time-based and distance-based features from the raw prediction
    payload, exactly matching what the model's preprocessor expects.
    """
    date_str = payload["date"]
    time_str = payload["time"]
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    hour = dt.hour
    day = dt.day
    month = dt.month
    weekday = dt.weekday()  # Monday=0 ... Sunday=6
    is_weekend = 1 if weekday >= 5 else 0
    is_peak_hour = 1 if hour in PEAK_HOURS else 0
    distance_category = _distance_category(payload["ride_distance"])

    row = {
        "Vehicle Type": payload["vehicle_type"],
        "Pickup Location": payload["pickup_location"],
        "Drop Location": payload["drop_location"],
        "Payment Method": payload["payment_method"],
        "Ride Distance": float(payload["ride_distance"]),
        "Avg VTAT": float(payload["avg_vtat"]),
        "Avg CTAT": float(payload["avg_ctat"]),
        "Driver Ratings": float(payload["driver_rating"]),
        "Customer Ratings": float(payload["customer_rating"]),
        "Hour": hour,
        "Day": day,
        "Month": month,
        "Weekday": weekday,
        "Is_Weekend": is_weekend,
        "Is_Peak_Hour": is_peak_hour,
        "Distance_Category": distance_category,
    }

    df = pd.DataFrame([row])
    return df, {
        "hour": hour,
        "day": day,
        "month": month,
        "weekday": weekday,
        "is_weekend": is_weekend,
        "is_peak_hour": is_peak_hour,
        "distance_category": distance_category,
    }


def _driver_recommendation(demand_label: str, cancel_prob: float, is_peak: bool) -> str:
    """Business-logic layer that turns model outputs into an actionable
    recommendation string for drivers."""
    if demand_label == "High" and cancel_prob < 0.3:
        base = "High demand & low cancellation risk — strongly recommended to accept and position nearby."
    elif demand_label == "High" and cancel_prob >= 0.3:
        base = "High demand but elevated cancellation risk — accept, but confirm rider promptly."
    elif demand_label == "Medium":
        base = "Moderate demand — a reasonable ride to accept, expect average wait times."
    else:
        base = "Low demand — consider repositioning towards a higher-demand zone."

    if is_peak:
        base += " Peak-hour surcharge may apply, maximizing earnings potential."
    return base


def run_inference(bundle: ModelBundle, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs the full inference pipeline:
      1. Feature engineering
      2. Preprocessing (ColumnTransformer)
      3. Demand classification (XGBoost)
      4. Fare regression (LightGBM)
      5. Cancellation probability (XGBoost binary)
      6. Derived driver recommendation
    """
    if not bundle.is_ready():
        raise RuntimeError("Model is not loaded yet.")

    df, derived = engineer_features(payload)

    # Reindex to the exact column order the preprocessor was fit on, if provided
    if bundle.feature_names:
        missing = [c for c in bundle.feature_names if c not in df.columns]
        if missing:
            raise ValueError(f"Missing engineered feature columns: {missing}")
        df = df[bundle.feature_names]

    X_transformed = bundle.preprocessor.transform(df)

    # --- Demand classification ---
    demand_pred = bundle.demand_model.predict(X_transformed)
    demand_class = int(np.ravel(demand_pred)[0])
    demand_label = bundle.demand_mapping.get(demand_class, str(demand_class))

    demand_proba = None
    if hasattr(bundle.demand_model, "predict_proba"):
        proba = bundle.demand_model.predict_proba(X_transformed)[0]
        demand_proba = {
            bundle.demand_mapping.get(i, str(i)): round(float(p), 4)
            for i, p in enumerate(proba)
        }

    # --- Fare regression ---
    fare_pred = float(np.ravel(bundle.value_model.predict(X_transformed))[0])
    fare_pred = max(0.0, round(fare_pred, 2))

    # --- Cancellation probability ---
    if hasattr(bundle.cancel_model, "predict_proba"):
        cancel_prob = float(bundle.cancel_model.predict_proba(X_transformed)[0][1])
    else:
        cancel_prob = float(np.ravel(bundle.cancel_model.predict(X_transformed))[0])
    cancel_prob = round(min(max(cancel_prob, 0.0), 1.0), 4)

    recommendation = _driver_recommendation(
        demand_label, cancel_prob, bool(derived["is_peak_hour"])
    )

    return {
        "demand_level": demand_label,
        "demand_class": demand_class,
        "demand_probabilities": demand_proba,
        "estimated_fare": fare_pred,
        "cancellation_probability": cancel_prob,
        "driver_recommendation": recommendation,
        "derived_features": derived,
    }
