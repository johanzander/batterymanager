# system.py

"""Main facade for battery system management.

This module provides the `BatterySystemManager` class, which acts as the main
facade for managing the battery system. It integrates various components such as
the consumption manager, optimization manager, schedule manager, power monitor,
battery monitor, and price manager to provide a cohesive interface for managing
the battery system.

The `BatterySystemManager` class provides functionality to:
- Initialize and configure system components with default values.
- Optimize battery charge/discharge schedules based on electricity prices and 
  consumption predictions.
- Update system state and apply schedules for specific hours.
- Verify inverter settings and adjust charging power based on house consumption.
- Prepare and apply schedules for the next day.
- Get and update system settings.

Components integrated by `BatterySystemManager`:
- `ElectricityPriceManager`: Manages electricity price data from various sources.
- `ConsumptionManager`: Manages consumption predictions and updates.
- `OptimizationManager`: Optimizes battery charge/discharge schedule.
- `GrowattScheduleManager`: Manages and applies schedules to the Growatt inverter.
- `HomePowerMonitor`: Monitors and adjusts home power consumption.
- `BatteryMonitor`: Monitors battery state and verifies system settings.

Price Sources:
- `HANordpoolSource`: Fetches Nordpool electricity prices from Home Assistant integration.
- `NordpoolAPISource`: Fetches Nordpool electricity prices directly from Nordpool API.
- Other sources can be integrated as needed.

Home Assistant Controller:
- The `HomeAssistantController` is used to interact with a Home Assistant system,
  providing both Growatt inverter control as well as real-time data on consumption, 
  battery state, etc.
"""

import logging
from .settings import (
    BatterySettings,
    ConsumptionSettings,
    HomeSettings,
    PriceSettings
)
from .algorithms import optimize_battery
from .consumption_manager import ConsumptionManager
from .growatt_schedule import GrowattScheduleManager
from .battery_monitor import BatteryMonitor
from .power_monitor import HomePowerMonitor
from .price_manager import ElectricityPriceManager, HANordpoolSource
from .schedule import Schedule

logger = logging.getLogger(__name__)

class BatterySystemManager:
    """Facade for battery system management."""
    
    def __init__(
        self, 
        controller = None,
        battery_settings: BatterySettings | None = None,
        consumption_settings: ConsumptionSettings | None = None,
        home_settings: HomeSettings | None = None,
        price_settings: PriceSettings | None = None,
        price_source = None
    ):
        """Initialize system components.
        
        Args:
            controller: Home Assistant controller
            battery_settings: Optional battery settings
            consumption_settings: Optional consumption settings
            home_settings: Optional home electrical settings
            price_settings: Optional price settings
        """
        # Initialize settings
        self.battery_settings = battery_settings or BatterySettings()
        self.consumption_settings = consumption_settings or ConsumptionSettings()
        self.home_settings = home_settings or HomeSettings()
        self.price_settings = price_settings or PriceSettings()
        
        # Initialize controller
        self._controller = controller
        
        # Initialize components with settings
        self._consumption_manager = ConsumptionManager(
            consumption_settings=self.consumption_settings,
            battery_settings=self.battery_settings
        )
                
        self._schedule_manager = GrowattScheduleManager()

        if price_source is None:        
            price_source = HANordpoolSource(controller)
        self._price_manager = ElectricityPriceManager(
            source=price_source
        )
        
        self._power_monitor = HomePowerMonitor(
            controller,
            home_settings=self.home_settings,
            battery_settings=self.battery_settings
        )
        
        self._battery_monitor = BatteryMonitor(
            controller,
            self._schedule_manager,
            home_settings=self.home_settings,
            battery_settings=self.battery_settings
        )
        
        self._current_schedule = None
        
        logger.info("BatterySystemManager initialized")

    def _run_battery_optimization(self, price_entries: list[dict]) -> Schedule:
        """Run battery optimization with given price entries."""
        if not price_entries:
            raise ValueError("No prices available for optimization")

        # Select appropriate prices and adjust cycle cost for optimization
        use_raw_prices = not self.price_settings.use_actual_price
        prices = []
        for entry in price_entries:
            if use_raw_prices:
                prices.append(entry["price"])
            else:
                prices.append(entry["buyPrice"])
        
        # Adjust cycle cost to match price type (remove VAT if using raw prices)
        cycle_cost = (
            self.battery_settings.charge_cycle_cost / self.price_settings.vat_multiplier 
            if use_raw_prices 
            else self.battery_settings.charge_cycle_cost
        )
        
        logger.info(f"Running optimization with {'nordpool' if use_raw_prices else 'retail'} prices")
        
        # Get current SOC from controller
        if self._controller is not None:
            current_soc = self._controller.get_battery_soc()
        else:
            current_soc = self.battery_settings.min_soc
            
        print(f"Current SOC: {current_soc}")
        self._log_battery_system_config()

        # Run optimization
        optimization_result = optimize_battery(
            prices=prices,
            total_capacity=self.battery_settings.total_capacity,
            reserved_capacity=self.battery_settings.total_capacity * (self.battery_settings.min_soc / 100),
            cycle_cost=cycle_cost,
            hourly_consumption=self._consumption_manager.get_predictions(),
            max_charge_power=(self.battery_settings.charging_power_rate / 100) * self.battery_settings.max_charge_power_kw,
            min_profit_threshold=0.2,  # TODO: Make configurable
            initial_soc=current_soc  
        )        
        # Create schedule from results
        schedule = Schedule()
        schedule.set_optimization_results(
            actions=optimization_result["actions"],
            state_of_energy=optimization_result["state_of_energy"],
            prices=prices,
            cycle_cost=cycle_cost,
            hourly_consumption=self._consumption_manager.get_predictions()
        )
        
        self._schedule_manager.apply_schedule(schedule)
        self._current_schedule = schedule
        schedule.log_schedule()
        
        return schedule

    def run_optimization(self, price_date: str) -> Schedule:
        """Run optimization for specific date."""
        self._price_date = price_date
        price_entries = self._price_manager.get_prices(self._price_date)
        return self._run_battery_optimization(price_entries)

    def prepare_schedule(self, price_entries=None) -> Schedule:
        """Prepare schedule for today."""
        try:
            if price_entries is None:
                logger.debug("No prices provided, fetching from price manager")
                price_entries = self._price_manager.get_today_prices()
                
            return self._run_battery_optimization(price_entries)
        except Exception as e:
            logger.error("Schedule preparation failed: %s", str(e))
            raise

    def prepare_next_day_schedule(self) -> bool:
        """Prepare schedule for tomorrow."""
        try:
            price_entries = self._price_manager.get_tomorrow_prices()
            if not price_entries:
                logger.warning("No prices available for tomorrow")
                return False
                
            schedule = self._run_battery_optimization(price_entries)
            
            # Apply TOU settings
            self._controller.disable_all_TOU_settings()
            daily_settings = self._schedule_manager.get_daily_TOU_settings()
            
            for segment in daily_settings:
                if segment["enabled"]:
                    self._controller.set_inverter_time_segment(**segment)

            logger.info("Next day's schedule prepared successfully")
            return True

        except Exception as e:
            logger.error("Failed to prepare next day's schedule: %s", str(e))
            return False
            
    def _validate_hour(self, hour):
        """Validate hour is within valid range."""
        if not isinstance(hour, int) or hour < 0 or hour > 23:
            raise ValueError(f"Invalid hour: {hour}. Must be between 0 and 23")


    def update_state(self, hour):
        """Update system state for current hour."""
        try:
            self._validate_hour(hour)
            
            # Update consumption tracking
            consumption = self._controller.get_current_consumption()
            battery_soc = self._controller.get_battery_soc()
            self._consumption_manager.update_consumption(
                hour=hour,
                grid_import=consumption,
                battery_soc=battery_soc
            )
            
            # Ensure schedule is applied
            self.apply_schedule(hour)
            
        except Exception as e:
            logger.error("State update failed for hour %d: %s", hour, str(e))
            raise

    def apply_schedule(self, hour):
        """Apply schedule settings for specific hour."""
        try:
            self._validate_hour(hour)
            
            # Get or create schedule
            if not self._current_schedule:
                self._current_schedule = self.prepare_schedule()
                
            # Get settings from schedule manager    
            settings = self._schedule_manager.get_hourly_settings(hour)
            
            # Apply grid charge setting
            grid_charge_enabled = bool(settings["grid_charge"])
            current_grid_charge = self._controller.grid_charge_enabled()
            if grid_charge_enabled != current_grid_charge:
                self._controller.set_grid_charge(grid_charge_enabled)
                
            # Apply discharge rate
            discharge_rate = int(settings["discharge_rate"])
            current_discharge_rate = self._controller.get_discharging_power_rate()
            if discharge_rate != current_discharge_rate:
                self._controller.set_discharging_power_rate(discharge_rate)
                
        except Exception as e:
            logger.error("Failed to apply schedule for hour %d: %s", hour, str(e))
            raise

    def verify_inverter_settings(self, hour):
        """Verify inverter settings match schedule."""
        self._validate_hour(hour)
        self._battery_monitor.check_system_state(hour)
        
    def adjust_charging_power(self):
        """Adjust charging power based on house consumption."""
        self._power_monitor.adjust_battery_charging()
                    
    def get_settings(self) -> dict:
        """Get all current settings."""
        return {
            "battery": self.battery_settings.asdict(),
            "consumption": self.consumption_settings.asdict(),
            "home": self.home_settings.asdict(),
            "price": self.price_settings.asdict()
        }
        
    def update_settings(self, settings: dict) -> None:
        """Update settings from dictionary.
        
        Args:
            settings: Dictionary containing settings to update.
                     Can include 'battery', 'consumption', 'home', and 'price' sections.
        """
        if "battery" in settings:
            self.battery_settings.update(**settings["battery"])
            
        if "consumption" in settings:
            self.consumption_settings.update(**settings["consumption"])
            
        if "home" in settings:
            self.home_settings.update(**settings["home"])
            
        if "price" in settings:
            self.price_settings.update(**settings["price"])
            self._price_manager.update_settings(**settings["price"])
            
            
    def _log_battery_system_config(self):
        """Log the current battery configuration."""

        predictions = self._consumption_manager.get_predictions()
        if self._controller:
            current_soc = self._controller.get_battery_soc()
        else:
            current_soc = self.battery_settings.min_soc
        min_consumption = min(predictions)
        max_consumption = max(predictions)
        avg_consumption = sum(predictions) / 24
        
        config_str = f"""
\n╔═════════════════════════════════════════════════════╗
║          Battery Schedule Prediction Data           ║
╠══════════════════════════════════╦══════════════════╣
║ Parameter                        ║ Value            ║
╠══════════════════════════════════╬══════════════════╣
║ Total Capacity                   ║ {self.battery_settings.total_capacity:>12.1f} kWh ║
║ Reserved Capacity                ║ {self.battery_settings.total_capacity * (self.battery_settings.min_soc / 100):>12.1f} kWh ║
║ Usable Capacity                  ║ {self.battery_settings.total_capacity * (1 - self.battery_settings.min_soc / 100):>12.1f} kWh ║
║ Inital SOE                       ║ {self.battery_settings.total_capacity * (current_soc / 100):>12.1f} kWh ║
║ Max Charge/Discharge Power       ║ {self.battery_settings.max_charge_power_kw:>12.1f} kW  ║
║ Charge Cycle Cost                ║ {self.battery_settings.charge_cycle_cost:>12.2f} SEK ║
╠══════════════════════════════════╬══════════════════╣
║ Use Actual Price                 ║ {str(self.price_settings.use_actual_price):>15}  ║
║ Charging Power Rate              ║ {self.battery_settings.charging_power_rate:>12.1f} %   ║
║ Charging Power                   ║ {(self.battery_settings.charging_power_rate / 100) * self.battery_settings.max_charge_power_kw:>12.1f} kW  ║
║ Min Hourly Consumption           ║ {min_consumption:>12.1f} kWh ║
║ Max Hourly Consumption           ║ {max_consumption:>12.1f} kWh ║
║ Avg Hourly Consumption           ║ {avg_consumption:>12.1f} kWh ║
╚══════════════════════════════════╩══════════════════╝\n"""
        logger.info(config_str)
