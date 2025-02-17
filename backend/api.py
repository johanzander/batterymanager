"""FastAPI backend for BESS management."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from core.bess import BatterySystemManager
from core.bess.price_manager import NordpoolAPISource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create system manager instance with Nordpool API price source for backend
system = BatterySystemManager(controller=None, price_source=NordpoolAPISource())

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/settings/battery")
async def get_battery_settings():
    """Get current battery settings."""
    try:
        settings = system.get_settings()
        # Convert to old format for API compatibility
        return {
            "totalCapacity": settings["battery"]["totalCapacity"],
            "reservedCapacity": settings["battery"]["totalCapacity"] * (settings["battery"]["minSoc"] / 100),
            "estimatedConsumption": settings["consumption"]["defaultHourly"],
            "maxChargeDischarge": settings["battery"]["maxChargeRate"],
            "chargeCycleCost": settings["battery"]["chargeCycleCost"],
            "chargingPowerRate": settings["battery"]["chargingPowerRate"],
            "useActualPrice": settings["price"]["useActualPrice"]
        }
    except Exception as e:
        logger.error(f"Error getting battery settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/battery")
async def update_battery_settings(settings: dict):
    """Update battery settings."""
    try:
        # Convert from old format to new
        new_settings = {
            "battery": {
                "totalCapacity": settings["totalCapacity"],
                "minSoc": (settings["reservedCapacity"] / settings["totalCapacity"]) * 100,
                "maxChargeRate": settings["maxChargeDischarge"],
                "chargeCycleCost": settings["chargeCycleCost"],
                "chargingPowerRate": settings["chargingPowerRate"]
            },
            "consumption": {
                "defaultHourly": settings["estimatedConsumption"]
            },
            "price": {
                "useActualPrice": settings["useActualPrice"]
            }
        }
        
        system.update_settings(new_settings)
        return {"message": "Battery settings updated successfully"}
    except Exception as e:
        logger.error(f"Error updating battery settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/electricity")
async def get_electricity_price_settings():
    """Get current electricity price settings."""
    try:
        settings = system.get_settings()
        # Convert to old format for API compatibility
        return {
            "area": settings["price"]["area"],
            "markupRate": settings["price"]["markupRate"],
            "vatMultiplier": settings["price"]["vatMultiplier"],
            "additionalCosts": settings["price"]["additionalCosts"],
            "taxReduction": settings["price"]["taxReduction"]
        }
    except Exception as e:
        logger.error(f"Error getting electricity settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings/electricity")
async def update_electricity_price_settings(settings: dict):
    """Update electricity price settings."""
    try:
        # Convert from old format to new
        new_settings = {
            "price": {
                "area": settings["area"],
                "markupRate": settings["markupRate"],
                "vatMultiplier": settings["vatMultiplier"],
                "additionalCosts": settings["additionalCosts"],
                "taxReduction": settings["taxReduction"]
            }
        }
        
        system.update_settings(new_settings)
        return {"message": "Electricity settings updated successfully"}
    except Exception as e:
        logger.error(f"Error updating electricity settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule")
async def get_battery_schedule(
    date: str = Query(None, description="Date in YYYY-MM-DD format"),
):
    """Get battery schedule data for dashboard."""
    try:
        target_date = (
            datetime.strptime(date, "%Y-%m-%d").date()
            if date
            else datetime.now().date()
        )

        schedule = system.run_optimization(target_date)

        return schedule.get_schedule_data()
        
    except Exception as e:
        logger.error(f"Error getting battery schedule: {e}")
        raise HTTPException(status_code=501, detail=str(e))