"""Battery Energy Storage System (BESS) management package."""

# Define public API - only include what users should directly access
__all__ = [
    "BatterySystemManager",  # Main facade
    "HomeAssistantController",  # Used by pyscript integrations
    "BatterySettings",  # Public settings classes
    "HomeSettings",
    "ConsumptionSettings",
    "PriceSettings",
]

# Import settings used by other modules
from .settings import (  # noqa: I001
    BatterySettings,
    ConsumptionSettings,
    HomeSettings,
    PriceSettings,
)

# Import controller for Home Assistant integration
from .ha_controller import HomeAssistantController

# Import main facade class (the primary entry point to the system)
from .battery_system import BatterySystemManager
