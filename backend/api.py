from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from core.bess.system_config import (
    SystemConfig, 
    BatterySettings, 
    ElectricityPriceSettings,
    SYSTEM_CONFIG
)
from core.bess.battery_manager import BatteryManager
from core.bess.price_manager import ElectricityPriceManager, NordpoolAPISource, Guru56APISource

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

# Create instances
price_manager = ElectricityPriceManager(NordpoolAPISource())
battery_manager = BatteryManager()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/api/config", response_model=SystemConfig)
async def get_system_config():
    """Get complete system configuration including capabilities and default settings."""
    return SYSTEM_CONFIG

@app.get("/api/settings/battery", response_model=BatterySettings)
async def get_battery_settings():
    """Get current battery settings."""
    settings_dict = battery_manager.get_battery_settings()
    return BatterySettings(**settings_dict)

@app.post("/api/settings/battery")
async def update_battery_settings(settings: BatterySettings):
    """Update battery settings."""
    try:
        battery_manager.set_battery_settings(
            total_capacity=settings.totalCapacity,
            reserved_capacity=settings.reservedCapacity,
            estimated_consumption=settings.estimatedConsumption,
            max_charge_discharge=settings.maxChargeDischarge,
            charge_cycle_cost=settings.chargeCycleCost,
            charging_power_rate=settings.chargingPowerRate
        )
        return {"message": "Battery settings updated successfully"}
    except Exception as e:
        logger.error(f"Error updating battery settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/electricity", response_model=ElectricityPriceSettings)
async def get_electricity_price_settings():
    """Get current electricity price settings."""
    settings_dict = price_manager.get_settings()
    return ElectricityPriceSettings(**settings_dict)

@app.post("/api/settings/electricity")
async def update_electricity_price_settings(settings: ElectricityPriceSettings):
    """Update electricity price settings."""
    try:
        price_manager.update_settings(
            use_actual_price=settings.useActualPrice,
            markup=settings.markupRate,
            vat=settings.vatMultiplier,
            additional_costs=settings.additionalCosts,
            tax_reduction=settings.taxReduction,
            area=settings.area
        )
        return {"message": "Electricity settings updated successfully"}
    except Exception as e:
        logger.error(f"Error updating electricity settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule")
async def get_battery_schedule(
    date: str = Query(None, description="Date in YYYY-MM-DD format")
):
    """Get battery schedule data for dashboard."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()

        prices = price_manager.get_prices(target_date)
    #        logger.info(f"Prices: {prices}")
        if not prices:
            logger.warning("No prices available for the selected date.")
            return []
        
        battery_manager.set_electricity_prices(prices)
        schedule = battery_manager.optimize_schedule()
        result = schedule.optimization_results
        
        # Get price key based on electricity settings
        electricity_settings = price_manager.get_settings()
        price_key = 'buyPrice' if electricity_settings["useActualPrice"] else 'price'
        
        hourly_data = []
        for hour in range(len(prices)):
            hourly_data.append({
                "hour": f"{hour:02d}:00",
                "price": float(prices[hour][price_key]),
                "batteryLevel": float(result["state_of_energy"][hour]),
                "action": float(result["actions"][hour]),
                "gridCost": float(result["hourly_costs"][hour]["grid_cost"]),
                "batteryCost": float(result["hourly_costs"][hour]["battery_cost"]),
                "totalCost": float(result["hourly_costs"][hour]["total_cost"]),
                "baseCost": float(result["hourly_costs"][hour]["base_cost"]),
                "savings": float(result["hourly_costs"][hour]["savings"])
            })

        return {
            "hourlyData": hourly_data,
            "summary": {
                "baseCost": float(result["base_cost"]),
                "optimizedCost": float(result["optimized_cost"]),
                "gridCosts": sum(hour["gridCost"] for hour in hourly_data),
                "batteryCosts": sum(hour["batteryCost"] for hour in hourly_data),
                "savings": float(result["cost_savings"]),
                "totalCharged": sum(1 for action in result["actions"] if action > 0),
                "totalDischarged": sum(1 for action in result["actions"] if action < 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))