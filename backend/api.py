# web/app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging

from nordpool2 import fetch_nordpool_prices
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
        for hour in range(len(prices)):
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "price": float(prices[hour]["price"]),
                "batteryLevel": float(result["state_of_energy"][hour]),
                "action": float(result["actions"][hour]),
                "gridCost": float(result["hourly_costs"][hour]["grid_cost"]),
                "batteryCost": float(result["hourly_costs"][hour]["battery_cost"]),
                "totalCost": float(result["hourly_costs"][hour]["total_cost"]),
                "baseCost": float(result["hourly_costs"][hour]["base_cost"]),
                "savings": float(result["hourly_costs"][hour]["savings"])
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