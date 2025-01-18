# web/app.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from datetime import datetime

from core.bess.battery_manager import BatteryManager
from core.bess.price_manager import ElectricityPriceManager, NordpoolAPISource, Spot56APISource


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

# Create battery and price manager instances
price_manager = ElectricityPriceManager(Spot56APISource())
battery_manager = BatteryManager()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}

class BatterySettings(BaseModel):
    totalCapacity: float
    reservedCapacity: float
    estimatedConsumption: float
    maxChargingPowerRate: float

@app.get("/api/battery/settings")
async def get_battery_settings():
    """Get current battery settings."""
    settings = battery_manager.get_battery_settings()
    return BatterySettings(**settings)

@app.post("/api/battery/settings")
async def update_battery_settings(settings: BatterySettings):
    """Update battery settings."""
    try:
        battery_manager.set_battery_settings(
            total_capacity=settings.totalCapacity,
            reserved_capacity=settings.reservedCapacity,
            estimated_consumption=settings.estimatedConsumption,
            max_charging_power_rate=settings.maxChargingPowerRate
        )
        return {"message": "Battery settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/battery/schedule-data")
async def get_schedule_data(
    estimated_consumption: float = Query(4.5, ge=0, le=15),
    max_charging_power_rate: float = Query(100.0, ge=0, le=100),
    date: str = Query(None, description="Date in YYYY-MM-DD format")
):
    """Get battery schedule data for dashboard."""
    try:
        # Parse the date parameter
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()

        prices = price_manager.get_prices(target_date)
        logger.debug(f"Prices fetched: {prices}")
        if not prices:
            logger.warning("No prices available for the selected date.")
            # Return empty data if no prices are available
            return []
        
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

        # Calculate totat charged and discharged energy
        total_charged = sum(1 for action in result["actions"] if action > 0)
        total_discharged = sum(1 for action in result["actions"] if action < 0)
        
        # Calculate total grid and battery costs
        total_grid_costs = sum(hour["grid_cost"] for hour in result["hourly_costs"])
        total_battery_costs = sum(hour["battery_cost"] for hour in result["hourly_costs"])

        return {
            "hourlyData": hourly_data,
            "summary": {
                "baseCost": float(result["base_cost"]),
                "optimizedCost": float(result["optimized_cost"]),
                "gridCosts": float(total_grid_costs),      
                "batteryCosts": float(total_battery_costs),
                "savings": float(result["cost_savings"]),
                "totalCharged": total_charged,
                "totalDischarged": total_discharged}
        }
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))
