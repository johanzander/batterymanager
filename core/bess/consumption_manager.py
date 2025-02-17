"""Module for predicting and managing home energy consumption data.

The module tracks actual consumption values and provides predictions for future hours.
It considers both grid consumption and battery energy changes when calculating total
household consumption.

Key features:
- Tracks actual consumption values with battery state changes
- Provides hourly consumption predictions
- Updates predictions based on recent consumption patterns
- Manages daily resets and data validation
"""

import logging
from datetime import datetime
from .settings import ConsumptionSettings, BatterySettings

logger = logging.getLogger(__name__)

class ConsumptionManager:
    """Manages home energy consumption tracking and prediction."""
    
    def __init__(
        self,
        consumption_settings: ConsumptionSettings | None = None,
        battery_settings: BatterySettings | None = None
    ) -> None:
        """Initialize consumption manager.
        
        Args:
            consumption_settings: Settings for consumption behavior
            battery_settings: Settings for battery capacity
        """
        self.settings = consumption_settings or ConsumptionSettings()
        self.battery_settings = battery_settings or BatterySettings()
        
        # Tracking state
        self._predictions = [self.settings.default_hourly] * 24
        self._actual_consumption = {}
        self._battery_soc = {}
        self._last_update = None
        
        logger.debug(
            "Initialized ConsumptionManager with default consumption %.1f kWh",
            self.settings.default_hourly
        )
        
    def update_battery_soc(self, hour: int, soc: float) -> None:
        """Record battery SOC for a specific hour."""
        if not 0 <= hour <= 23:
            raise ValueError(f"Invalid hour: {hour}")
        if not 0 <= soc <= 100:
            raise ValueError(f"Invalid SOC value: {soc}")
            
        self._battery_soc[hour] = soc
        self._last_update = datetime.now()
        
        logger.debug("Updated hour %d SOC to %.1f%%", hour, soc)
        
    def calculate_energy_change(self, hour: int) -> float | None:
        """Calculate battery energy change for the given hour.
        
        Returns:
            Energy change in kWh or None if insufficient data
            Positive value indicates charging, negative indicates discharging
        """
        if hour not in self._battery_soc:
            return None
            
        prev_hour = (hour - 1) % 24
        if prev_hour not in self._battery_soc:
            return None
            
        soc_change = self._battery_soc[hour] - self._battery_soc[prev_hour]
        return (soc_change / 100.0) * self.battery_settings.total_capacity
        
    def update_consumption(self, hour: int, grid_import: float, 
                         battery_soc: float | None = None) -> None:
        """Update actual consumption for a specific hour."""
        if not 0 <= hour <= 23:
            raise ValueError(f"Invalid hour: {hour}")
            
        if grid_import < 0:
            raise ValueError(f"Invalid grid import: {grid_import}")
            
        # Record battery SOC if provided
        if battery_soc is not None:
            self.update_battery_soc(hour, battery_soc)
            
        # Calculate battery contribution
        energy_change = self.calculate_energy_change(hour)
        if energy_change:
            actual_consumption = grid_import + energy_change
        else:
            actual_consumption = grid_import
            
        # Ensure minimum valid consumption
        actual_consumption = max(self.settings.min_valid, actual_consumption)
        
        self._actual_consumption[hour] = actual_consumption
        self._last_update = datetime.now()
        
        logger.info(
            "Hour %d consumption updated: grid=%.2f, battery_change=%s, total=%.2f",
            hour, grid_import,
            f"{energy_change:.2f}" if energy_change else "N/A",
            actual_consumption
        )
        
        # Update predictions for future hours if we have enough data
        self._update_predictions(hour)
        
    def get_predictions(self) -> list[float]:
        """Get current hourly consumption predictions."""
        return self._predictions.copy()
        
    def get_actual_consumption(self, hour: int) -> float | None:
        """Get actual consumption for a specific hour if available."""
        return self._actual_consumption.get(hour)
        
    def reset_daily(self) -> None:
        """Reset tracking for new day."""
        self._actual_consumption.clear()
        self._battery_soc.clear()
        logger.info("Daily consumption tracking reset")
        
    def _update_predictions(self, current_hour: int) -> None:
        """Update predictions for future hours based on actual consumption."""
        if len(self._actual_consumption) < 3:
            return  # Need more data for meaningful updates
            
        # Calculate average from recent actual consumption
        recent_values = sorted(self._actual_consumption.values())[-3:]
        new_prediction = sum(recent_values) / len(recent_values)
        
        # Update all future hours
        for hour in range(current_hour + 1, 24):
            self._predictions[hour] = new_prediction
            
        logger.debug(
            "Updated future predictions to %.2f based on recent consumption",
            new_prediction
        )
        
    def set_predictions(self, predictions: list[float]) -> None:
        """Set hourly consumption predictions directly."""
        if len(predictions) != 24:
            raise ValueError(f"Expected 24 predictions, got {len(predictions)}")
            
        if any(p < self.settings.min_valid for p in predictions):
            raise ValueError(f"All predictions must be >= {self.settings.min_valid} kWh")
            
        self._predictions = list(predictions)  # Make a copy
        logger.debug(
            "Set predictions - min=%.1f, max=%.1f, avg=%.1f kWh",
            min(predictions), max(predictions), sum(predictions)/len(predictions)
        )