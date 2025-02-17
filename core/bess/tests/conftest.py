# tests/conftest.py

"""Shared test fixtures and utilities."""

from datetime import datetime
import logging
import pytest
from bess.schedule import Schedule
from bess.consumption_manager import ConsumptionManager

# Constants for testing
VALID_TEST_HOURS = [0, 12, 23]  # Start, middle, end of day
INVALID_TEST_HOURS = [-1, 24, 25]  # Before start, after end, way after

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockHomeAssistantController:
    """Mock HA controller for testing."""
    
    def __init__(self):
        self.settings = {
            "grid_charge": False,
            "discharge_rate": 0,
            "battery_soc": 50,
            "consumption": 4.5,
            "charge_power": 0,
            "discharge_power": 0,
            "l1_current": 10.0,
            "l2_current": 8.0,
            "l3_current": 12.0,
            "charge_stop_soc": 100,
            "discharge_stop_soc": 10,
            "charging_power_rate": 40,
            "test_mode": False,
            "tou_settings": []  # Added for schedule adaptation tests
        }
        
    def get_battery_soc(self):
        return self.settings["battery_soc"]
        
    def get_current_consumption(self):
        return self.settings["consumption"]
        
    def grid_charge_enabled(self):
        return self.settings["grid_charge"]
        
    def set_grid_charge(self, enabled):
        self.settings["grid_charge"] = enabled
        
    def get_battery_charge_power(self):
        return self.settings["charge_power"]
        
    def get_battery_discharge_power(self):
        return self.settings["discharge_power"]
        
    def get_charging_power_rate(self):
        return self.settings["charging_power_rate"]
        
    def set_charging_power_rate(self, rate):
        self.settings["charging_power_rate"] = rate
        
    def get_discharging_power_rate(self):
        return self.settings["discharge_rate"]
        
    def set_discharging_power_rate(self, rate):
        self.settings["discharge_rate"] = rate
        
    def get_charge_stop_soc(self):
        return self.settings["charge_stop_soc"]
        
    def set_charge_stop_soc(self, soc):
        self.settings["charge_stop_soc"] = soc
        
    def get_discharge_stop_soc(self):
        return self.settings["discharge_stop_soc"]
        
    def set_discharge_stop_soc(self, soc):
        self.settings["discharge_stop_soc"] = soc

    def set_test_mode(self, enabled):
        self.settings["test_mode"] = enabled
        
    def get_l1_current(self):
        return self.settings["l1_current"]

    def get_l2_current(self):
        return self.settings["l2_current"]

    def get_l3_current(self):
        return self.settings["l3_current"]
        
    def get_nordpool_prices_today(self):
        """Get today's prices."""
        # Return flat prices by default
        return [1.0] * 24
        
    def get_nordpool_prices_tomorrow(self):
        """Get tomorrow's prices."""
        # Return flat prices by default
        return [1.0] * 24
        
    def disable_all_TOU_settings(self):
        """Clear all TOU settings."""
        self.settings["tou_settings"] = []
        
    def set_inverter_time_segment(self, **kwargs):
        """Store TOU setting."""
        self.settings["tou_settings"].append(kwargs)

# Helper functions
def format_test_prices(raw_prices, buy_multiplier=1.25, sell_multiplier=0.8):
    """Format raw prices into price dictionaries."""
    return [
        {
            "timestamp": (datetime.now().replace(hour=h, minute=0)).strftime("%Y-%m-%d %H:%M"),
            "price": price,
            "buyPrice": price * buy_multiplier,
            "sellPrice": price * sell_multiplier
        }
        for h, price in enumerate(raw_prices)
    ]

def create_alternating_prices():
    """Create alternating low/high price pattern for adaptation tests."""
    return [
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  # Hours 0-5: Low
        3.0, 3.0, 3.0, 3.0, 3.0, 3.0,  # Hours 6-11: High
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  # Hours 12-17: Low
        3.0, 3.0, 3.0, 3.0, 3.0, 3.0,  # Hours 18-23: High
    ]

# Fixtures
@pytest.fixture
def ha_controller():
    """Provide mock Home Assistant controller."""
    return MockHomeAssistantController()

@pytest.fixture
def consumption_manager():
    """Provide ConsumptionManager instance."""
    return ConsumptionManager()

@pytest.fixture
def create_test_schedule():
    """Create schedule with specified actions."""
    def _create(actions, state_of_energy=None):
        if state_of_energy is None:
            state_of_energy = [3.0] * (len(actions) + 1)
            
        schedule = Schedule()
        schedule.set_optimization_results(
            actions=actions,
            state_of_energy=state_of_energy,
            prices=[1.0] * len(actions),
            cycle_cost=0.5,
            hourly_consumption=[4.5] * len(actions)
        )
        return schedule
        
    return _create

# Test data fixtures
@pytest.fixture
def alternating_prices():
    """Provide prices alternating between low and high periods."""
    return format_test_prices(create_alternating_prices())

# Test data fixtures
@pytest.fixture
def test_prices_2024_08_16():
    """Return price pattern from 2024-08-16."""
    return format_test_prices([
        0.9827, 0.8419, 0.0321, 0.0097, 0.0098, 0.9136,
        1.4433, 1.5162, 1.4029, 1.1346, 0.8558, 0.6485,
        0.2895, 0.1363, 0.1253, 0.6200, 0.8880, 1.1662,
        1.5163, 2.5908, 2.7325, 1.9312, 1.5121, 1.3056,
    ])

@pytest.fixture
def test_prices_2025_01_05():
    """Return price pattern from 2025-01-05."""
    return format_test_prices([
        0.780, 0.790, 0.800, 0.830, 0.950, 0.970,
        1.160, 1.170, 1.220, 1.280, 1.210, 1.300,
        1.200, 1.130, 0.980, 0.740, 0.730, 0.950,
        0.920, 0.740, 0.530, 0.530, 0.500, 0.400,
    ])

@pytest.fixture
def test_prices_2025_01_12():
    """Return price pattern with evening peak from 2025-01-12."""
    return format_test_prices([
        0.357, 0.301, 0.289, 0.349, 0.393, 0.405,
        0.412, 0.418, 0.447, 0.605, 0.791, 0.919,
        0.826, 0.779, 1.066, 1.332, 1.492, 1.583,
        1.677, 1.612, 1.514, 1.277, 0.829, 0.481,
    ])

@pytest.fixture
def test_prices_2025_01_13():
    """Return price pattern with night low from 2025-01-13."""
    return format_test_prices([
        0.477, 0.447, 0.450, 0.438, 0.433, 0.422,
        0.434, 0.805, 1.180, 0.654, 0.454, 0.441,
        0.433, 0.425, 0.410, 0.399, 0.402, 0.401,
        0.379, 0.347, 0.067, 0.023, 0.018, 0.000,
    ])

@pytest.fixture
def flat_prices():
    """Provide test data with flat prices."""
    return format_test_prices([1.0] * 24)

@pytest.fixture
def peak_prices():
    """Provide test data with peak/valley prices."""
    return format_test_prices([
        0.98, 0.84, 0.03, 0.01, 0.01, 0.91,
        1.44, 1.52, 1.40, 1.13, 0.86, 0.65,
        0.29, 0.14, 0.13, 0.62, 0.89, 1.17,
        1.52, 2.59, 2.73, 1.93, 1.51, 1.31,
    ])

# System fixtures
@pytest.fixture
def system(ha_controller):
    """Provide configured system instance."""
    from bess import BatterySystemManager
    return BatterySystemManager(controller=ha_controller)

# System fixtures
@pytest.fixture
def system(ha_controller):
    """Provide configured system instance."""
    from bess import BatterySystemManager
    return BatterySystemManager(controller=ha_controller)

@pytest.fixture
def system_with_alternating_prices(system, alternating_prices):
    """Provide system configured with alternating price pattern."""
    class MockPriceSource:
        def get_prices(self, target_date, area, calculator):
            return alternating_prices
            
    system._price_manager.source = MockPriceSource()
    return system

# Environment setup
@pytest.fixture
def test_env(consumption_manager):
    """Set up test environment with specific conditions."""
    def _configure(consumption_level=5.2, prices=None):
        consumption_manager.set_predictions([consumption_level] * 24)
        
        return {
            "consumption_manager": consumption_manager,
            "consumption_level": consumption_level
        }
        
    return _configure

# Test scenario helper
@pytest.fixture
def adaptation_scenario():
    """Create test scenario for schedule adaptation tests."""
    def _create_scenario(hour, consumption, soc):
        return {
            "hour": hour,
            "consumption": consumption,
            "soc": soc
        }
    return _create_scenario