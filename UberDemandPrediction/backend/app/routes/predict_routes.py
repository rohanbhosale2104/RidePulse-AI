"""
Prediction routes: run ML inference and expose prediction history.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user
from app.database.connection import get_database
from app.ml.predictor import ModelBundle, run_inference
from app.schemas.predict_schema import PredictionRequestSchema, PredictionResponseSchema
from app.services import db_service

router = APIRouter(tags=["Prediction"])


@router.post("/predict", response_model=PredictionResponseSchema)
async def predict(
    payload: PredictionRequestSchema,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    bundle = ModelBundle.instance()
    if not bundle.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded yet. Please try again shortly.",
        )

    try:
        result = run_inference(bundle, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference failed: {exc}",
        )

    prediction_doc = {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "vehicle_type": payload.vehicle_type.value,
        "pickup_location": payload.pickup_location.value,
        "drop_location": payload.drop_location.value,
        "payment_method": payload.payment_method.value,
        "ride_distance": payload.ride_distance,
        "avg_vtat": payload.avg_vtat,
        "avg_ctat": payload.avg_ctat,
        "driver_rating": payload.driver_rating,
        "customer_rating": payload.customer_rating,
        "date": payload.date,
        "time": payload.time,
        "demand_level": result["demand_level"],
        "demand_probabilities": result["demand_probabilities"],
        "estimated_fare": result["estimated_fare"],
        "cancellation_probability": result["cancellation_probability"],
        "driver_recommendation": result["driver_recommendation"],
        "derived_features": result["derived_features"],
    }
    inserted_id = await db_service.save_prediction(db, prediction_doc)

    from datetime import datetime, timezone

    return PredictionResponseSchema(
        id=inserted_id,
        demand_level=result["demand_level"],
        demand_probabilities=result["demand_probabilities"],
        estimated_fare=result["estimated_fare"],
        cancellation_probability=result["cancellation_probability"],
        driver_recommendation=result["driver_recommendation"],
        pickup_location=payload.pickup_location.value,
        drop_location=payload.drop_location.value,
        vehicle_type=payload.vehicle_type.value,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/history")
async def history(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
    limit: int = 50,
):
    docs = await db_service.get_user_predictions(db, current_user["user_id"], limit=limit)
    for d in docs:
        d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else d["created_at"]
    return {"count": len(docs), "predictions": docs}
