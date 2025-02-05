"""Battery management module for optimizing charge/discharge schedules based on electricity prices."""

import logging
from typing import Any

import numpy as np

from .algorithms import optimize_battery
from .constants import (
    BATTERY_CHARGE_CYCLE_COST_SEK,
    BATTERY_DEFAULT_CHARGING_POWER_RATE,
    BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW,
    BATTERY_MAX_SOC,
    BATTERY_MIN_SOC,
    BATTERY_STORAGE_SIZE_KWH,
)
from .schedule import Schedule

#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BatteryManager:
    """Manages battery charging/discharging schedule based on electricity prices."""

    def __init__(self) -> None:
        """Initialize the battery manager."""
        self.electricity_price_nordpool: np.ndarray | None = None
        self.electricity_price_buy: np.ndarray | None = None
        self.electricity_price_sell: np.ndarray | None = None
        self.schedule: Schedule | None = None

        # Battery parameters with defaults
        self.total_capacity = BATTERY_STORAGE_SIZE_KWH
        self.reserved_capacity = BATTERY_MIN_SOC / 100 * BATTERY_STORAGE_SIZE_KWH
        self.estimated_consumption_per_hour_kwh = 4.5
        self.charging_power_rate = BATTERY_MAX_SOC
        self.max_charge_discharge = BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW
        self.charge_cycle_cost = BATTERY_CHARGE_CYCLE_COST_SEK
        self.charging_power_rate = BATTERY_DEFAULT_CHARGING_POWER_RATE

        self.battery_capacity_to_use_kwh = self.total_capacity - self.reserved_capacity
        self.battery_min_capacity_kwh = self.reserved_capacity
        self.charging_power_kw = (
            self.charging_power_rate / 100
        ) * self.max_charge_discharge

    def get_battery_settings(self) -> dict[str, float]:
        """Get current battery settings."""
        return {
            "totalCapacity": self.total_capacity,
            "reservedCapacity": self.reserved_capacity,
            "estimatedConsumption": self.estimated_consumption_per_hour_kwh,
            "maxChargeDischarge": self.max_charge_discharge,
            "chargeCycleCost": self.charge_cycle_cost,
            "chargingPowerRate": self.charging_power_rate,
        }

    def set_battery_settings(
        self,
        total_capacity: float,
        reserved_capacity: float,
        estimated_consumption: float,
        max_charge_discharge: float,
        charge_cycle_cost: float,
        charging_power_rate: float,
    ) -> None:
        """Set battery settings."""
        self.total_capacity = total_capacity
        self.reserved_capacity = reserved_capacity
        self.estimated_consumption_per_hour_kwh = estimated_consumption
        self.max_charge_discharge = max_charge_discharge
        self.charge_cycle_cost = charge_cycle_cost
        self.charging_power_rate = charging_power_rate

        # Recalculate derived values
        self.battery_capacity_to_use_kwh = self.total_capacity - self.reserved_capacity
        self.battery_min_capacity_kwh = self.reserved_capacity
        self.charging_power_kw = (
            self.charging_power_rate / 100
        ) * self.max_charge_discharge

        self._log_battery_config()

    def set_electricity_prices(self, prices: list[dict[str, Any]]) -> None:
        """Set electricity prices from a list of price dictionaries."""
        self.electricity_price_nordpool = np.array([entry["price"] for entry in prices])
        self.electricity_price_buy = np.array([entry["buyPrice"] for entry in prices])
        self.electricity_price_sell = np.array([entry["sellPrice"] for entry in prices])

        logger.info(
            "Loaded prices for %d hours starting from %s",
            len(prices),
            prices[0]["timestamp"],
        )

    def optimize_schedule(self) -> Schedule:
        """Calculate optimal battery charge/discharge schedule."""
        if self.electricity_price_nordpool is None:
            raise ValueError("Electricity prices must be set before optimization")

        # Run optimization
        result = optimize_battery(
            prices=self.electricity_price_nordpool,
            total_capacity=self.total_capacity,
            reserved_capacity=self.battery_min_capacity_kwh,
            cycle_cost=self.charge_cycle_cost,
            hourly_consumption=self.estimated_consumption_per_hour_kwh,
            max_charge_rate=self.charging_power_kw,
        )

        # Create and store schedule
        self.schedule = Schedule()
        self.schedule.set_optimization_results(
            actions=result["actions"],
            state_of_energy=result["state_of_energy"],
            results=result,
        )

        self._log_battery_schedule()
        return self.schedule

    def set_prediction_data(
        self,
        estimated_consumption_per_hour_kwh: float,
        max_charging_power_rate: float = 100.0,
    ) -> None:
        """Configure battery parameters based on consumption prediction."""
        self.estimated_consumption_per_hour_kwh = estimated_consumption_per_hour_kwh

        # Calculate usable battery capacity
        self.battery_capacity_to_use_kwh = self.total_capacity - self.reserved_capacity
        self.battery_min_capacity_kwh = self.reserved_capacity

        # Calculate charging parameters
        self.charging_power_rate = max_charging_power_rate
        self.charging_power_kw = (
            max_charging_power_rate / 100
        ) * BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW

        self._log_battery_config()

    def get_schedule(self) -> Schedule:
        """Get the current battery schedule."""
        if self.schedule is None:
            raise ValueError("No schedule has been calculated yet")
        return self.schedule

    def _log_battery_config(self) -> None:
        """Log the current battery configuration."""
        config = f"""
\n╔═════════════════════════════════════════════════════╗
║          Battery Schedule Prediction Data           ║
╠══════════════════════════════════╦══════════════════╣
║ Parameter                        ║ Value            ║
╠══════════════════════════════════╬══════════════════╣
║ Total Capacity                   ║ {BATTERY_STORAGE_SIZE_KWH:>12.1f} kWh ║
║ Reserved Capacity                ║ {self.battery_min_capacity_kwh:>12.1f} kWh ║
║ Usable Capacity                  ║ {self.battery_capacity_to_use_kwh:>12.1f} kWh ║
║ Max Charge/Discharge Power       ║ {BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW:>12.1f} kW  ║
║ Charge Cycle Cost                ║ {BATTERY_CHARGE_CYCLE_COST_SEK:>12.2f} SEK ║
╠══════════════════════════════════╬══════════════════╣
║ Charging Power Rate              ║ {self.charging_power_rate:>12.1f} %   ║
║ Charging Power                   ║ {self.charging_power_kw:>12.1f} kW  ║
║ Estimated Hourly Consumption     ║ {self.estimated_consumption_per_hour_kwh:>12.1f} kWh ║
╚══════════════════════════════════╩══════════════════╝\n"""
        logger.info(config)

    def _log_battery_schedule(self) -> None:
        """Print the current battery schedule."""
        if self.schedule is None:
            logger.warning("No schedule has been calculated yet")
            return

        result = self.schedule.optimization_results
        prices = self.electricity_price_nordpool
        hourly_consumption = self.estimated_consumption_per_hour_kwh
        name = "Battery Schedule"

        lines = []
        lines.append(f"\n{name}:")

        # Table headers
        header1 = "╔════════╦═════════════════════════════╦╦══════════════════════════════════════════════════════════════╗"
        header2 = "║        ║        Base Case            ║║                      Optimized Case                          ║"
        header3 = "║  Hour  ╠═════════╦═══════╦═══════════╬╬══════╦════════╦═════════╦═══════════╦════════════╦═══════════╣"
        header4 = "║        ║  Price  ║ Cons. ║   Cost    ║║  SOE ║ Action ║ G.Cost  ║  B.Cost   ║ Tot. Cost  ║  Savings  ║"
        header5 = "╠════════╬═════════╬═══════╬═══════════╬╬══════╬════════╬═════════╬═══════════╬════════════╬═══════════╣"

        lines.extend([header1, header2, header3, header4, header5])

        # Initialize totals
        total_base_cost = 0
        total_grid_cost = 0
        total_battery_cost = 0
        total_optimized_cost = 0
        total_savings = 0
        total_consumption = 0
        total_charged = 0
        total_discharged = 0

        # Format hourly data
        for hour, costs in enumerate(result["hourly_costs"]):
            base_cost = prices[hour] * hourly_consumption
            soe = result["state_of_energy"][hour]
            action = result["actions"][hour]

            # Update totals
            total_base_cost += base_cost
            total_grid_cost += costs["grid_cost"]
            total_battery_cost += costs["battery_cost"]
            total_optimized_cost += costs["total_cost"]
            total_savings += costs["savings"]
            total_consumption += hourly_consumption

            if action > 0:
                total_charged += action
            elif action < 0:
                total_discharged -= action

            # Format row
            row = (
                f"║ {hour:02d}:00  ║"
                f" {prices[hour]:>7.3f} ║"
                f" {hourly_consumption:>5.1f} ║"
                f" {base_cost:>9.2f} ║║"
                f" {soe:>4.1f} ║"
                f" {action:>6.1f} ║"
                f" {costs['grid_cost']:>7.2f} ║"
                f" {costs['battery_cost']:>9.2f} ║"
                f" {costs['total_cost']:>10.2f} ║"
                f" {costs['savings']:>9.2f} ║"
            )
            lines.append(row)

        # Format totals
        footer1 = "╠════════╬═════════╬═══════╬═══════════╬╬══════╬════════╬═════════╬═══════════╬════════════╬═══════════╣"
        footer2 = (
            f"║ TOTAL  ║         ║{total_consumption:>7.1f}║{total_base_cost:>11.2f}║║      ║"
            f"C:{total_charged:>6.1f}║{total_grid_cost:>9.2f}║{total_battery_cost:>11.2f}║"
            f"{total_optimized_cost:>12.2f}║{total_savings:>11.2f}║"
        )
        footer3 = (
            f"║        ║         ║       ║           ║║      ║"
            f"D:{total_discharged:>6.1f}║         ║           ║            ║           ║"
        )
        footer4 = "╚════════╩═════════╩═══════╩═══════════╩╩══════╩════════╩═════════╩═══════════╩════════════╩═══════════╝"

        lines.extend([footer1, footer2, footer3, footer4])

        # Format summary
        lines.extend(
            [
                "\nSummary:",
                f"Base case cost:               {total_base_cost:>8.2f} SEK",
                f"Optimized cost:               {total_optimized_cost:>8.2f} SEK",
                f"Total savings:                {total_savings:>8.2f} SEK",
                f"Savings percentage:           {(total_savings/total_base_cost*100):>8.1f} %",
                f"Total energy charged:         {total_charged:>8.1f} kWh",
                f"Total energy discharged:      {total_discharged:>8.1f} kWh\n",
            ]
        )

        logger.info("\n".join(lines))
