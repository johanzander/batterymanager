# bess/__init__.py

"""Battery Energy Storage System (BESS) management package."""

# First import defaults since they're used by other modules
from .settings import *

# Internal components (not in __all__)
from .consumption_manager import ConsumptionManager
from .growatt_schedule import GrowattScheduleManager
from .battery_monitor import BatteryMonitor
from .power_monitor import HomePowerMonitor
from .price_manager import (
    ElectricityPriceManager,
    HANordpoolSource,
)
from .schedule import Schedule
from .ha_controller import HomeAssistantController

# Import facade last to avoid circular dependencies
from .system import BatterySystemManager

# Only expose what's needed for pyscript
__all__ = [
    'BatterySystemManager',   # Main facade for all operations
    'HomeAssistantController',  # Required for initial setup
]