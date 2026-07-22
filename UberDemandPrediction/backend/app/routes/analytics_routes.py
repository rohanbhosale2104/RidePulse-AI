"""
Analytics routes: aggregate statistics for Chart.js and Leaflet.js.
"""
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import get_current_user
from app.database.connection import get_database
from app.services import db_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Approximate lat/lng centroids used to plot pickup hotspots on the Leaflet map.
# In production these would come from real geocoding of ride pickup points.
LOCATION_COORDINATES = {
    "Airport": [12.9500, 77.6683],
    "Downtown": [12.9716, 77.5946],
    "Suburbs": [12.9250, 77.5000],
    "Tech Park": [12.9352, 77.6146],
    "Train Station": [12.9767, 77.5713],
    "Shopping Mall": [12.9345, 77.6100],
}


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    aggregates = await db_service.get_analytics_aggregates(db)

    # Attach map coordinates to each hotspot location
    hotspots_with_coords = []
    for loc in aggregates["location_hotspots"]:
        coords = LOCATION_COORDINATES.get(loc["location"])
        if coords:
            hotspots_with_coords.append(
                {
                    "location": loc["location"],
                    "count": loc["count"],
                    "avg_fare": loc["avg_fare"],
                    "lat": coords[0],
                    "lng": coords[1],
                }
            )
    aggregates["location_hotspots"] = hotspots_with_coords

    return aggregates
