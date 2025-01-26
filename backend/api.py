from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from core.bess.system_config import (
    BatterySettings,
    ElectricityPriceSettings,
)
from core.bess.battery_manager import BatteryManager
from core.bess.price_manager import ElectricityPriceManager, NordpoolAPISource

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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


@app.get("/api/settings/battery", response_model=BatterySettings)
async def get_battery_settings():
    """Get current battery settings."""
    settings_dict = battery_manager.get_settings()
    return BatterySettings(**settings_dict)

@app.post("/api/settings/battery")
async def update_battery_settings(settings: BatterySettings):
    """Update battery settings."""
    try:
        battery_manager.update_settings(
            use_actual_price=settings.useActualPrice,
            total_capacity=settings.totalCapacity,
            reserved_capacity=settings.reservedCapacity,
            estimated_consumption=settings.estimatedConsumption,
            max_charge_discharge=settings.maxChargeDischarge,
            charge_cycle_cost=settings.chargeCycleCost,
            charging_power_rate=settings.chargingPowerRate,
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
            area=settings.area,
            markup=settings.markupRate,
            vat=settings.vatMultiplier,
            additional_costs=settings.additionalCosts,
            tax_reduction=settings.taxReduction
        )
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

        prices = price_manager.get_prices(target_date)
        if not prices:
            logger.warning("No prices available for the selected date.")
            return []

        battery_manager.set_electricity_prices(prices)
        schedule = battery_manager.optimize_schedule()
        
        if not schedule:
            raise ValueError("Failed to create schedule")
            
        return schedule.get_schedule_data()
    except Exception as e:
        raise HTTPException(status_code=501, detail=str(e))
