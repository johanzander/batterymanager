# tests/test_power_monitor.py

"""Tests for power monitoring functionality."""

import pytest
from bess.power_monitor import HomePowerMonitor
from bess.settings import HomeSettings, BatterySettings

class TestPowerMonitor:
    """Power monitor tests."""

    def test_phase_load_calculation(self, ha_controller):
        """Test calculation of phase loads."""
        monitor = HomePowerMonitor(ha_controller)
        l1, l2, l3 = monitor.get_current_phase_loads_w()
        
        assert isinstance(l1, float)
        assert isinstance(l2, float)
        assert isinstance(l3, float)
        
        # Each load should be current * voltage
        voltage = monitor.home_settings.voltage
        assert l1 == ha_controller.get_l1_current() * voltage
        assert l2 == ha_controller.get_l2_current() * voltage
        assert l3 == ha_controller.get_l3_current() * voltage

    def test_available_charging_power(self, ha_controller):
        """Test calculation of available charging power."""
        monitor = HomePowerMonitor(ha_controller)
        power = monitor.calculate_available_charging_power()
        
        assert isinstance(power, float)
        assert 0 <= power <= monitor.battery_settings.charging_power_rate

    def test_custom_settings(self, ha_controller):
        """Test monitor with custom settings."""
        home_settings = HomeSettings()
        home_settings.max_fuse_current = 32  # Higher fuse rating
        home_settings.voltage = 240  # Different voltage
        
        battery_settings = BatterySettings()
        battery_settings.charging_power_rate = 50  # Higher charging rate
        
        monitor = HomePowerMonitor(
            ha_controller,
            home_settings=home_settings,
            battery_settings=battery_settings
        )
        
        # Verify settings were applied
        assert monitor.home_settings.max_fuse_current == 32
        assert monitor.home_settings.voltage == 240
        assert monitor.battery_settings.charging_power_rate == 50
        
        # Test calculations with new settings
        l1, l2, l3 = monitor.get_current_phase_loads_w()
        assert l1 == ha_controller.get_l1_current() * 240  # Using new voltage

    def test_charging_adjustment(self, ha_controller):
        """Test charging power adjustment."""
        monitor = HomePowerMonitor(ha_controller, step_size=10)
        
        # Enable grid charging
        ha_controller.set_grid_charge(True)
        
        # Initial adjustment
        monitor.adjust_battery_charging()
        
        # Verify charging power was set
        current_power = ha_controller.get_charging_power_rate()
        assert isinstance(current_power, (int, float))
        assert 0 <= current_power <= monitor.battery_settings.charging_power_rate

    def test_disabled_grid_charging(self, ha_controller):
        """Test behavior when grid charging is disabled."""
        monitor = HomePowerMonitor(ha_controller)
        
        # Disable grid charging
        ha_controller.set_grid_charge(False)
        
        # Get current charging power
        initial_power = ha_controller.get_charging_power_rate()
        
        # Try to adjust charging
        monitor.adjust_battery_charging()
        
        # Verify no changes were made
        assert ha_controller.get_charging_power_rate() == initial_power