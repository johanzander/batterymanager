# web/app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging

from .nordpool2 import fetch_nordpool_prices
from core.bess.bess import BatteryManager
from core.bess.schedule import Schedule

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

# Create a battery manager instance
battery_manager = BatteryManager()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/prices")
async def get_prices():
    """Get Nordpool prices."""
    prices = fetch_nordpool_prices()
    return {"prices": prices}

@app.get("/api/schedule/current")
async def get_current_schedule():
    """Get the current battery schedule."""
    try:
        schedule = battery_manager.get_schedule()
        return {
            "schedule": {
                "intervals": schedule.get_daily_intervals(),
                "total_charged_kwh": schedule.optimization_results.get("total_charged_kwh", 0),
                "total_discharged_kwh": schedule.optimization_results.get("total_discharged_kwh", 0),
                "cost_savings": schedule.optimization_results.get("cost_savings", 0),
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedule/optimize")
async def optimize_schedule(
    estimated_consumption: Optional[float] = 3.5,
    max_charging_power_rate: Optional[float] = 40.0
):
    """Generate new optimized schedule."""
    try:
        # Get prices for optimization
        prices = fetch_nordpool_prices()
        
        # Configure battery manager
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=estimated_consumption,
            max_charging_power_rate=max_charging_power_rate
        )
        
        # Generate schedule
        schedule = battery_manager.optimize_schedule()
        
        return {
            "schedule": {
                "intervals": schedule.get_daily_intervals(),
                "optimization_results": {
                    "base_cost": schedule.optimization_results["base_cost"],
                    "optimized_cost": schedule.optimization_results["optimized_cost"],
                    "cost_savings": schedule.optimization_results["cost_savings"],
                    "total_charged_kwh": schedule.optimization_results.get("total_charged_kwh", 0),
                    "total_discharged_kwh": schedule.optimization_results.get("total_discharged_kwh", 0),
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule/hourly/{hour}")
async def get_hourly_settings(hour: int):
    """Get settings for a specific hour."""
    try:
        if hour < 0 or hour > 23:
            raise HTTPException(status_code=400, detail="Hour must be between 0 and 23")
            
        schedule = battery_manager.get_schedule()
        settings = schedule.get_hour_settings(hour)
        
        return {
            "hour": hour,
            "settings": settings
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/battery/schedule-data")
async def get_schedule_data(
    estimated_consumption: float = Query(4.5, ge=0, le=15),
    max_charging_power_rate: float = Query(100.0, ge=0, le=100)
):
    """Get battery schedule data for dashboard."""
    try:
        prices = fetch_nordpool_prices()
        
        # Configure battery manager
        battery_manager.set_electricity_prices(prices)
        battery_manager.set_prediction_data(
            estimated_consumption_per_hour_kwh=estimated_consumption,
            max_charging_power_rate=max_charging_power_rate
        )
        
        # Generate schedule
        schedule = battery_manager.optimize_schedule()
        result = schedule.optimization_results
        
        # Create hourly data from optimization results
        hourly_data = []
        for hour, costs in enumerate(result["hourly_costs"]):
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "price": float(prices[hour]["price"]),
                "batteryLevel": float(result["state_of_energy"][hour]),
                "action": float(result["actions"][hour]),
                "gridUsed": float(4.5 + max(0, result["actions"][hour]))  # Base consumption + charging
            })

        # Calculate battery cycles (charging events)
        total_charged = sum(1 for action in result["actions"] if action > 0)

        return {
            "hourlyData": hourly_data,
            "summary": {
                "baseCost": float(result["base_cost"]),
                "optimizedCost": float(result["optimized_cost"]),
                "savings": float(result["cost_savings"]),
                "cycleCount": float(total_charged)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))