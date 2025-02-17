"""Monitors home power usage and adapts battery charging power to prevent overloading of fuses.

It does this by:

1. Power Monitoring:
   - Continuously monitors current draw on all three phases
   - Calculates total power consumption per phase
   - Considers house fuse limits (e.g., 25A per phase)
   - Maintains a safety margin to prevent tripping fuses

2. Battery Charge Management:
   - Adjusts battery charging power based on available power
   - Ensures total power draw (including battery) stays within fuse limits
   - Makes gradual adjustments (e.g., 5% steps) to prevent sudden load changes
   - Respects maximum charging rate configuration
   - Only activates when grid charging is enabled

This module is designed to work with the Home Assistant controller and to be run periodically (e.g from pyscript)

"""

import logging
from .settings import HomeSettings, BatterySettings
from .settings import BATTERY_MAX_CHARGE_DISCHARGE_POWER_KW

logger = logging.getLogger(__name__)

class HomePowerMonitor:
    """Monitors home power consumption and manages battery charging."""

    def __init__(
        self,
        ha_controller,
        home_settings: HomeSettings | None = None,
        battery_settings: BatterySettings | None = None,
        step_size: int = 5,
    ):
        """Initialize power monitor.
        
        Args:
            ha_controller: Home Assistant controller instance
            home_settings: Home electrical settings (optional)
            battery_settings: Battery settings (optional)
            step_size: Size of power adjustments in percent (default: 5%)
        """
        self.controller = ha_controller
        self.home_settings = home_settings or HomeSettings()
        self.battery_settings = battery_settings or BatterySettings()
        self.step_size = step_size

        # Calculate max power per phase with safety margin
        self.max_power_per_phase = (
            self.home_settings.voltage * 
            self.home_settings.max_fuse_current * 
            self.home_settings.safety_margin
        )

        # Max charging power in watts (convert from kW)
        self.max_charge_power = BATTERY_MAX_CHARGE_DISCHARGE_POWER_KW * 1000

        logger.info(
            f"Initialized HomePowerMonitor with:\n"
            f"  Max power per phase: {self.max_power_per_phase:.0f}W\n"
            f"  Max charging power: {self.max_charge_power:.0f}W\n"
            f"  Max battery charging rate: {self.battery_settings.charging_power_rate}%\n"
            f"  Step size: {self.step_size}%"
        )

    def get_current_phase_loads_w(self):
        """Get current load on each phase in watts."""
        l1_current = self.controller.get_l1_current()
        l2_current = self.controller.get_l2_current()
        l3_current = self.controller.get_l3_current()

        return (
            l1_current * self.home_settings.voltage,
            l2_current * self.home_settings.voltage,
            l3_current * self.home_settings.voltage,
        )

    def calculate_available_charging_power(self):
        """Calculate safe battery charging power based on most loaded phase."""
        # Get current loads in watts
        l1, l2, l3 = self.get_current_phase_loads_w()

        # Calculate current usage as percentage of max safe current
        l1_pct = (l1 / self.max_power_per_phase) * 100
        l2_pct = (l2 / self.max_power_per_phase) * 100
        l3_pct = (l3 / self.max_power_per_phase) * 100

        # Find most loaded phase
        max_load_pct = max(l1_pct, l2_pct, l3_pct)

        # Available capacity is what's left from 100%
        available_pct = 100 - max_load_pct

        # Convert to charging power percentage (limit by configured max)
        charging_power_pct = min(available_pct, float(self.battery_settings.charging_power_rate))

        logger.info(
            f"Phase loads: #1: {l1:.0f}W ({l1_pct:.1f}%), "
            f"#2: {l2:.0f}W ({l2_pct:.1f}%), "
            f"#3: {l3:.0f}W ({l3_pct:.1f}%)\n"
            f"Most loaded phase: {max_load_pct:.1f}%\n"
            f"Available capacity: {available_pct:.1f}%\n"
            f"Recommended charging: {charging_power_pct:.1f}%"
        )

        return max(0, charging_power_pct)

    def adjust_battery_charging(self):
        """Adjust battery charging power based on available capacity."""
        if not self.controller.grid_charge_enabled():
            return

        target_power = self.calculate_available_charging_power()
        current_power = self.controller.get_charging_power_rate()

        if target_power > current_power:
            new_power = min(current_power + self.step_size, target_power)
        else:
            new_power = max(current_power - self.step_size, target_power)

        if abs(new_power - current_power) >= self.step_size:
            logger.info(
                f"Adjusting charging power from {current_power}% to {new_power:.0f}% "
                f"(target: {target_power:.0f}%)"
            )
            self.controller.set_charging_power_rate(int(new_power))