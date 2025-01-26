"""Battery management module for optimizing charge/discharge schedules based on electricity prices."""

import logging

from .algorithms import optimize_battery
from .defaults import (
    BATTERY_CHARGE_CYCLE_COST_SEK,
    BATTERY_DEFAULT_CHARGING_POWER_RATE,
    BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW,
    BATTERY_MIN_SOC,
    BATTERY_STORAGE_SIZE_KWH,
    HOME_HOURLY_CONSUMPTION_KWH,
    MIN_PROFIT,
    VAT_MULTIPLIER,
)
from .schedule import Schedule

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)


class BatteryConfig:
    """Battery system configuration."""

    def __init__(self):
        """Initialize battery configuration with default values."""

        self.use_actual_price = False
        self.total_capacity = BATTERY_STORAGE_SIZE_KWH
        self.reserved_capacity = BATTERY_MIN_SOC / 100 * BATTERY_STORAGE_SIZE_KWH
        self.max_charge_discharge_power = BATTERY_MAX_CHARGE_DISCHARGE_RATE_KW
        self.charge_cycle_cost = BATTERY_CHARGE_CYCLE_COST_SEK
        self.charging_power_rate = BATTERY_DEFAULT_CHARGING_POWER_RATE
        self.min_profit_threshold = MIN_PROFIT
        self.estimated_consumption = HOME_HOURLY_CONSUMPTION_KWH


class BatteryManager:
    """Manages battery operations including optimization and scheduling."""

    def __init__(self) -> None:
        """Initialize battery manager with default configuration."""
        self.config = BatteryConfig()
        self.electricity_price_nordpool = None
        self.electricity_price_buy = None
        self.electricity_price_sell = None
        self.schedule = None
        self.capacity_to_use = (
            self.config.total_capacity - self.config.reserved_capacity
        )
        self.charging_power_kw = (
            self.config.charging_power_rate / 100
        ) * self.config.max_charge_discharge_power

    def get_settings(self):
        """Return the current battery configuration settings."""

        return {
            "useActualPrice": self.config.use_actual_price,
            "totalCapacity": self.config.total_capacity,
            "reservedCapacity": self.config.reserved_capacity,
            "estimatedConsumption": self.config.estimated_consumption,
            "maxChargeDischarge": self.config.max_charge_discharge_power,
            "chargeCycleCost": self.config.charge_cycle_cost,
            "chargingPowerRate": self.config.charging_power_rate,
        }

    def update_settings(
        self,
        use_actual_price=None,
        total_capacity=None,
        reserved_capacity=None,
        estimated_consumption=None,
        max_charge_discharge=None,
        charge_cycle_cost=None,
        charging_power_rate=None,
    ):
        """Update battery configuration settings."""
        if use_actual_price is not None:
            self.config.use_actual_price = use_actual_price
        if total_capacity is not None:
            self.config.total_capacity = total_capacity
        if reserved_capacity is not None:
            self.config.reserved_capacity = reserved_capacity
        if estimated_consumption is not None:
            self.config.estimated_consumption = estimated_consumption
        if max_charge_discharge is not None:
            self.config.max_charge_discharge_power = max_charge_discharge
        if charge_cycle_cost is not None:
            self.config.charge_cycle_cost = charge_cycle_cost
        if charging_power_rate is not None:
            self.config.charging_power_rate = charging_power_rate

        self.capacity_to_use = (
            self.config.total_capacity - self.config.reserved_capacity
        )
        self.charging_power_kw = (
            self.config.charging_power_rate / 100
        ) * self.config.max_charge_discharge_power
        self._log_battery_config()

    def set_electricity_prices(self, prices):
        """Set electricity prices for optimization."""
        self.electricity_price_nordpool = [entry["price"] for entry in prices]
        self.electricity_price_buy = [entry["buyPrice"] for entry in prices]
        self.electricity_price_sell = [entry["sellPrice"] for entry in prices]

        logger.info(
            "Loaded prices for %d hours starting from %s",
            len(prices),
            prices[0]["timestamp"],
        )

    def optimize_schedule(self):
        """Optimize battery schedule using configured prices."""
        if self.electricity_price_nordpool is None:
            raise ValueError("Electricity prices must be set before optimization")

        # Optimize using actual prices if that setting is enabled
        if self.config.use_actual_price:  # incl. VAT
            prices_to_use = self.electricity_price_buy
            cycle_cost = self.config.charge_cycle_cost
        else:  # excl. VAT
            prices_to_use = self.electricity_price_nordpool
            cycle_cost = self.config.charge_cycle_cost / VAT_MULTIPLIER
        #            cycle_cost = self.config.charge_cycle_cost / self.config.vat_multiplier

        result = optimize_battery(
            prices=prices_to_use,
            total_capacity=self.config.total_capacity,
            reserved_capacity=self.config.reserved_capacity,
            cycle_cost=cycle_cost,
            hourly_consumption=self.config.estimated_consumption,
            max_charge_rate=self.charging_power_kw,
            min_profit_threshold=self.config.min_profit_threshold,
        )

        self.schedule = Schedule()
        self.schedule.set_optimization_results(
            actions=result["actions"],
            state_of_energy=result["state_of_energy"],
            prices=prices_to_use,
            cycle_cost=self.config.charge_cycle_cost,
            hourly_consumption=self.config.estimated_consumption,
        )

        self._log_battery_schedule()
        return self.schedule

    def set_prediction_data(
        self,
        estimated_consumption_per_hour_kwh,
        max_charging_power_rate,
    ):
        """Set prediction data for battery optimization."""
        self.config.estimated_consumption = estimated_consumption_per_hour_kwh
        self.config.charging_power_rate = max_charging_power_rate
        self.charging_power_kw = (
            max_charging_power_rate / 100
        ) * self.config.max_charge_discharge_power
        self._log_battery_config()

    def get_schedule(self):
        """Return the current battery schedule."""
        if self.schedule is None:
            raise ValueError("No schedule has been calculated yet")
        return self.schedule

    def _log_battery_config(self):
        config = f"""
\n╔═════════════════════════════════════════════════════╗
║          Battery Schedule Prediction Data           ║
╠══════════════════════════════════╦══════════════════╣
║ Parameter                        ║ Value            ║
╠══════════════════════════════════╬══════════════════╣
║ Use Actual Price                 ║ {str(self.config.use_actual_price):>12} ║
║ Total Capacity                   ║ {self.config.total_capacity:>12.1f} kWh ║
║ Reserved Capacity                ║ {self.config.reserved_capacity:>12.1f} kWh ║
║ Usable Capacity                  ║ {self.capacity_to_use:>12.1f} kWh ║
║ Max Charge/Discharge Power       ║ {self.config.max_charge_discharge_power:>12.1f} kW  ║
║ Charge Cycle Cost                ║ {self.config.charge_cycle_cost:>12.2f} SEK ║
╠══════════════════════════════════╬══════════════════╣
║ Charging Power Rate              ║ {self.config.charging_power_rate:>12.1f} %   ║
║ Charging Power                   ║ {self.charging_power_kw:>12.1f} kW  ║
║ Estimated Hourly Consumption     ║ {self.config.estimated_consumption:>12.1f} kWh ║
╚══════════════════════════════════╩══════════════════╝\n"""
        logger.info(config)

    def _log_battery_schedule(self) -> None:
        """Print the current battery schedule."""
        if self.schedule is None:
            logger.warning("No schedule has been calculated yet")
            return

        schedule_data = self.schedule.get_schedule_data()
        hourly_data = schedule_data["hourlyData"]
        summary = schedule_data["summary"]

        # Table headers
        lines = [
            "\nBattery Schedule:",
            "╔════════╦═════════════════════════════╦╦══════════════════════════════════════════════════════════════╗",
            "║        ║        Base Case            ║║                      Optimized Case                          ║",
            "║  Hour  ╠═════════╦═══════╦═══════════╬╬══════╦════════╦═════════╦═══════════╦════════════╦═══════════╣",
            "║        ║  Price  ║ Cons. ║   Cost    ║║  SOE ║ Action ║ G.Cost  ║  B.Cost   ║ Tot. Cost  ║  Savings  ║",
            "╠════════╬═════════╬═══════╬═══════════╬╬══════╬════════╬═════════╬═══════════╬════════════╬═══════════╣",
        ]

        # Format hourly data
        total_charged = 0
        total_discharged = 0

        for hour_data in hourly_data:
            action = hour_data["action"]
            if action > 0:
                total_charged += action
            elif action < 0:
                total_discharged -= action

            row = (
                f"║ {hour_data['hour']}  ║"
                f" {hour_data['price']:>7.3f} ║"
                f" {self.config.estimated_consumption:>5.1f} ║"
                f" {hour_data['baseCost']:>9.2f} ║║"
                f" {hour_data['batteryLevel']:>4.1f} ║"
                f" {action:>6.1f} ║"
                f" {hour_data['gridCost']:>7.2f} ║"
                f" {hour_data['batteryCost']:>9.2f} ║"
                f" {hour_data['totalCost']:>10.2f} ║"
                f" {hour_data['savings']:>9.2f} ║"
            )
            lines.append(row)

        # Format totals
        lines.extend(
            [
                "╠════════╬═════════╬═══════╬═══════════╬╬══════╬════════╬═════════╬═══════════╬════════════╬═══════════╣",
                f"║ TOTAL  ║         ║{self.config.estimated_consumption * 24:>7.1f}║{summary['baseCost']:>11.2f}║║      ║"
                f"C:{total_charged:>6.1f}║{summary['gridCosts']:>9.2f}║{summary['batteryCosts']:>11.2f}║"
                f"{summary['optimizedCost']:>12.2f}║{summary['savings']:>11.2f}║",
                f"║        ║         ║       ║           ║║      ║D:{total_discharged:>6.1f}║         ║           ║            ║           ║",
                "╚════════╩═════════╩═══════╩═══════════╩╩══════╩════════╩═════════╩═══════════╩════════════╩═══════════╝",
            ]
        )

        # Format summary
        lines.extend(
            [
                "\nSummary:",
                f"Base case cost:               {summary['baseCost']:>8.2f} SEK",
                f"Optimized cost:               {summary['optimizedCost']:>8.2f} SEK",
                f"Total savings:                {summary['savings']:>8.2f} SEK",
                f"Savings percentage:           {(summary['savings']/summary['baseCost']*100):>8.1f} %",
                f"Total energy charged:         {total_charged:>8.1f} kWh",
                f"Total energy discharged:      {total_discharged:>8.1f} kWh\n",
            ]
        )

        logger.info("\n".join(lines))
