"""
Database service layer: encapsulates all Motor/MongoDB queries used by the
route handlers, keeping route files thin.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
async def get_user_by_username(db: AsyncIOMotorDatabase, username: str) -> Optional[dict]:
    return await db["users"].find_one({"username": username})


async def get_user_by_email(db: AsyncIOMotorDatabase, email: str) -> Optional[dict]:
    return await db["users"].find_one({"email": email})


async def create_user(db: AsyncIOMotorDatabase, user_doc: Dict[str, Any]) -> str:
    user_doc["created_at"] = datetime.now(timezone.utc)
    result = await db["users"].insert_one(user_doc)
    return str(result.inserted_id)


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------
async def save_prediction(db: AsyncIOMotorDatabase, prediction_doc: Dict[str, Any]) -> str:
    prediction_doc["created_at"] = datetime.now(timezone.utc)
    result = await db["predictions"].insert_one(prediction_doc)
    return str(result.inserted_id)


async def get_user_predictions(
    db: AsyncIOMotorDatabase, user_id: str, limit: int = 50
) -> List[dict]:
    cursor = (
        db["predictions"]
        .find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def get_all_predictions(db: AsyncIOMotorDatabase, limit: int = 1000) -> List[dict]:
    cursor = db["predictions"].find({}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def get_analytics_aggregates(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """
    Runs aggregation pipelines to build the analytics dashboard payload:
    KPIs, hourly demand series, vehicle breakdown, and pickup hotspots.
    """
    total_rides = await db["predictions"].count_documents({})

    # --- KPI aggregates ---
    kpi_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$estimated_fare"},
                "avg_fare": {"$avg": "$estimated_fare"},
                "avg_cancel_prob": {"$avg": "$cancellation_probability"},
            }
        }
    ]
    kpi_cursor = db["predictions"].aggregate(kpi_pipeline)
    kpi_docs = await kpi_cursor.to_list(length=1)
    kpi = kpi_docs[0] if kpi_docs else {}

    # --- Hourly demand distribution ---
    hourly_pipeline = [
        {
            "$group": {
                "_id": "$derived_features.hour",
                "count": {"$sum": 1},
                "avg_demand_high": {
                    "$sum": {"$cond": [{"$eq": ["$demand_level", "High"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"_id": 1}},
    ]
    hourly_cursor = db["predictions"].aggregate(hourly_pipeline)
    hourly_docs = await hourly_cursor.to_list(length=24)

    # --- Vehicle type breakdown ---
    vehicle_pipeline = [
        {"$group": {"_id": "$vehicle_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    vehicle_cursor = db["predictions"].aggregate(vehicle_pipeline)
    vehicle_docs = await vehicle_cursor.to_list(length=20)

    # --- Demand level breakdown ---
    demand_pipeline = [
        {"$group": {"_id": "$demand_level", "count": {"$sum": 1}}},
    ]
    demand_cursor = db["predictions"].aggregate(demand_pipeline)
    demand_docs = await demand_cursor.to_list(length=10)

    # --- Pickup location hotspot breakdown (for Leaflet heatmap) ---
    location_pipeline = [
        {
            "$group": {
                "_id": "$pickup_location",
                "count": {"$sum": 1},
                "avg_fare": {"$avg": "$estimated_fare"},
            }
        },
        {"$sort": {"count": -1}},
    ]
    location_cursor = db["predictions"].aggregate(location_pipeline)
    location_docs = await location_cursor.to_list(length=20)

    cancellations = await db["predictions"].count_documents(
        {"cancellation_probability": {"$gte": 0.5}}
    )

    return {
        "total_rides": total_rides,
        "total_revenue": round(kpi.get("total_revenue", 0) or 0, 2),
        "avg_fare": round(kpi.get("avg_fare", 0) or 0, 2),
        "cancellation_rate": round(
            (cancellations / total_rides * 100) if total_rides else 0, 2
        ),
        "hourly_demand": [
            {"hour": h["_id"], "count": h["count"]} for h in hourly_docs if h["_id"] is not None
        ],
        "vehicle_breakdown": [
            {"vehicle_type": v["_id"], "count": v["count"]} for v in vehicle_docs
        ],
        "demand_breakdown": [
            {"demand_level": d["_id"], "count": d["count"]} for d in demand_docs
        ],
        "location_hotspots": [
            {
                "location": loc["_id"],
                "count": loc["count"],
                "avg_fare": round(loc["avg_fare"], 2),
            }
            for loc in location_docs
        ],
    }
