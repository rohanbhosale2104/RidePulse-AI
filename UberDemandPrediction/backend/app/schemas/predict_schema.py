"""
Pydantic schemas for the prediction endpoints.
"""
from datetime import date as date_type
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class VehicleType(str, Enum):
    uberx = "UberX"
    uberxl = "UberXL"
    uber_auto = "Uber Auto"
    uber_premier = "Uber Premier"
    uber_go = "Uber Go"


class LocationType(str, Enum):
    airport = "Airport"
    downtown = "Downtown"
    suburbs = "Suburbs"
    tech_park = "Tech Park"
    train_station = "Train Station"
    shopping_mall = "Shopping Mall"


class PaymentMethod(str, Enum):
    credit_card = "Credit Card"
    uber_cash = "Uber Cash"
    upi = "UPI"
    cash = "Cash"
    debit_card = "Debit Card"


class PredictionRequestSchema(BaseModel):
    vehicle_type: VehicleType
    pickup_location: LocationType
    drop_location: LocationType
    payment_method: PaymentMethod
    ride_distance: float = Field(..., gt=0, le=500)
    avg_vtat: float = Field(..., ge=0, le=120)
    avg_ctat: float = Field(..., ge=0, le=120)
    driver_rating: float = Field(..., ge=1, le=5)
    customer_rating: float = Field(..., ge=1, le=5)
    date: str
    time: str

    @field_validator("date")
    @classmethod
    def validate_date(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v):
        from datetime import datetime
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("time must be in HH:MM format")
        return v


class PredictionResponseSchema(BaseModel):
    id: str
    demand_level: str
    demand_probabilities: Optional[Dict[str, float]] = None
    estimated_fare: float
    cancellation_probability: float
    driver_recommendation: str
    pickup_location: str
    drop_location: str
    vehicle_type: str
    created_at: str
